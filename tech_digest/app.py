import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import SCRAPE_SECRET, SESSION_COOKIE, SESSION_MAX_AGE, SITE_URL
from .db import get_bookmarked_products, get_last_scraped_at, get_products, init_db, toggle_bookmark
from .services import run_scrape

PAGE_SIZE = 15

_TITLES = {
    "all": "Tech Digest — Top Stories from Hacker News & Product Hunt",
    "hn": "Hacker News — Tech Digest",
    "ph": "Product Hunt — Tech Digest",
    "bookmarks": "Bookmarks — Tech Digest",
}
_DESCRIPTIONS = {
    "all": "Daily curated feed of top stories from Hacker News and Product Hunt.",
    "hn": "Top stories from Hacker News, curated daily.",
    "ph": "Top launches from Product Hunt, curated daily.",
    "bookmarks": "Your bookmarked stories.",
}


def _base_url(request: Request) -> str:
    if SITE_URL:
        return SITE_URL
    return str(request.base_url).rstrip("/")


def _seo_meta(source: str, view: str, page: int, base: str) -> dict:
    title = _TITLES.get(source, _TITLES["all"])
    description = _DESCRIPTIONS.get(source, _DESCRIPTIONS["all"])
    if page > 1:
        title = f"Page {page} — {title}"

    if view == "bookmarks":
        path = "/bookmarks" + (f"?page={page}" if page > 1 else "")
    elif source != "all":
        path = f"/?source={source}" + (f"&page={page}" if page > 1 else "")
    else:
        path = "/" + (f"?page={page}" if page > 1 else "")

    return {
        "page_title": title,
        "page_description": description,
        "canonical_url": base + path,
        "og_image": base + "/static/techdigest-small.png",
        "noindex": view == "bookmarks",
    }


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
    src = source or "all"
    seo = _seo_meta(src, "index", page, _base_url(request))
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": src,
            "view": "index",
            "page": page,
            "has_next": has_next,
            **seo,
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
    seo = _seo_meta("bookmarks", "bookmarks", page, _base_url(request))
    response = templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": products,
            "source": "bookmarks",
            "view": "bookmarks",
            "page": page,
            "has_next": has_next,
            **seo,
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


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt(request: Request):
    base = _base_url(request)
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /bookmarks\n"
        "Disallow: /bookmark/\n"
        "Disallow: /scrape\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    base = _base_url(request)
    lastmod = get_last_scraped_at()
    lastmod_tag = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    urls = [f"{base}/", f"{base}/?source=hn", f"{base}/?source=ph"]
    xml_urls = "\n".join(f"  <url><loc>{u}</loc>{lastmod_tag}</url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{xml_urls}\n"
        "</urlset>\n"
    )
    return Response(content=xml, media_type="application/xml")


@app.post("/scrape")
async def trigger_scrape(authorization: str = Header(None)):
    if not SCRAPE_SECRET:
        raise HTTPException(503, "SCRAPE_SECRET not configured")
    if authorization != f"Bearer {SCRAPE_SECRET}":
        raise HTTPException(401, "Invalid secret")

    return await run_scrape()
