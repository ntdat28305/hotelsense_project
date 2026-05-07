# HotelSense — AI Hotel Review Analyzer

Phân tích cảm xúc đa khía cạnh (ABSA) cho đánh giá khách sạn tiếng Việt.

## Kiến trúc

```
HuggingFace Spaces (Backend)    Railway (Frontend)
────────────────────────────    ──────────────────
FastAPI + PhoBERT/LR        +   React + TailwindCSS
SQLite database                 Giao diện tìm kiếm
```

## Cấu trúc repo

```
lab1/
├── notebooks/          # Training notebooks
├── data/raw/           # Dataset gốc
├── models/baseline/    # LR + TF-IDF models
├── backend/            # FastAPI (deploy HF Spaces)
└── frontend/           # React app (deploy Railway)
```

## Chạy local

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

**Cào data (chạy 1 lần):**
```bash
cd backend
python crawler.py --city hcm --max_hotels 10 --max_reviews 100
```

**Frontend:**
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env
npm run dev
```

## Deploy

**Backend → HuggingFace Spaces:**
- Upload thư mục `backend/` lên HF Space
- Đặt Space type: Docker

**Frontend → Railway:**
- Connect GitHub repo
- Set root directory: `frontend`
- Set env: `VITE_API_URL=https://your-hf-space.hf.space`
