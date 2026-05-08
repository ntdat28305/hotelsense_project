"""
api.py — FastAPI backend cho HotelSense
Deploy lên HuggingFace Spaces

Endpoints:
    POST /predict              — giữ nguyên endpoint cũ (backward compatible)
    POST /analyze              — phân tích batch reviews
    GET  /hotels/search        — tìm KS từ DB (Chế độ 1)
    POST /hotels/analyze-urls  — phân tích URLs tùy chọn (Chế độ 2)
    GET  /hotels/{id}          — chi tiết KS
    GET  /hotels/{id}/reviews  — reviews đã gán nhãn
    GET  /cities               — danh sách thành phố
    GET  /districts/{city}     — danh sách quận theo thành phố
    GET  /health               — health check

Chạy local:
    uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging

from predictor import (
    predict_single, predict_batch,
    compute_absa_summary, compute_match_score,
)
from database import (
    init_db, get_hotel_by_id, search_hotels,
    get_reviews_by_hotel, get_all_cities,
    get_districts_by_city, get_db_stats,
    add_search_history, get_search_history,
    add_bookmark, remove_bookmark, get_bookmarks, is_bookmarked,
)
from auth import router as auth_router, require_user

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(
    title="HotelSense ABSA API",
    description="Phân tích cảm xúc đa khía cạnh cho đánh giá khách sạn",
    version="2.0.0",
)

# Include auth routes
app.include_router(auth_router)

# CORS — cho phép React frontend gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo DB khi startup
@app.on_event("startup")
async def startup():
    init_db()
    log.info("API sẵn sàng!")


# ── Pydantic Models ──────────────────────────────────────────────────

class ReviewInput(BaseModel):
    """Giữ nguyên từ api.py cũ — backward compatible."""
    text:       str
    model_type: str = "phobert"


class AnalyzeBatchInput(BaseModel):
    reviews:    list[str]
    model_type: str = "phobert"


class AnalyzeUrlsInput(BaseModel):
    urls:             list[str]
    max_reviews:      int        = 50
    model_type:       str        = "phobert"
    models:           list[str]  = []          # multi-model so sanh
    user_request:     Optional[str] = None
    priority_aspects: list[str]  = []



class SearchInput(BaseModel):
    city:             str
    district:         Optional[str] = None
    user_request:     Optional[str] = None
    priority_aspects: list[str]     = []
    min_score:        float         = 0


# ── Endpoint cũ — giữ nguyên ─────────────────────────────────────────

@app.post("/predict")
async def predict(data: ReviewInput):
    """
    Endpoint cũ — giữ nguyên để backward compatible với app.py Streamlit cũ.
    """
    try:
        result = predict_single(data.text, data.model_type)

        # Chuyển sang format cũ: list 12 phần tử [neg, pos] x 6 aspects
        CATEGORIES = [
            "Room_Facilities", "Service_Staff", "Location",
            "Food_Beverage", "Price_Value", "General",
        ]
        preds = []
        for cat in CATEGORIES:
            val = result[cat]
            preds.append(1 if val == 1 else 0)  # neg
            preds.append(1 if val == 2 else 0)  # pos

        return {
            "status":      "success",
            "model_used":  data.model_type,
            "predictions": preds,
            "categories":  CATEGORIES,
        }
    except Exception as e:
        log.error(f"/predict error: {e}")
        return {"status": "error", "message": str(e)}


# ── Endpoints mới ────────────────────────────────────────────────────

@app.post("/analyze")
async def analyze_batch(data: AnalyzeBatchInput):
    """
    Phân tích ABSA cho nhiều reviews cùng lúc.
    Trả về predictions + summary scores.
    """
    try:
        predictions = predict_batch(data.reviews, data.model_type)
        summary     = compute_absa_summary(predictions)
        return {
            "status":      "success",
            "total":       len(predictions),
            "predictions": predictions,
            "summary":     summary,
        }
    except Exception as e:
        log.error(f"/analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hotels/search")
async def hotel_search(
    city:             str,
    district:         Optional[str] = None,
    user_request:     Optional[str] = None,
    priority_aspects: str           = "",
    min_score:        float         = 0,
):
    """
    Chế độ 1 — Tìm khách sạn từ database đã phân tích sẵn.
    Trả về danh sách KS kèm match score với yêu cầu user.
    """
    try:
        aspects = [a.strip() for a in priority_aspects.split(",") if a.strip()]
        hotels  = search_hotels(city=city, district=district, min_score=min_score)

        if not hotels:
            return {"status": "success", "total": 0, "hotels": []}

        # Tu dong detect aspects tu user_request neu chua co
        if user_request and not aspects:
            try:
                from predictor import detect_aspects_from_request
                aspects = detect_aspects_from_request(user_request)
                log.info(f"Auto-detected aspects: {aspects}")
            except Exception:
                pass

        # Tính match score cho từng KS
        results = []
        for h in hotels:
            match = compute_match_score(h, user_request or "", aspects)
            results.append({**h, "match_score": match})

        # Sắp xếp theo match score
        results.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "status": "success",
            "total":  len(results),
            "hotels": results,
        }
    except Exception as e:
        log.error(f"/hotels/search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/hotels/analyze-urls")
async def analyze_urls(data: AnalyzeUrlsInput):
    """
    Che do 2 — Cao va phan tich URLs tuy chon cua user.
    Ho tro multi-model: neu models=[...] thi phan tich nhieu model va so sanh.
    Tu dong detect link khu vuc (HOTEL_GEO) va chuyen sang analyze_geo_url.
    """
    if not data.urls:
        raise HTTPException(status_code=400, detail="Can it nhat 1 URL")

    try:
        from crawler import analyze_urls as crawler_analyze

        # Xac dinh models can chay
        models = data.models if data.models else [data.model_type]

        if len(models) > 1:
            # Multi-model: chay tung model, gop ket qua
            model_results = {}
            for m in models:
                results = crawler_analyze(data.urls, data.max_reviews, m)
                for r in results:
                    r["match_score"] = compute_match_score(
                        r.get("scores", {}), data.user_request or "", data.priority_aspects
                    ) if r.get("scores") else 0
                model_results[m] = results
            return {
                "status":  "success",
                "total":   1,
                "results": [{"type": "hotels", "multi_model": True, "models": model_results}],
            }
        else:
            results = crawler_analyze(data.urls, data.max_reviews, models[0])
            for r in results:
                r["match_score"] = compute_match_score(
                    r.get("scores", {}), data.user_request or "", data.priority_aspects
                ) if r.get("scores") else 0
            results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return {
                "status":  "success",
                "total":   len(results),
                "results": results,
            }
    except Exception as e:
        log.error(f"/hotels/analyze-urls error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/hotels/{hotel_id}")
async def hotel_detail(hotel_id: int):
    """Chi tiết khách sạn kèm ABSA scores."""
    hotel = get_hotel_by_id(hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn")
    return {"status": "success", "hotel": hotel}


@app.get("/hotels/{hotel_id}/reviews")
async def hotel_reviews(
    hotel_id:  int,
    aspect:    Optional[str] = None,
    sentiment: Optional[int] = None,
    limit:     int           = Query(default=50, le=200),
):
    """
    Reviews của khách sạn, có filter theo aspect và sentiment.
    sentiment: 1=Negative, 2=Positive
    """
    hotel = get_hotel_by_id(hotel_id)
    if not hotel:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn")

    reviews = get_reviews_by_hotel(hotel_id, aspect, sentiment, limit)
    return {
        "status":   "success",
        "total":    len(reviews),
        "reviews":  reviews,
    }


@app.get("/cities")
async def list_cities():
    """Danh sách thành phố có trong database."""
    cities = get_all_cities()
    return {"status": "success", "cities": cities}


@app.get("/districts/{city}")
async def list_districts(city: str):
    """Danh sách quận/khu vực theo thành phố."""
    districts = get_districts_by_city(city)
    return {"status": "success", "city": city, "districts": districts}


@app.get("/stats")
async def db_stats():
    """Thống kê database."""
    stats = get_db_stats()
    return {"status": "success", "stats": stats}


# ── History & Bookmark endpoints ─────────────────────────────────────

class BookmarkInput(BaseModel):
    hotel_id:    int
    hotel_name:  str  = ""
    hotel_url:   str  = ""
    city:        str  = ""
    match_score: float = 0


@app.post("/user/history")
async def save_history(meta: dict, user: dict = Depends(require_user)):
    """Lưu lịch sử tìm kiếm."""
    try:
        add_search_history(int(user["sub"]), meta)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/user/history")
async def user_history(user: dict = Depends(require_user)):
    """Lấy lịch sử tìm kiếm."""
    history = get_search_history(int(user["sub"]))
    return {"status": "success", "history": history}


@app.post("/user/bookmarks")
async def add_hotel_bookmark(data: BookmarkInput, user: dict = Depends(require_user)):
    """Thêm bookmark KS."""
    add_bookmark(int(user["sub"]), data.dict())
    return {"status": "success"}


@app.delete("/user/bookmarks/{hotel_id}")
async def remove_hotel_bookmark(hotel_id: int, user: dict = Depends(require_user)):
    """Xóa bookmark KS."""
    remove_bookmark(int(user["sub"]), hotel_id)
    return {"status": "success"}


@app.get("/user/bookmarks")
async def user_bookmarks(user: dict = Depends(require_user)):
    """Lấy danh sách bookmark."""
    bookmarks = get_bookmarks(int(user["sub"]))
    return {"status": "success", "bookmarks": bookmarks}


@app.get("/user/bookmarks/{hotel_id}/check")
async def check_bookmark(hotel_id: int, user: dict = Depends(require_user)):
    """Kiểm tra KS đã bookmark chưa."""
    return {"bookmarked": is_bookmarked(int(user["sub"]), hotel_id)}


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
async def root():
    return {
        "name":    "HotelSense ABSA API",
        "version": "2.0.0",
        "docs":    "/docs",
    }