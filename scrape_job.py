import asyncio
from db import init_db, get_conn, upsert_product, log_scrape_start, log_scrape_end
from scraper import scrape_hn, scrape_ph
from telegram import send_telegram_digest


async def run():
    init_db()

    # Scrape HN top stories
    log_id = log_scrape_start("hn_top")
    try:
        print("Scraping HN top stories...")
        items = await scrape_hn("top")
        conn = get_conn()
        for item in items:
            upsert_product(conn, item)
        conn.commit()
        conn.close()
        log_scrape_end(log_id, len(items))
        print(f"  HN top: {len(items)} items")
    except Exception as e:
        log_scrape_end(log_id, 0, f"error: {e}")
        print(f"  HN top failed: {e}")

    # Scrape HN Show stories
    log_id = log_scrape_start("hn_show")
    try:
        print("Scraping HN Show stories...")
        items = await scrape_hn("show")
        conn = get_conn()
        for item in items:
            upsert_product(conn, item)
        conn.commit()
        conn.close()
        log_scrape_end(log_id, len(items))
        print(f"  HN show: {len(items)} items")
    except Exception as e:
        log_scrape_end(log_id, 0, f"error: {e}")
        print(f"  HN show failed: {e}")

    # Scrape Product Hunt
    log_id = log_scrape_start("ph")
    try:
        print("Scraping Product Hunt feed...")
        items = await scrape_ph()
        conn = get_conn()
        for item in items:
            upsert_product(conn, item)
        conn.commit()
        conn.close()
        log_scrape_end(log_id, len(items))
        print(f"  PH: {len(items)} items")
    except Exception as e:
        log_scrape_end(log_id, 0, f"error: {e}")
        print(f"  PH failed: {e}")

    # Send Telegram digest
    await send_telegram_digest()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(run())
