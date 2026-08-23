"""
app.py - TaskMining Server エントリーポイント
================================================
役割:
  - FastAPIアプリの初期化
  - ミドルウェア(キャッシュ無効化など)の設定
  - HTMLフロントエンドの配信 (/dashboard, /login 等)
  - 分割された各Routerのマウント
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from database import init_db
from routers import admin, auth, settings, logs, dashboard

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("DATABASE_URL"):
        init_db()
    yield

app = FastAPI(title="TaskMining Central Server", lifespan=lifespan)

# 静的ファイルの配信
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    """HTMLやJSファイルのブラウザキャッシュを無効化する"""
    response = await call_next(request)
    ctype = response.headers.get("Content-Type", "")
    if "text/html" in ctype or "application/javascript" in ctype or request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ===========================
# HTML 画面配信ルート
# ===========================

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return FileResponse("static/login.html")

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    with open(os.path.join("static", "dashboard.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/user_dashboard", response_class=HTMLResponse)
async def get_user_dashboard():
    with open(os.path.join("static", "user_dashboard.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/settings", response_class=HTMLResponse)
async def get_settings():
    with open(os.path.join("static", "settings.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    with open(os.path.join("static", "login.html"), "r", encoding="utf-8") as f:
        return f.read()

# ===========================
# API ルーターの登録
# ===========================

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(logs.router)
app.include_router(dashboard.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
