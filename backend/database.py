"""
database.py — SQLite schema và helper functions
Lưu trữ dữ liệu khách sạn đã cào và phân tích sẵn

Chạy độc lập để khởi tạo DB:
    python database.py
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional

DB_PATH = os.environ.get("DB_PATH", "../data/hotels.db")

# ── Download DB từ Railway Bucket khi startup ────────────────────────

def download_db_from_bucket():
    """Tải hotels.db từ Railway S3 Bucket nếu chưa có local."""
    import os, boto3
    from botocore.exceptions import ClientError

    endpoint   = os.environ.get("S3_ENDPOINT",   "https://t3.storageapi.dev")
    access_key = os.environ.get("S3_ACCESS_KEY",  "")
    secret_key = os.environ.get("S3_SECRET_KEY",  "")
    bucket     = os.environ.get("S3_BUCKET",      "")
    db_path    = os.environ.get("DB_PATH",         "/app/data/hotels.db")

    if not all([access_key, secret_key, bucket]):
        print("[S3] Credentials not set, skipping download")
        return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path) and os.path.getsize(db_path) > 1000:
        print(f"[S3] DB already exists at {db_path}, skipping download")
        return

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        print(f"[S3] Downloading hotels.db from bucket {bucket}...")
        s3.download_file(bucket, "hotels.db", db_path)
        print(f"[S3] Downloaded to {db_path} ({os.path.getsize(db_path)} bytes)")
    except ClientError as e:
        print(f"[S3] Download failed: {e}")



CATEGORIES = [
    "Room_Facilities",
    "Service_Staff",
    "Location",
    "Food_Beverage",
    "Price_Value",
    "General",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS hotels (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    url             TEXT    UNIQUE NOT NULL,
    city            TEXT    NOT NULL,
    district        TEXT,
    address         TEXT,
    stars           INTEGER DEFAULT 0,
    booking_score   REAL    DEFAULT 0,
    total_reviews   INTEGER DEFAULT 0,
    crawled_at      TEXT,
    analyzed        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id        INTEGER NOT NULL REFERENCES hotels(id),
    text            TEXT    NOT NULL,
    reviewer_name   TEXT,
    review_date     TEXT,
    room_facilities INTEGER DEFAULT 0,
    service_staff   INTEGER DEFAULT 0,
    location        INTEGER DEFAULT 0,
    food_beverage   INTEGER DEFAULT 0,
    price_value     INTEGER DEFAULT 0,
    general         INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS absa_scores (
    hotel_id                INTEGER PRIMARY KEY REFERENCES hotels(id),
    room_positive_pct       REAL DEFAULT 0,
    room_negative_pct       REAL DEFAULT 0,
    staff_positive_pct      REAL DEFAULT 0,
    staff_negative_pct      REAL DEFAULT 0,
    location_positive_pct   REAL DEFAULT 0,
    location_negative_pct   REAL DEFAULT 0,
    food_positive_pct       REAL DEFAULT 0,
    food_negative_pct       REAL DEFAULT 0,
    price_positive_pct      REAL DEFAULT 0,
    price_negative_pct      REAL DEFAULT 0,
    general_positive_pct    REAL DEFAULT 0,
    general_negative_pct    REAL DEFAULT 0,
    overall_score           REAL DEFAULT 0,
    total_analyzed          INTEGER DEFAULT 0,
    updated_at              TEXT
);

CREATE INDEX IF NOT EXISTS idx_hotels_city     ON hotels(city);
CREATE INDEX IF NOT EXISTS idx_hotels_district ON hotels(district);
CREATE INDEX IF NOT EXISTS idx_reviews_hotel   ON reviews(hotel_id);
"""


@contextmanager
def get_conn(db_path: str = DB_PATH):
    """Context manager trả về SQLite connection."""
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DB_PATH):
    """Khởi tạo database và tạo tables."""
    download_db_from_bucket()
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)
    print(f"[DB] Khởi tạo xong: {db_path}")


