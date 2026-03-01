from .db import get_conn, log_scrape_start, log_scrape_end, upsert_product
from .scraper import scrape_hn, scrape_ph
from .telegram import send_telegram_digest


async def run_scrape() -> dict[str, int]:
    """Run all scrapers, persist results, send digest. Returns counts."""

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
