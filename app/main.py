from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_cursor

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title="News Ideology Tracker")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with get_cursor() as cur:
        cur.execute("SELECT id, title, summary, updated_at FROM stories ORDER BY updated_at DESC LIMIT 10")
        stories = cur.fetchall()
    return templates.TemplateResponse(request, "index.html", {"stories": stories})


@app.get("/health")
def health():
    return {"status": "ok"}