def upsert_hotel(hotel: dict, db_path: str = DB_PATH) -> int:
    """Thêm hoặc cập nhật khách sạn. Trả về hotel_id."""
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO hotels (name, url, city, district, address, stars, booking_score, crawled_at)
            VALUES (:name, :url, :city, :district, :address, :stars, :booking_score, datetime('now'))
            ON CONFLICT(url) DO UPDATE SET
                name          = excluded.name,
                district      = excluded.district,
                address       = excluded.address,
                stars         = excluded.stars,
                booking_score = excluded.booking_score,
                crawled_at    = datetime('now')
        """, hotel)
        row = conn.execute("SELECT id FROM hotels WHERE url = ?", (hotel["url"],)).fetchone()
        return row["id"]


def get_hotel_by_id(hotel_id: int, db_path: str = DB_PATH) -> Optional[dict]:
    """Lấy thông tin hotel kèm absa_scores theo id."""
    with get_conn(db_path) as conn:
        row = conn.execute("""
            SELECT h.*, s.overall_score,
                   s.room_positive_pct, s.room_negative_pct,
                   s.staff_positive_pct, s.staff_negative_pct,
                   s.location_positive_pct, s.location_negative_pct,
                   s.food_positive_pct, s.food_negative_pct,
                   s.price_positive_pct, s.price_negative_pct,
                   s.general_positive_pct, s.general_negative_pct,
                   s.total_analyzed
            FROM hotels h
            LEFT JOIN absa_scores s ON s.hotel_id = h.id
            WHERE h.id = ?
        """, (hotel_id,)).fetchone()
        return dict(row) if row else None


def search_hotels(
    city: str,
    district: str = None,
    min_score: float = 0,
    db_path: str = DB_PATH,
) -> list:
    """Tìm khách sạn đã phân tích sẵn theo city/district."""
    query = """
        SELECT h.*, s.overall_score,
               s.room_positive_pct, s.staff_positive_pct,
               s.location_positive_pct, s.food_positive_pct,
               s.price_positive_pct, s.general_positive_pct,
               s.total_analyzed
        FROM hotels h
        JOIN absa_scores s ON s.hotel_id = h.id
        WHERE h.city = ?
          AND h.analyzed = 1
          AND s.overall_score >= ?
    """
    params = [city, min_score]
    if district:
        query += " AND h.district = ?"
        params.append(district)
    query += " ORDER BY s.overall_score DESC"

    with get_conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_reviews_by_hotel(
    hotel_id: int,
    aspect: str = None,
    sentiment: int = None,
    limit: int = 50,
    db_path: str = DB_PATH,
) -> list:
    """
    Lấy reviews của hotel, có thể filter theo aspect và sentiment.
    sentiment: 1=Negative, 2=Positive, None=tất cả
    """
    col_map = {
        "Room_Facilities": "room_facilities",
        "Service_Staff":   "service_staff",
        "Location":        "location",
        "Food_Beverage":   "food_beverage",
        "Price_Value":     "price_value",
        "General":         "general",
    }

    query = "SELECT * FROM reviews WHERE hotel_id = ?"
    params = [hotel_id]

    if aspect and aspect in col_map:
        col = col_map[aspect]
        if sentiment is not None:
            query += f" AND {col} = ?"
            params.append(sentiment)
        else:
            query += f" AND {col} != 0"

    query += f" ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with get_conn(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_all_cities(db_path: str = DB_PATH) -> list:
    """Lấy danh sách thành phố có trong DB."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT city FROM hotels WHERE analyzed = 1 ORDER BY city"
        ).fetchall()
        return [r["city"] for r in rows]


def get_districts_by_city(city: str, db_path: str = DB_PATH) -> list:
    """Lấy danh sách quận theo thành phố."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT district FROM hotels WHERE city = ? AND district IS NOT NULL ORDER BY district",
            (city,)
        ).fetchall()
        return [r["district"] for r in rows]


def save_absa_scores(hotel_id: int, scores: dict, db_path: str = DB_PATH):
    """Lưu điểm ABSA tổng hợp cho hotel và đánh dấu analyzed=1."""
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO absa_scores (
                hotel_id,
                room_positive_pct, room_negative_pct,
                staff_positive_pct, staff_negative_pct,
                location_positive_pct, location_negative_pct,
                food_positive_pct, food_negative_pct,
                price_positive_pct, price_negative_pct,
                general_positive_pct, general_negative_pct,
                overall_score, total_analyzed, updated_at
            ) VALUES (
                :hotel_id,
                :room_positive_pct, :room_negative_pct,
                :staff_positive_pct, :staff_negative_pct,
                :location_positive_pct, :location_negative_pct,
                :food_positive_pct, :food_negative_pct,
                :price_positive_pct, :price_negative_pct,
                :general_positive_pct, :general_negative_pct,
                :overall_score, :total_analyzed, datetime('now')
            )
            ON CONFLICT(hotel_id) DO UPDATE SET
                room_positive_pct       = excluded.room_positive_pct,
                room_negative_pct       = excluded.room_negative_pct,
                staff_positive_pct      = excluded.staff_positive_pct,
                staff_negative_pct      = excluded.staff_negative_pct,
                location_positive_pct   = excluded.location_positive_pct,
                location_negative_pct   = excluded.location_negative_pct,
                food_positive_pct       = excluded.food_positive_pct,
                food_negative_pct       = excluded.food_negative_pct,
                price_positive_pct      = excluded.price_positive_pct,
                price_negative_pct      = excluded.price_negative_pct,
                general_positive_pct    = excluded.general_positive_pct,
                general_negative_pct    = excluded.general_negative_pct,
                overall_score           = excluded.overall_score,
                total_analyzed          = excluded.total_analyzed,
                updated_at              = datetime('now')
        """, {"hotel_id": hotel_id, **scores})

        conn.execute(
            "UPDATE hotels SET analyzed = 1 WHERE id = ?", (hotel_id,)
        )


