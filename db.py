import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "data", "products.db"))


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT,
            tagline TEXT,
            author TEXT,
            score INTEGER,
            comment_count INTEGER,
            source_url TEXT,
            published_at TEXT,
            scraped_at TEXT NOT NULL,
            UNIQUE(source, source_id)
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(session_id, product_id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS scrape_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            items_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running'
        );
    """)
    # Migrate old bookmarks table (no session_id column) to new schema
    cols = [row[1] for row in conn.execute("PRAGMA table_info(bookmarks)").fetchall()]
    if "session_id" not in cols:
        conn.executescript("""
            ALTER TABLE bookmarks RENAME TO bookmarks_old;
            CREATE TABLE bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(session_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            INSERT INTO bookmarks (session_id, product_id, created_at)
                SELECT 'legacy', product_id, created_at FROM bookmarks_old;
            DROP TABLE bookmarks_old;
        """)
    conn.close()


def upsert_product(conn: sqlite3.Connection, product: dict):
    conn.execute("""
        INSERT INTO products (source, source_id, title, url, tagline, author, score, comment_count, source_url, published_at, scraped_at)
        VALUES (:source, :source_id, :title, :url, :tagline, :author, :score, :comment_count, :source_url, :published_at, :scraped_at)
        ON CONFLICT(source, source_id) DO UPDATE SET
            title=excluded.title,
            url=excluded.url,
            tagline=excluded.tagline,
            score=excluded.score,
            comment_count=excluded.comment_count,
            scraped_at=excluded.scraped_at
    """, product)


def get_products(source: str | None = None, limit: int = 60, session_id: str = "") -> list[dict]:
    conn = get_conn()
    if source:
        rows = conn.execute(
            "SELECT p.*, (b.id IS NOT NULL) as bookmarked FROM products p LEFT JOIN bookmarks b ON p.id = b.product_id AND b.session_id = ? WHERE p.source = ? ORDER BY p.scraped_at DESC, p.score DESC LIMIT ?",
            (session_id, source, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT p.*, (b.id IS NOT NULL) as bookmarked FROM products p LEFT JOIN bookmarks b ON p.id = b.product_id AND b.session_id = ? ORDER BY p.scraped_at DESC, p.score DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_bookmarked_products(session_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT p.*, 1 as bookmarked FROM products p INNER JOIN bookmarks b ON p.id = b.product_id WHERE b.session_id = ? ORDER BY b.created_at DESC",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def toggle_bookmark(product_id: int, session_id: str) -> bool:
    conn = get_conn()
    existing = conn.execute("SELECT id FROM bookmarks WHERE session_id = ? AND product_id = ?", (session_id, product_id)).fetchone()
    if existing:
        conn.execute("DELETE FROM bookmarks WHERE session_id = ? AND product_id = ?", (session_id, product_id))
        conn.commit()
        conn.close()
        return False
    else:
        conn.execute("INSERT INTO bookmarks (session_id, product_id, created_at) VALUES (?, ?, ?)", (session_id, product_id, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
        return True


def log_scrape_start(source: str) -> int:
    conn = get_conn()
    cur = conn.execute("INSERT INTO scrape_log (source, started_at) VALUES (?, ?)", (source, datetime.now(timezone.utc).isoformat()))
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return log_id


def log_scrape_end(log_id: int, items_count: int, status: str = "ok"):
    conn = get_conn()
    conn.execute("UPDATE scrape_log SET finished_at = ?, items_count = ?, status = ? WHERE id = ?",
                 (datetime.now(timezone.utc).isoformat(), items_count, status, log_id))
    conn.commit()
    conn.close()


def get_latest_products_for_digest(source: str, limit: int = 10) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM products WHERE source = ? ORDER BY score DESC, scraped_at DESC LIMIT ?",
        (source, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
