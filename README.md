# Tech Digest

**[techdigest.live](https://techdigest.live)**

Aggregates top posts from Hacker News and Product Hunt into a single feed with a clean dark UI. Optionally sends a daily digest to a Telegram channel.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)

## Features

- **HN + Product Hunt scraping** — top stories from HN (top & show) and latest Product Hunt launches
- **Web UI** — filterable feed with dark theme, per-user bookmarks via session cookies
- **Telegram digest** — daily top-10 from each source broadcast to a channel
- **Zero auth** — bookmarks use anonymous cookie sessions, no signup required

## Setup

```bash
# Install dependencies
uv sync

# Populate the database
python scrape_job.py

# Start the server
uvicorn tech_digest.app:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SCRAPE_SECRET` | Bearer token for the `POST /scrape` endpoint | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | No |
| `TELEGRAM_CHANNEL_ID` | Telegram channel (`@handle` or numeric ID) | No |
| `DATABASE_PATH` | SQLite DB path (default: `./data/products.db`) | No |
| `PORT` | Server port (default: `8000`) | No |

## API

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Feed page, optional `?source=hn\|ph` filter |
| `/bookmarks` | GET | User's bookmarked items |
| `/bookmark/{id}` | POST | Toggle bookmark |
| `/scrape` | POST | Trigger scrape + Telegram digest (requires `Authorization: Bearer <SCRAPE_SECRET>`) |

## Project Structure

```
hackernews-scraper/
├── tech_digest/
│   ├── __init__.py       # package marker
│   ├── app.py            # FastAPI app + routes
│   ├── config.py         # all env vars
│   ├── db.py             # SQLite database layer
│   ├── scraper.py        # HN + Product Hunt scrapers
│   ├── services.py       # shared scrape orchestration
│   └── telegram.py       # Telegram digest sender
├── templates/
│   └── index.html
├── scrape_job.py         # CLI entry point
├── pyproject.toml
├── Procfile
└── README.md
```

## Deployment

Includes a `Procfile` for Heroku / Railway / Render:

```
web: uvicorn tech_digest.app:app --host 0.0.0.0 --port ${PORT:-8000}
```

Set up a cron job or scheduler to hit `POST /scrape` periodically.

## Tech Stack

FastAPI, SQLite (WAL mode), httpx, BeautifulSoup, Jinja2