def insert_reviews_batch(hotel_id: int, reviews: list, db_path: str = DB_PATH):
    """Lưu nhiều reviews cùng lúc."""
    with get_conn(db_path) as conn:
        conn.executemany("""
            INSERT INTO reviews
                (hotel_id, text, reviewer_name, review_date,
                 room_facilities, service_staff, location,
                 food_beverage, price_value, general)
            VALUES
                (:hotel_id, :text, :reviewer_name, :review_date,
                 :room_facilities, :service_staff, :location,
                 :food_beverage, :price_value, :general)
        """, [{"hotel_id": hotel_id, **r} for r in reviews])

        conn.execute(
            "UPDATE hotels SET total_reviews = (SELECT COUNT(*) FROM reviews WHERE hotel_id = ?) WHERE id = ?",
            (hotel_id, hotel_id)
        )


def get_db_stats(db_path: str = DB_PATH) -> dict:
    """Thống kê tổng quan database."""
    with get_conn(db_path) as conn:
        hotels_total = conn.execute("SELECT COUNT(*) FROM hotels").fetchone()[0]
        hotels_analyzed = conn.execute("SELECT COUNT(*) FROM hotels WHERE analyzed=1").fetchone()[0]
        reviews_total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        cities = conn.execute(
            "SELECT city, COUNT(*) as cnt FROM hotels WHERE analyzed=1 GROUP BY city"
        ).fetchall()
        return {
            "hotels_total":    hotels_total,
            "hotels_analyzed": hotels_analyzed,
            "reviews_total":   reviews_total,
            "by_city":         {r["city"]: r["cnt"] for r in cities},
        }


# ── History & Bookmark ───────────────────────────────────────────────

def ensure_user_tables(db_path: str = DB_PATH):
    """Tạo bảng search_history và bookmarks nếu chưa có."""
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                mode       TEXT,
                city       TEXT,
                district   TEXT,
                aspects    TEXT,
                models     TEXT,
                urls       TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                hotel_id   INTEGER,
                hotel_name TEXT,
                hotel_url  TEXT,
                city       TEXT,
                match_score REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, hotel_id)
            )
        """)
        conn.commit()


def add_search_history(user_id: int, meta: dict, db_path: str = DB_PATH):
    import json
    ensure_user_tables(db_path)
    with get_conn(db_path) as conn:
        conn.execute("""
            INSERT INTO search_history (user_id, mode, city, district, aspects, models, urls)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            meta.get("mode", ""),
            meta.get("city", ""),
            meta.get("district", ""),
            json.dumps(meta.get("aspects", []), ensure_ascii=False),
            json.dumps(meta.get("models", []), ensure_ascii=False),
            json.dumps(meta.get("urls", []), ensure_ascii=False),
        ))
        conn.commit()


def get_search_history(user_id: int, limit: int = 20, db_path: str = DB_PATH) -> list:
    import json
    ensure_user_tables(db_path)
    with get_conn(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM search_history WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            for key in ["aspects", "models", "urls"]:
                try: item[key] = json.loads(item[key] or "[]")
                except: item[key] = []
            result.append(item)
        return result


def add_bookmark(user_id: int, hotel: dict, db_path: str = DB_PATH) -> bool:
    ensure_user_tables(db_path)
    try:
        with get_conn(db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO bookmarks (user_id, hotel_id, hotel_name, hotel_url, city, match_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                hotel.get("id"),
                hotel.get("name", ""),
                hotel.get("url", ""),
                hotel.get("city", ""),
                hotel.get("match_score", 0),
            ))
            conn.commit()
        return True
    except Exception:
        return False


def remove_bookmark(user_id: int, hotel_id: int, db_path: str = DB_PATH) -> bool:
    ensure_user_tables(db_path)
    with get_conn(db_path) as conn:
        conn.execute("DELETE FROM bookmarks WHERE user_id = ? AND hotel_id = ?", (user_id, hotel_id))
        conn.commit()
    return True


def get_bookmarks(user_id: int, db_path: str = DB_PATH) -> list:
    ensure_user_tables(db_path)
    with get_conn(db_path) as conn:
        rows = conn.execute("""
            SELECT * FROM bookmarks WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def is_bookmarked(user_id: int, hotel_id: int, db_path: str = DB_PATH) -> bool:
    ensure_user_tables(db_path)
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM bookmarks WHERE user_id = ? AND hotel_id = ?", (user_id, hotel_id)
        ).fetchone()
        return row is not None


if __name__ == "__main__":
    init_db()
    stats = get_db_stats()
    print(f"[DB Stats] Hotels: {stats['hotels_total']} | Reviews: {stats['reviews_total']}")