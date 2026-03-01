import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import SCRAPE_SECRET, SESSION_COOKIE, SESSION_MAX_AGE
from .db import get_bookmarked_products, get_products, init_db, toggle_bookmark
from .services import run_scrape

PAGE_SIZE = 15


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "static")), name="static")
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, source: str | None = None, page: int = 1):
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())
    products = get_products(source=source, limit=PAGE_SIZE + 1, offset=offset, session_id=session_id)
    has_next = len(products) > PAGE_SIZE
    products = products[:PAGE_SIZE]
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": source or "all",
            "view": "index",
            "page": page,
            "has_next": has_next,
        },
    )
    if SESSION_COOKIE not in request.cookies:
        response.set_cookie(SESSION_COOKIE, session_id, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax")
    return response


@app.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_page(request: Request, page: int = 1):
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE
    session_id = request.cookies.get(SESSION_COOKIE) or str(uuid.uuid4())
    products = get_bookmarked_products(session_id, limit=PAGE_SIZE + 1, offset=offset)
    has_next = len(products) > PAGE_SIZE
    products = products[:PAGE_SIZE]
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": "bookmarks",
            "view": "bookmarks",
            "page": page,
            "has_next": has_next,
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

    return await run_scrape()
