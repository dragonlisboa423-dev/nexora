import sqlite3

import pytest
from sqlalchemy import select

from backend import storage as store
from backend.manage import migrate_legacy
from backend.security import password_hash


def test_legacy_migration_preserves_source_password_content_dates(tmp_path, monkeypatch):
    source = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(source) as c:
        c.executescript("""
        CREATE TABLE users(id TEXT,username TEXT,password TEXT);
        CREATE TABLE memories(id TEXT,user_id TEXT,content TEXT,category TEXT,tags TEXT,relations TEXT,created TEXT,updated TEXT);
        CREATE TABLE versions(id INTEGER,user_id TEXT,memory_id TEXT,snapshot TEXT,created TEXT);
        CREATE TABLE conversations(id TEXT,user_id TEXT,title TEXT,created TEXT);
        CREATE TABLE documents(id TEXT,user_id TEXT,name TEXT,content TEXT,created TEXT);
        CREATE TABLE activities(id INTEGER,user_id TEXT,kind TEXT,detail TEXT,created TEXT);
        CREATE TABLE evaluations(id INTEGER,user_id TEXT,results TEXT,model TEXT,created TEXT);
        CREATE TABLE lists(id TEXT,user_id TEXT,content TEXT,done INTEGER);
        CREATE TABLE messages(id TEXT,conversation_id TEXT,role TEXT,content TEXT,created TEXT);
        CREATE TABLE chunks(id INTEGER,document_id TEXT,user_id TEXT,content TEXT,position INTEGER);
        CREATE TABLE settings(user_id TEXT,value TEXT);
        """)
        hashed = password_hash("legacy-owner-password")
        c.execute("INSERT INTO users VALUES(?,?,?)", ("owner", "legacy-user", hashed))
        c.execute(
            "INSERT INTO memories VALUES(?,?,?,?,?,?,?,?)",
            (
                "memory",
                "owner",
                "Minha preferencia antiga",
                "preferencias",
                "[]",
                "[]",
                "2020-01-01",
                "2021-01-01",
            ),
        )
        c.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?)",
            ("doc", "owner", "antigo.pdf", "texto preservado", "2020-01-01"),
        )
        c.execute(
            "INSERT INTO chunks VALUES(?,?,?,?,?)", (1, "doc", "owner", "texto preservado", 0)
        )
    raw = source.read_bytes()
    monkeypatch.setattr(store, "DATA", tmp_path / "new")
    monkeypatch.setenv(
        "SALY_DATABASE_URL", "sqlite:///" + str(tmp_path / "new" / "saly-v2.sqlite3")
    )
    counts = migrate_legacy(source)
    assert counts["memories"] == 1 and source.read_bytes() == raw
    assert source.with_name("legacy.sqlite3.before-global.bak").exists()
    assert store.get("memories", "memory")["created"] == "2020-01-01"
    assert store.get("documents", "doc")["original_missing"] is True
    with store.db() as c:
        assert c.execute(select(store.owner_access.c.password_hash)).scalar() == hashed
    with pytest.raises(ValueError):
        migrate_legacy(source)
