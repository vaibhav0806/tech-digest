import httpx

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from .db import get_latest_products_for_digest


def format_digest() -> str:
    hn_items = get_latest_products_for_digest("hn", 10)
    ph_items = get_latest_products_for_digest("ph", 10)

    lines = ["<b>Daily Tech Digest</b>\n"]

    if hn_items:
        lines.append("<b>Hacker News</b>")
        for i, item in enumerate(hn_items, 1):
            score = item.get("score") or 0
            title = item["title"]
            url = item.get("source_url") or item.get("url") or ""
            lines.append(f'{i}. <a href="{url}">{title}</a> ({score} pts)')
        lines.append("")

    if ph_items:
        lines.append("<b>Product Hunt</b>")
        for i, item in enumerate(ph_items, 1):
            title = item["title"]
            url = item.get("url") or ""
            tagline = item.get("tagline") or ""
            lines.append(f'{i}. <a href="{url}">{title}</a>')
            if tagline:
                lines.append(f"   {tagline[:100]}")
        lines.append("")

    return "\n".join(lines)


async def send_telegram_digest():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID), skipping.")
        return

    text = format_digest()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )
        if resp.status_code == 200:
            print("Telegram digest sent.")
        else:
            print(f"Telegram send failed: {resp.status_code} {resp.text}")
