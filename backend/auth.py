"""
auth.py — Google OAuth2 + JWT authentication
"""

import os
import jwt
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.environ.get(
    "GOOGLE_REDIRECT_URI",
    "https://ntdat232-hotel-absa-api.hf.space/auth/google/callback"
)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://hotelsense283.up.railway.app")
JWT_SECRET   = os.environ.get("JWT_SECRET", "hotelsense-secret-key-change-in-prod")
JWT_EXPIRE_DAYS = 30

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v2/userinfo"

router   = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


# ── DB helpers ───────────────────────────────────────────────────────

def ensure_users_table():
    from database import get_connection
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id  TEXT UNIQUE,
                email      TEXT UNIQUE NOT NULL,
                name       TEXT,
                avatar     TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                last_login TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def upsert_user(google_id: str, email: str, name: str, avatar: str) -> dict:
    from database import get_connection
    ensure_users_table()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (google_id, email, name, avatar, last_login)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(google_id) DO UPDATE SET
                name       = excluded.name,
                avatar     = excluded.avatar,
                last_login = datetime('now')
        """, (google_id, email, name, avatar))
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        ).fetchone()
        return dict(row) if row else {}


def get_user_by_id(user_id: int) -> Optional[dict]:
    from database import get_connection
    ensure_users_table()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


# ── JWT helpers ──────────────────────────────────────────────────────

def create_jwt(user: dict) -> str:
    payload = {
        "sub":    str(user["id"]),
        "email":  user["email"],
        "name":   user.get("name", ""),
        "avatar": user.get("avatar", ""),
        "exp":    datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_jwt(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None


# ── Dependency: get current user ────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    if not credentials:
        return None
    payload = decode_jwt(credentials.credentials)
    if not payload:
        return None
    return payload


async def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    user = await get_current_user(credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Cần đăng nhập")
    return user


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    """Redirect user đến Google OAuth consent screen."""
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None):
    """Google callback — đổi code lấy token, tạo JWT, redirect về FE."""
    if error or not code:
        return RedirectResponse(f"{FRONTEND_URL}?auth=error")

    async with httpx.AsyncClient() as client:
        # Đổi code lấy access token
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  GOOGLE_REDIRECT_URI,
            "grant_type":    "authorization_code",
        })
        token_data = token_resp.json()
        access_token = token_data.get("access_token")

        if not access_token:
            log.error(f"Token error: {token_data}")
            return RedirectResponse(f"{FRONTEND_URL}?auth=error")

        # Lấy thông tin user từ Google
        user_resp = await client.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        guser = user_resp.json()

    # Lưu/cập nhật user vào DB
    user = upsert_user(
        google_id = guser.get("id", ""),
        email     = guser.get("email", ""),
        name      = guser.get("name", ""),
        avatar    = guser.get("picture", ""),
    )

    # Tạo JWT và redirect về frontend
    token = create_jwt(user)
    return RedirectResponse(f"{FRONTEND_URL}?token={token}")


@router.get("/me")
async def get_me(user: dict = Depends(require_user)):
    """Lấy thông tin user hiện tại từ JWT."""
    return {"status": "success", "user": user}


@router.post("/logout")
async def logout():
    """Logout — FE tự xóa token."""
    return {"status": "success", "message": "Đã đăng xuất"}