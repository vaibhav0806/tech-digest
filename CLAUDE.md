# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Tech Digest — aggregates top posts from Hacker News and Product Hunt into a single feed. FastAPI + SQLite + Jinja2.

## Structure

- `tech_digest/` — Python package (app, config, db, scraper, services, telegram)
- `templates/` — Jinja2 HTML templates
- `scrape_job.py` — CLI entry point for running scrapers
- `data/` — SQLite database (gitignored)

## Commands

```bash
# Install dependencies
uv sync

# Run scraper
python scrape_job.py

# Start dev server
uvicorn tech_digest.app:app --reload

# Import check
python3 -c "from tech_digest.app import app"
```
