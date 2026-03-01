import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from db import init_db, get_products, get_bookmarked_products, toggle_bookmark

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.on_event("startup")
def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, source: str | None = None):
    products = get_products(source=source)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "source": source or "all",
        "page": "index",
    })


@app.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_page(request: Request):
    products = get_bookmarked_products()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "products": products,
        "source": "bookmarks",
        "page": "bookmarks",
    })


@app.post("/bookmark/{product_id}")
async def bookmark(product_id: int):
    is_bookmarked = toggle_bookmark(product_id)
    return JSONResponse({"bookmarked": is_bookmarked})
