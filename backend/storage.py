import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA = Path(os.environ.get("SALY_DATA_DIR", "data")).resolve()


@contextmanager
def db():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    con = sqlite3.connect(DATA / "saly.sqlite3", timeout=15)
    os.chmod(DATA / "saly.sqlite3", 0o600)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init():
    with db() as c:
        c.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_version VALUES(1);
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), expires REAL);
        CREATE TABLE IF NOT EXISTS settings(user_id TEXT PRIMARY KEY REFERENCES users(id), value TEXT NOT NULL DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), content TEXT NOT NULL,
          category TEXT NOT NULL, tags TEXT NOT NULL, source TEXT NOT NULL, verification TEXT NOT NULL,
          archived INTEGER NOT NULL, enabled INTEGER NOT NULL, relations TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(id UNINDEXED, content, tags, tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER IF NOT EXISTS memory_insert AFTER INSERT ON memories BEGIN
          INSERT INTO memory_fts(id,content,tags) VALUES(new.id,new.content,new.tags); END;
        CREATE TRIGGER IF NOT EXISTS memory_delete AFTER DELETE ON memories BEGIN DELETE FROM memory_fts WHERE id=old.id; END;
        CREATE TRIGGER IF NOT EXISTS memory_update AFTER UPDATE ON memories BEGIN
          DELETE FROM memory_fts WHERE id=old.id; INSERT INTO memory_fts(id,content,tags) VALUES(new.id,new.content,new.tags); END;
        CREATE TABLE IF NOT EXISTS versions(id INTEGER PRIMARY KEY, memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
          user_id TEXT REFERENCES users(id), snapshot TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), title TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
          role TEXT NOT NULL, content TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id), name TEXT NOT NULL,
          content TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
          user_id TEXT REFERENCES users(id), content TEXT NOT NULL, position INTEGER);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(content, tokenize='unicode61 remove_diacritics 2');
        CREATE TRIGGER IF NOT EXISTS chunk_insert AFTER INSERT ON chunks BEGIN
          INSERT INTO chunk_fts(rowid,content) VALUES(new.id,new.content); END;
        CREATE TRIGGER IF NOT EXISTS chunk_delete AFTER DELETE ON chunks BEGIN DELETE FROM chunk_fts WHERE rowid=old.id; END;
        CREATE TABLE IF NOT EXISTS activities(id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id), kind TEXT, detail TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY, user_id TEXT REFERENCES users(id), results TEXT, model TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS lists(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),content TEXT,done INTEGER DEFAULT 0);
        """)


def row(r):
    if r is None:
        return None
    d = dict(r)
    for key in ("tags", "relations"):
        if key in d:
            d[key] = json.loads(d[key])
    for key in ("archived", "enabled", "done"):
        if key in d:
            d[key] = bool(d[key])
    return d
