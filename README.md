# 🏨 HotelSense — AI Hotel Review Analyzer

> Phân tích hàng nghìn đánh giá thực bằng AI — không chỉ điểm sao

**Live Demo**: [hotelsense283.up.railway.app](https://hotelsense283.up.railway.app)

---

## 📌 Giới thiệu

HotelSense là hệ thống phân tích cảm xúc đa khía cạnh (Aspect-Based Sentiment Analysis - ABSA) cho đánh giá khách sạn tiếng Việt. Thay vì chỉ hiển thị điểm sao tổng quát, HotelSense phân tích sâu từng khía cạnh cụ thể của trải nghiệm lưu trú.

Dự án được phát triển trong khuôn khổ môn học **Machine Learning** — Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

---

## ✨ Tính năng

### 🗄 Tìm từ Database
- Tìm kiếm khách sạn từ database đã phân tích sẵn (424 KS tại HCM, Hà Nội, Đà Nẵng)
- Lọc theo thành phố, quận/khu vực
- Chọn khía cạnh ưu tiên để tính điểm phù hợp

### 🔗 Phân tích theo Link
- Paste link Traveloka bất kỳ → crawl reviews realtime → phân tích ABSA
- Hỗ trợ so sánh song song nhiều model AI
- Xem chi tiết từng review đã được gán nhãn

### 🤖 3 Model AI
| Model | Đặc điểm |
|-------|----------|
| **PhoBERT** | Transformer tiếng Việt, kết quả tốt nhất |
| **CNN-LSTM** | Mạng tích chập + LSTM, cân bằng tốc độ/độ chính xác |
| **Logistic Regression** | Nhanh nhất, phù hợp baseline |

### 📊 Phân tích 6 Khía cạnh
- 🛏 **Phòng ốc** — chất lượng phòng, tiện nghi
- 👤 **Nhân viên** — thái độ phục vụ, chuyên nghiệp
- 📍 **Vị trí** — địa điểm, giao thông
- 🍽 **Ăn uống** — buffet, nhà hàng, bữa sáng
- 💰 **Giá cả** — giá trị so với chi phí
- ⭐ **Tổng thể** — đánh giá chung

### 👤 Tài khoản người dùng
- Đăng nhập bằng Google OAuth
- Lưu lịch sử tìm kiếm
- Bookmark khách sạn yêu thích
- Trang cá nhân

---

## 🏗 Kiến trúc hệ thống

```
Frontend (React + Vite)          Backend (FastAPI)
Railway                    →     Railway
hotelsense283.up.railway.app      bountiful-spirit-production.up.railway.app

                                  ↓ Download models
                            HuggingFace Hub (quangdao232)
                            - phobert-hotel-absa
                            - cnn-lstm-hotel-absa
                            - lr-hotel-absa

                                  ↓ Database
                            Railway S3 Bucket
                            - hotels.db (424 KS, 15,355 reviews)
```

---

## 🗂 Cấu trúc Project

```
hotelsense_project/
├── backend/
│   ├── api.py          # FastAPI endpoints
│   ├── predictor.py    # 3-model inference pipeline
│   ├── crawler.py      # Traveloka crawler
│   ├── database.py     # SQLite + S3 helpers
│   ├── auth.py         # Google OAuth + JWT
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx
│       │   ├── Results.jsx
│       │   ├── Detail.jsx
│       │   └── Profile.jsx
│       ├── components/
│       │   ├── HotelCard.jsx
│       │   ├── CommentList.jsx
│       │   └── RadarChart.jsx
│       └── hooks/
│           └── useAuth.js
└── data/
    └── hotels.db
```

---

## 🚀 Chạy Local

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## 📊 Dataset

| Thành phố | Số KS | Số Reviews |
|-----------|-------|------------|
| Ho Chi Minh City | 173 | ~6,300 |
| Hanoi | 145 | ~5,200 |
| Da Nang | 106 | ~3,800 |
| **Tổng** | **424** | **~15,355** |

Dữ liệu crawled từ Traveloka, dùng cho mục đích nghiên cứu học thuật.

---

## 🔧 API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/hotels/search` | Tìm KS từ DB |
| POST | `/hotels/analyze-urls` | Phân tích link Traveloka |
| GET | `/hotels/{id}` | Chi tiết KS |
| GET | `/hotels/{id}/reviews` | Reviews đã gán nhãn |
| GET | `/auth/google/login` | Google OAuth |
| GET | `/auth/me` | Thông tin user |
| GET | `/user/history` | Lịch sử tìm kiếm |
| GET | `/user/bookmarks` | KS yêu thích |
| GET | `/stats` | Thống kê DB |

---

## 👨‍💻 Tác giả

**Nguyễn Thành Đạt**  
Sinh viên năm 3 — Khoa học Tự nhiên, ĐHQG-HCM  

---

## 📄 License

Dự án này được phát triển cho mục đích học thuật.