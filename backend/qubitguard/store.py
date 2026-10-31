import json
from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
                config TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                result TEXT, error TEXT)""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE experiments SET status='failed', error='Server restarted before completion; rerun this configuration.' WHERE status IN ('queued','running')")

    def create(self, config):
        key = str(uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO experiments (id,created_at,status,config) VALUES (?,?,?,?)",
                (key, datetime.now(timezone.utc).isoformat(), "queued", json.dumps(config)))
        return key

    def update(self, key, **fields):
        allowed = {"status", "progress", "result", "error"}
        if not fields or not fields.keys() <= allowed:
            raise ValueError("Invalid experiment update")
        with self.connect() as db:
            db.execute("UPDATE experiments SET " + ",".join(f"{f}=?" for f in fields) + " WHERE id=?",
                [json.dumps(v) if f == "result" else v for f, v in fields.items()] + [key])

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT * FROM experiments WHERE id=?", (key,)).fetchone()
        if not row:
            return None
        item = dict(row)
        for field in ("config", "result"):
            if item[field] is not None:
                item[field] = json.loads(item[field])
        return item

    def list(self, limit=50, offset=0):
        with self.connect() as db:
            rows = db.execute("SELECT id,created_at,status,config,progress,error FROM experiments ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [{**dict(row), "config": json.loads(row["config"])} for row in rows]
