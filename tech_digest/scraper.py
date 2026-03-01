import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timezone

HN_API = "https://hacker-news.firebaseio.com/v0"
PH_FEED = "https://www.producthunt.com/feed"


async def scrape_hn(story_type: str = "top") -> list[dict]:
    endpoint = "topstories" if story_type == "top" else "showstories"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{HN_API}/{endpoint}.json")
        resp.raise_for_status()
        story_ids = resp.json()[:30]

        products = []
        for story_id in story_ids:
            try:
                item_resp = await client.get(f"{HN_API}/item/{story_id}.json")
                item_resp.raise_for_status()
                item = item_resp.json()
                if not item or item.get("type") != "story":
                    continue
                products.append({
                    "source": "hn",
                    "source_id": str(story_id),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "tagline": None,
                    "author": item.get("by", ""),
                    "score": item.get("score", 0),
                    "comment_count": item.get("descendants", 0),
                    "source_url": f"https://news.ycombinator.com/item?id={story_id}",
                    "published_at": datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc).isoformat(),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                print(f"  skip HN item {story_id}: {e}")
        return products


async def scrape_ph() -> list[dict]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(PH_FEED)
        resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries = root.findall("atom:entry", ns)

    products = []
    for entry in entries:
        title = entry.findtext("atom:title", "", ns)
        link_el = entry.find("atom:link", ns)
        url = link_el.get("href", "") if link_el is not None else ""
        entry_id = entry.findtext("atom:id", "", ns)
        author_el = entry.find("atom:author", ns)
        author = author_el.findtext("atom:name", "", ns) if author_el is not None else ""
        published = entry.findtext("atom:published", "", ns)

        content_html = entry.findtext("atom:content", "", ns)
        tagline = ""
        if content_html:
            soup = BeautifulSoup(content_html, "html.parser")
            first_p = soup.find("p")
            tagline = (first_p.get_text(strip=True) if first_p else soup.contents[0].strip() if soup.contents else "")[:200]

        source_id = entry_id or url
        products.append({
            "source": "ph",
            "source_id": source_id,
            "title": title,
            "url": url,
            "tagline": tagline,
            "author": author,
            "score": None,
            "comment_count": None,
            "source_url": url,
            "published_at": published,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        })
    return products
