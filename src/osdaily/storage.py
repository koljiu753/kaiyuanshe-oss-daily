from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import NewsItem


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  url_hash TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  raw_title TEXT,
  raw_summary TEXT,
  source_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  published_at TEXT,
  author TEXT,
  category TEXT,
  tags_json TEXT,
  related_urls_json TEXT,
  curation_status TEXT NOT NULL DEFAULT 'candidate',
  editor_note TEXT NOT NULL DEFAULT '',
  updated_at TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_published_at ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_source_id ON items(source_id);

CREATE TABLE IF NOT EXISTS translations (
  cache_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(items)").fetchall()}
        migrations = [
            ("raw_title", "ALTER TABLE items ADD COLUMN raw_title TEXT"),
            ("raw_summary", "ALTER TABLE items ADD COLUMN raw_summary TEXT"),
            ("curation_status", "ALTER TABLE items ADD COLUMN curation_status TEXT NOT NULL DEFAULT 'candidate'"),
            ("editor_note", "ALTER TABLE items ADD COLUMN editor_note TEXT NOT NULL DEFAULT ''"),
            ("updated_at", "ALTER TABLE items ADD COLUMN updated_at TEXT"),
        ]
        for column, sql in migrations:
            if column not in columns:
                self.conn.execute(sql)
        self.conn.commit()

    @staticmethod
    def url_hash(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def seen_url(self, url: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM items WHERE url_hash = ? LIMIT 1",
            (self.url_hash(url),),
        )
        return cur.fetchone() is not None

    def backfill_raw_fields(self, item: NewsItem) -> bool:
        raw_title = item.raw_title or item.title
        raw_summary = item.raw_summary or item.summary
        cur = self.conn.execute(
            """
            UPDATE items
            SET raw_title = COALESCE(NULLIF(raw_title, ''), ?),
                raw_summary = COALESCE(NULLIF(raw_summary, ''), ?),
                updated_at = ?
            WHERE url_hash = ?
            """,
            (
                raw_title,
                raw_summary,
                datetime.now(timezone.utc).isoformat(),
                self.url_hash(item.normalized_url()),
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def insert_item(self, item: NewsItem) -> bool:
        try:
            self.conn.execute(
                """
                INSERT INTO items (
                  url_hash, url, title, summary, raw_title, raw_summary,
                  source_id, source_name, published_at, author, category,
                  tags_json, related_urls_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.url_hash(item.normalized_url()),
                    item.normalized_url(),
                    item.title,
                    item.summary,
                    item.raw_title or item.title,
                    item.raw_summary or item.summary,
                    item.source_id,
                    item.source_name,
                    item.published_at.isoformat() if item.published_at else None,
                    item.author,
                    item.category,
                    json.dumps(item.tags, ensure_ascii=False),
                    json.dumps(item.related_urls, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_translation(self, cache_key: str) -> tuple[str, str] | None:
        cur = self.conn.execute(
            "SELECT title, summary FROM translations WHERE cache_key = ?",
            (cache_key,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else None

    def save_translation(self, cache_key: str, title: str, summary: str) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO translations (cache_key, title, summary, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (cache_key, title, summary, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def list_items(self, limit: int = 300) -> list[NewsItem]:
        cur = self.conn.execute(
            """
            SELECT url, title, summary, raw_title, raw_summary, source_id, source_name,
                   published_at, author, category, tags_json, related_urls_json
            FROM items
            ORDER BY COALESCE(published_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_item(row) for row in cur.fetchall()]

    def list_item_records(self, limit: int = 300) -> list[dict]:
        cur = self.conn.execute(
            """
            SELECT id, url, title, summary, raw_title, raw_summary, source_id, source_name,
                   published_at, author, category, tags_json, related_urls_json,
                   curation_status, editor_note, updated_at, created_at
            FROM items
            ORDER BY COALESCE(published_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_record(row) for row in cur.fetchall()]

    def items_by_ids(self, ids: list[int]) -> list[NewsItem]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        cur = self.conn.execute(
            f"""
            SELECT id, url, title, summary, raw_title, raw_summary, source_id, source_name,
                   published_at, author, category, tags_json, related_urls_json,
                   curation_status, editor_note, updated_at, created_at
            FROM items
            WHERE id IN ({placeholders})
            ORDER BY category, COALESCE(published_at, created_at) DESC
            """,
            tuple(ids),
        )
        by_id = {record["id"]: record for record in (self._row_to_record(row) for row in cur.fetchall())}
        return [self._record_to_item(by_id[item_id]) for item_id in ids if item_id in by_id]

    def update_item(
        self,
        item_id: int,
        title: str,
        summary: str,
        category: str,
        tags: list[str],
        curation_status: str = "candidate",
        editor_note: str = "",
    ) -> bool:
        if curation_status not in {"accepted", "candidate", "rejected"}:
            curation_status = "candidate"
        cur = self.conn.execute(
            """
            UPDATE items
            SET title = ?, summary = ?, category = ?, tags_json = ?,
                curation_status = ?, editor_note = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                summary,
                category,
                json.dumps(tags, ensure_ascii=False),
                curation_status,
                editor_note,
                datetime.now(timezone.utc).isoformat(),
                item_id,
            ),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def update_curation_status(self, item_id: int, curation_status: str) -> bool:
        if curation_status not in {"accepted", "candidate", "rejected"}:
            return False
        cur = self.conn.execute(
            """
            UPDATE items
            SET curation_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (curation_status, datetime.now(timezone.utc).isoformat(), item_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _loads_list(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return loaded if isinstance(loaded, list) else []

    def _row_to_item(self, row: tuple) -> NewsItem:
        return NewsItem(
            url=row[0],
            title=row[1],
            summary=row[2] or "",
            raw_title=row[3] or row[1],
            raw_summary=row[4] or row[2] or "",
            source_id=row[5],
            source_name=row[6],
            published_at=datetime.fromisoformat(row[7]) if row[7] else None,
            author=row[8] or "",
            category=row[9] or "综合",
            tags=self._loads_list(row[10]),
            related_urls=self._loads_list(row[11]),
        )

    def _row_to_record(self, row: tuple) -> dict:
        return {
            "id": row[0],
            "url": row[1],
            "title": row[2],
            "summary": row[3] or "",
            "raw_title": row[4] or row[2],
            "raw_summary": row[5] or row[3] or "",
            "source_id": row[6],
            "source_name": row[7],
            "published_at": row[8],
            "author": row[9] or "",
            "category": row[10] or "综合",
            "tags": self._loads_list(row[11]),
            "related_urls": self._loads_list(row[12]),
            "curation_status": row[13] or "candidate",
            "editor_note": row[14] or "",
            "updated_at": row[15],
            "created_at": row[16],
        }

    def _record_to_item(self, record: dict) -> NewsItem:
        return NewsItem(
            url=record["url"],
            title=record["title"],
            summary=record["summary"],
            raw_title=record["raw_title"],
            raw_summary=record["raw_summary"],
            source_id=record["source_id"],
            source_name=record["source_name"],
            published_at=datetime.fromisoformat(record["published_at"]) if record["published_at"] else None,
            author=record["author"],
            category=record["category"],
            tags=record["tags"],
            related_urls=record["related_urls"],
        )
