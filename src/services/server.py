"""
server.py

One-script FastAPI app for the Notebook project:
  - Serves the JSON API the frontend calls:
      /api/register, /api/login, /api/logout,
      /api/notes-save, /api/notes-load
  - Serves the frontend itself (register.html, login.html, note.html,
    styles.css, api.js) from the ./frontend folder next to this file.

Run:
    pip install fastapi uvicorn
    python schema.py     # once, to create notebook.db
    python server.py     # starts everything at http://127.0.0.1:8000

Then open http://127.0.0.1:8000 in a browser.

Auth model:
  Login sets a random, HttpOnly session-id cookie. Session -> user_id
  mappings are kept in an in-memory dict, so restarting the server logs
  everyone out. That's a fine trade-off for a simple single-note app;
  swap in a "sessions" table in schema.py if you ever need sessions to
  survive a restart.
"""

import hashlib
import secrets
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from schema import get_connection, init_db

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# server.py lives in src/services/, so .parent.parent gets to src/
VIEWS_DIR = Path(__file__).parent.parent / "views"
STYLES_DIR = Path(__file__).parent.parent / "styles"
SESSION_COOKIE = "session_id"

app = FastAPI(title="Notebook API")

# In-memory session store: {session_id: user_id}.
SESSIONS: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Password hashing — stdlib only, no external crypto dependency.
# PBKDF2-HMAC-SHA256 with a random per-user salt and 200k iterations.
# ---------------------------------------------------------------------------

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000
    )
    return digest.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest, _ = hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class NoteBody(BaseModel):
    content: str = Field(default="", max_length=200_000)


# ---------------------------------------------------------------------------
# Auth helper — every protected route takes the session cookie as a
# parameter and passes it through this.
# ---------------------------------------------------------------------------

def current_user_id(session_id: Optional[str]) -> int:
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return SESSIONS[session_id]


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/register", status_code=201)
def register(creds: Credentials):
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (creds.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="That username is already taken.")

        password_hash, salt = hash_password(creds.password)
        conn.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (creds.username, password_hash, salt),
        )
        conn.commit()
        return {"message": "Account created."}
    finally:
        conn.close()


@app.post("/api/login")
def login(creds: Credentials, response: Response):
    conn = get_connection()
    try:
        user = conn.execute(
            "SELECT id, password_hash, salt FROM users WHERE username = ?",
            (creds.username,),
        ).fetchone()
    finally:
        conn.close()

    if not user or not verify_password(creds.password, user["password_hash"], user["salt"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    session_id = secrets.token_hex(32)
    SESSIONS[session_id] = user["id"]

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
    )
    return {"message": "Logged in."}


@app.post("/api/logout")
def logout(
    response: Response,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    if session_id:
        SESSIONS.pop(session_id, None)
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "Logged out."}


# ---------------------------------------------------------------------------
# Note endpoints — one note per user, upserted on save.
# ---------------------------------------------------------------------------

@app.get("/api/notes-load")
def load_note(session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)):
    user_id = current_user_id(session_id)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM notes WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    return {"content": row["content"] if row else ""}


@app.post("/api/notes-save")
def save_note(
    body: NoteBody,
    session_id: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
):
    user_id = current_user_id(session_id)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO notes (user_id, content, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            (user_id, body.content),
        )
        conn.commit()
    finally:
        conn.close()
    return {"message": "Saved."}


# ---------------------------------------------------------------------------
# Frontend — serve the static files from ./frontend, with "/" sent to
# the login page. This mount must be added last: FastAPI matches routes
# in the order they're registered, so the /api/* routes above and the
# "/" redirect below are matched first, and everything else (login.html,
# note.html, styles.css, api.js) falls through to the static mount.
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return RedirectResponse(url="/login.html")

app.mount("/styles", StaticFiles(directory=STYLES_DIR), name="styles")
app.mount("/", StaticFiles(directory=VIEWS_DIR, html=True), name="views")