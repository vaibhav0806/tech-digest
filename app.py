import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from db import (
    get_bookmarked_products,
    get_conn,
    get_products,
    init_db,
    log_scrape_end,
    log_scrape_start,
    toggle_bookmark,
    upsert_product,
)
from scraper import scrape_hn, scrape_ph
from telegram import send_telegram_digest

SCRAPE_SECRET = os.environ.get("SCRAPE_SECRET", "")
SESSION_COOKIE = "session_id"
SESSION_MAX_AGE = 365 * 24 * 60 * 60  # 1 year



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, source: str | None = None):
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())
    products = get_products(source=source, session_id=session_id)
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": source or "all",
            "page": "index",
        },
    )
    if SESSION_COOKIE not in request.cookies:
        response.set_cookie(SESSION_COOKIE, session_id, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax")
    return response


@app.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_page(request: Request):
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())
    products = get_bookmarked_products(session_id)
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": "bookmarks",
            "page": "bookmarks",
        },
    )
    if SESSION_COOKIE not in request.cookies:
        response.set_cookie(SESSION_COOKIE, session_id, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax")
    return response


@app.post("/bookmark/{product_id}")
async def bookmark(request: Request, product_id: int):
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        raise HTTPException(400, "No session cookie")
    is_bookmarked = toggle_bookmark(product_id, session_id)
    return JSONResponse({"bookmarked": is_bookmarked})


@app.post("/scrape")
async def trigger_scrape(authorization: str = Header(None)):
    if not SCRAPE_SECRET:
        raise HTTPException(503, "SCRAPE_SECRET not configured")
    if authorization != f"Bearer {SCRAPE_SECRET}":
        raise HTTPException(401, "Invalid secret")

    async def do_scrape(source_name, coro):
        log_id = log_scrape_start(source_name)
        try:
            items = await coro
            conn = get_conn()
            for item in items:
                upsert_product(conn, item)
            conn.commit()
            conn.close()
            log_scrape_end(log_id, len(items))
            return len(items)
        except Exception as e:
            log_scrape_end(log_id, 0, f"error: {e}")
            return 0

    hn_top = await do_scrape("hn_top", scrape_hn("top"))
    hn_show = await do_scrape("hn_show", scrape_hn("show"))
    ph = await do_scrape("ph", scrape_ph())

    await send_telegram_digest()

    return {"hn_top": hn_top, "hn_show": hn_show, "ph": ph}
