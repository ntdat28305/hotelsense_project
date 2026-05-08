# 🏨 HotelSense — AI Hotel Review Analyzer

> Phân tích hàng nghìn đánh giá thực bằng AI — không chỉ điểm sao

**Live Demo**: [hotelsense283.up.railway.app](https://hotelsense283.up.railway.app)  


---

## 📌 Tổng quan

HotelSense là hệ thống **Aspect-Based Sentiment Analysis (ABSA)** cho đánh giá khách sạn tiếng Việt. Phân tích sâu 6 khía cạnh từ mỗi review: Phòng ốc, Nhân viên, Vị trí, Ăn uống, Giá cả, Tổng thể.

Dự án phát triển trong khuôn khổ môn **Machine Learning** — Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

---

## 🏗 Kiến trúc hệ thống

```
Frontend (React+Vite) → Railway hotelsense283.up.railway.app
         ↓ VITE_API_URL
Backend (FastAPI) → Railway bountiful-spirit-production.up.railway.app
         ↓ hf_hub_download                    ↓ boto3
HuggingFace Hub (quangdao232)         Railway S3 Bucket
- phobert-hotel-absa (540MB)          hotels.db (4MB)
- cnn-lstm-hotel-absa (6MB)           424 KS, 15K reviews
- lr-hotel-absa (3MB)
```

---

## 📁 Cấu trúc

```
hotelsense_project/
├── backend/
│   ├── api.py          # FastAPI 15+ endpoints
│   ├── predictor.py    # 3-model inference pipeline (lazy load từ HF Hub)
│   ├── crawler.py      # Traveloka crawler (Selenium + requests API)
│   ├── database.py     # SQLite schema + S3 download khi startup
│   ├── auth.py         # Google OAuth2 + JWT
│   ├── requirements.txt
│   └── Dockerfile      # Python 3.10, port 8000
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Home.jsx      # 2 chế độ: DB search + URL analyze, AuthModal (createPortal)
│       │   ├── Results.jsx   # Kết quả single/multi-model cards
│       │   ├── Detail.jsx    # Chi tiết KS: radar chart + comments + filter
│       │   └── Profile.jsx   # Lịch sử tìm kiếm + bookmarks
│       ├── components/
│       │   ├── HotelCard.jsx   # Card với aspect badges + bookmark button
│       │   ├── CommentList.jsx # Reviews có filter theo aspect/sentiment
│       │   └── RadarChart.jsx  # SVG custom (không dùng thư viện ngoài)
│       ├── hooks/useAuth.js    # Google OAuth + JWT localStorage
│       └── api.js              # Tất cả fetch calls + authRequest helper
├── notebooks/
│   ├── 01_data_crawl.ipynb    # Thu thập dữ liệu Traveloka
│   ├── 02_process.ipynb       # Tiền xử lý + gán nhãn + EDA
│   └── 03_train_all_models.ipynb  # Training 4 models
└── data/
    └── hotels.db              # Download từ S3 khi deploy
```

---

## 📊 Quy trình xây dựng hệ thống

### Bước 1 — Thu thập dữ liệu (`01_data_crawl.ipynb`)

**Crawl Hotel IDs** bằng Selenium:
```python
# Duyệt từng trang kết quả Traveloka (scroll + wait)
# Parse href: /hotel/vietnam/name-{ID} → lấy hotel_id
driver.get(f"https://www.traveloka.com/vi-vn/hotel/vietnam/region/ho-chi-minh-city-10009794/{page}?viewType=list")
# Regex: r'-(\\d+)(?:\\?|$)'
```

**Crawl Reviews** bằng Traveloka Review API:
```python
POST https://www.traveloka.com/api/v2/ugc/review/consumption/v2/getReviews
# Payload: objectId, productType=HOTEL, limit=40, skip, sort=SORT_CREATED_DESCENDING
# Headers: Cookie (datadome + aws-waf-token), x-domain: ugcReview
# Pagination: hasNext → tăng skip += 40, sleep(1.5-2.5s)
```

**Kết quả thu thập:**
| Thành phố | KS | Reviews |
|-----------|-----|---------|
| Ho Chi Minh City | 173 | ~6,300 |
| Hanoi | 145 | ~5,200 |
| Da Nang | 106 | ~3,800 |
| **Tổng** | **424** | **~15,355** |

---

### Bước 2 — Tiền xử lý & Gán nhãn (`02_process.ipynb`)

**Làm sạch văn bản:**
```python
def clean_vietnamese_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)       # Xóa ký tự đặc biệt
    words = [teencode_dict.get(w, w) for w in text.split()]  # Teencode → chuẩn
    return word_tokenize(text, format="text")  # underthesea tokenizer
# Teencode dict: "ks"→"khách sạn", "ko"→"không", "nv"→"nhân viên", ...
```

**Lọc trùng lặp ngữ nghĩa:**
```python
# TF-IDF + Cosine Similarity, threshold=0.8
def drop_duplicates_by_threshold(df, threshold=0.8):
    cosine_sim = cosine_similarity(tfidf_matrix)
    # Xóa các cặp tương đồng > 0.8
```

**Gán nhãn bằng Label Studio:**
- Export JSON → parse về format chuẩn
- Mapping: `Room→Room_Facilities, Service→Service_Staff, Food→Food_Beverage, Price→Price_Value`
- Sentiment: `Positive=2, Negative=1, None=0`

**Tạo ma trận nhãn:**
```python
# Output: CSV với columns [text, Room_Facilities, Service_Staff, Location, Food_Beverage, Price_Value, General]
# Values: 0=None, 1=Negative, 2=Positive
```

**Thống kê EDA:**
- Độ dài review: mean ~25 từ/câu, min 1, max 200+
- Tỉ lệ Positive >> Negative (đặc trưng review khách sạn)
- Aspect phổ biến nhất: Service_Staff, General

**Dataset split:** 70% Train / 15% Val / 15% Test

---

### Bước 3 — Training Models (`03_train_all_models.ipynb`)

#### 3.1 Logistic Regression (Baseline)
```python
TfidfVectorizer(max_features=15000, ngram_range=(1,2), sublinear_tf=True, min_df=2)
LogisticRegression(C=1.0, max_iter=1000, class_weight='balanced', solver='lbfgs')
# 6 classifiers riêng cho 6 categories
```

#### 3.2 Random Forest (Baseline)
```python
RandomForestClassifier(n_estimators=200, class_weight='balanced', n_jobs=-1)
# Cùng TF-IDF vectorizer với LR
```

#### 3.3 CNN-LSTM (Deep Learning)
```python
# Hyperparameters
CNN_CFG = {
    'max_words': 15000, 'max_len': 128,
    'embed_dim': 128, 'num_filters': 128, 'kernel_size': 3,
    'hidden_dim': 256, 'dropout': 0.3,
    'batch_size': 64, 'epochs': 15, 'patience': 5, 'lr': 0.001
}

# Architecture
class CNN_LSTM_ABSA(nn.Module):
    Embedding(vocab_size, embed_dim)
    → Conv1D(embed_dim, num_filters, kernel_size) + BatchNorm1d
    → BiLSTM(num_filters, hidden_dim)
    → Dropout → FC(hidden_dim*2, 12)  # 6 categories × 2 (neg/pos)

# Training: Adam + ReduceLROnPlateau(patience=2, factor=0.5)
# Loss: BCEWithLogitsLoss, EarlyStopping patience=5
# Keras Tokenizer để tokenize (cần tensorflow để load pkl)
```

#### 3.4 PhoBERT (Transformer)
```python
# Base: vinai/phobert-base
PB_CFG = {
    'max_length': 256, 'batch_size': 16,
    'epochs': 10, 'lr': 2e-5
}
# Output: 18 logits = 6 categories × 3 classes (None/Neg/Pos)
# Cần GPU để train (~2-4 giờ trên T4)
# Fine-tune với HuggingFace Trainer API
```

**Metrics đánh giá (macro F1 trên test set):**
| Model | Room | Staff | Location | Food | Price | General | **Avg F1** |
|-------|------|-------|----------|------|-------|---------|-----------|
| Logistic Regression | - | - | - | - | - | - | ~65% |
| Random Forest | - | - | - | - | - | - | ~60% |
| CNN-LSTM | - | - | - | - | - | - | ~70% |
| **PhoBERT** | - | - | - | - | - | - | **~75%** |

*(Kết quả chi tiết xem trong `results/` sau khi chạy notebook)*

---

## 🤖 Models (Production)

### PhoBERT (`quangdao232/phobert-hotel-absa`)
- Output shape: `[1, 18]` = 6×3 classes
- Parse: `logits[i*3:(i+1)*3]` → argmax cho mỗi category
- Load time: ~30-60s lần đầu (download 540MB)

### CNN-LSTM (`quangdao232/cnn-lstm-hotel-absa`)
- Output shape: `[1, 12]` = 6×2 logits (neg/pos)
- Parse: sigmoid → threshold 0.3 cho mỗi cặp
- Cần `tensorflow` để load `keras_tokenizer.pkl`

### Logistic Regression (`quangdao232/lr-hotel-absa`)
- Files: `tfidf_vectorizer.pkl`, `logistic_regression_models.pkl`
- models là dict `{category: LR_model}`
- Nhanh nhất, không cần GPU

### Inference Pipeline (`predictor.py`)
```python
# Lazy loading — download từ HF Hub lần đầu, cache trong RAM
predict_batch(texts, model_type) → list[{category: 0/1/2}]
compute_absa_summary(preds) → {room_positive_pct, ..., overall_score, total_analyzed}
compute_match_score(scores, priority_aspects) → float
# Score = weighted_avg(aspects, weights) * (0.7 + 0.3 * log_confidence)
# Priority weight = 3.0x, default weight = 1.0x
```

---

## 🗄 Database (`database.py`)

```sql
hotels(id, name, url, city, district, address, stars, total_reviews, analyzed)
absa_scores(hotel_id, model_type,
    room/staff/location/food/price/general _positive/negative_pct,
    overall_score, total_analyzed)
reviews(id, hotel_id, text, reviewer_name, review_date,
    room_facilities, service_staff, location, food_beverage, price_value, general)
    -- Values: 0=None, 1=Negative, 2=Positive
users(id, google_id, email, name, avatar, created_at, last_login)
search_history(id, user_id, mode, city, district, aspects JSON, models JSON, urls JSON, created_at)
bookmarks(id, user_id, hotel_id, hotel_name, hotel_url, city, match_score, created_at)
```

**S3 download khi startup:**
```python
def download_db_from_bucket():  # gọi trong init_db()
    s3.download_file(bucket, "hotels.db", DB_PATH)
    # Env: S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET
```

---

## 🔗 Crawler (`crawler.py`)

**Crawl hotel IDs** — Selenium + undetected_chromedriver (bypass CloudFront WAF):
```python
scrape_district(driver, url, city_key, district_name)
# Parse href /hotel/vietnam/name-{ID} từ HTML sau khi scroll
```

**Crawl reviews** — requests trực tiếp vào API:
```python
crawl_hotel_reviews(hotel_id, max_reviews)
# POST traveloka.com/api/v2/ugc/review/consumption/v2/getReviews
# Cookie expire vài giờ → update TRAVELOKA_COOKIES trong Railway Variables
```

**Parse URL Traveloka:**
```python
parse_traveloka_url(url) → (hotel_id, hotel_name)
# Dạng 1: /hotel/detail?spec=...HOTEL.{ID}.{Name}...
# Dạng 2: /vi-vn/hotel/vietnam/name-{ID}
# Dùng unquote() trước để xử lý %26 trong tên có ký tự đặc biệt
```

---

## 🔐 Auth (`auth.py`)

```
click "Đăng nhập" → GET /auth/google/login → redirect Google OAuth
→ callback /auth/google/callback?code=...
→ POST Google token endpoint → access_token
→ GET Google userinfo → {id, email, name, picture}
→ upsert users table → create JWT (expire 30 ngày)
→ redirect FRONTEND_URL?token=JWT
→ frontend: localStorage.setItem("hs_token", token)
→ mọi request sau: Authorization: Bearer JWT
```

---

## 🌐 API Endpoints

```
GET  /hotels/search?city=&district=&priority_aspects=&min_score=
POST /hotels/analyze-urls   {urls, max_reviews, models[], priority_aspects[]}
GET  /hotels/{id}
GET  /hotels/{id}/reviews?aspect=&sentiment=&limit=
GET  /auth/google/login
GET  /auth/google/callback
GET  /auth/me                 [JWT required]
POST /user/history            [JWT required]
GET  /user/history            [JWT required]
POST /user/bookmarks          [JWT required]
DELETE /user/bookmarks/{id}   [JWT required]
GET  /user/bookmarks          [JWT required]
GET  /stats
GET  /cities
GET  /districts/{city}
GET  /health
```

---

## ☁️ Deploy

### Railway Variables — Backend (`bountiful-spirit`)
```
DB_PATH=/app/data/hotels.db
HF_TOKEN=<token quangdao232>
TRAVELOKA_COOKIES=<copy từ DevTools → Network → cookie header>
GOOGLE_CLIENT_ID=824012651207-6nn7ev2peigkk6g459ljuqrf4a4donp2.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=https://bountiful-spirit-production.up.railway.app/auth/google/callback
FRONTEND_URL=https://hotelsense283.up.railway.app
JWT_SECRET=<random string>
S3_ENDPOINT=https://t3.storageapi.dev
S3_ACCESS_KEY=tid_rGjLAZfc...
S3_SECRET_KEY=tsec_VsXSeyf...
S3_BUCKET=resilient-drum-ws2x5wnd3f
```

### Railway Variables — Frontend (`hotelsense_project`)
```
VITE_API_URL=https://bountiful-spirit-production.up.railway.app
```

### Google Cloud Console
- Project: `hotelsense`
- Authorized redirect URIs: `https://bountiful-spirit-production.up.railway.app/auth/google/callback`
- Authorized JS origins: `https://hotelsense283.up.railway.app`

---

## 🔄 Maintenance

**Cập nhật Cookie Traveloka** (khi phân tích link bị lỗi 404):
1. Chrome → traveloka.com → F12 → Network → copy header `Cookie`
2. Railway → `bountiful-spirit` → Variables → update `TRAVELOKA_COOKIES`

**Cập nhật Database:**
```python
import boto3
s3 = boto3.client('s3', endpoint_url='https://t3.storageapi.dev',
    aws_access_key_id='...', aws_secret_access_key='...')
s3.upload_file('data/hotels.db', 'resilient-drum-ws2x5wnd3f', 'hotels.db')
# Railway restart → tự download DB mới
```

---

## ⚠️ Known Issues

1. **PhoBERT lần đầu chậm** (~30-60s) do download 540MB, các lần sau cache trong RAM
2. **Railway restart** → mất cache → chậm lại lần đầu
3. **CNN-LSTM** kết quả chưa tối ưu (sigmoid threshold cần tune thêm)
4. **Traveloka Cookie** expire sau vài giờ → cần update thủ công
5. **HF Token** của `quangdao232` nếu expire → models không load → predict trả 0

---
