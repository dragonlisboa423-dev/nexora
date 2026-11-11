"""Opt-in integration against a disposable PostgreSQL+pgvector database, never production."""

import os

import pytest
from sqlalchemy import insert, select, text

from backend import storage as store
from backend.smolin import service as smolin


@pytest.mark.skipif(
    not os.environ.get("SALY_TEST_DATABASE_URL"), reason="PostgreSQL descartável não configurado"
)
def test_postgres_real_vectors_text_and_rls(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DATA", tmp_path)
    store.initialize(os.environ["SALY_TEST_DATABASE_URL"])
    doc = store.save(
        "documents",
        {
            "name": "vetores.pdf",
            "status": "ready",
            "content": "genetica molecular",
            "file_size": 10,
            "chunks": 1,
            "sha256": "test",
            "page_count": 1,
        },
    )
    key = doc["id"]
    vector = [1.0] + [0.0] * 383
    with store.db() as c:
        c.execute(insert(store.originals).values(id=key, content=b"%PDF test fixture"))
        c.execute(
            insert(store.chunks).values(
                id=key,
                document_id=key,
                page=42,
                position=2,
                content="Genética molecular e biologia celular",
                embedding=vector,
                embedding_version="fixture-v1",
            )
        )
        found = c.execute(
            select(store.chunks.c.id)
            .order_by(store.chunks.c.embedding.cosine_distance(vector))
            .limit(1)
        ).scalar()
        assert found == key
        assert (
            c.execute(text("SELECT relrowsecurity FROM pg_class WHERE relname='memories'")).scalar()
            is True
        )
    assert smolin.lexical("genética")[0]["page"] == 42
    # A SQL guest with SELECT permission still sees no rows through RLS.
    with store.db() as c:
        c.execute(
            text(
                "DO $$ BEGIN IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='saly_test_guest') THEN CREATE ROLE saly_test_guest NOLOGIN; END IF; END $$"
            )
        )
        c.execute(text("GRANT USAGE ON SCHEMA public TO saly_test_guest"))
        c.execute(text("GRANT SELECT ON documents TO saly_test_guest"))
        c.execute(text("SET LOCAL ROLE saly_test_guest"))
        assert c.execute(text("SELECT count(*) FROM documents")).scalar() == 0
    smolin.delete_document(key)
    with store.db() as c:
        assert (
            c.execute(select(store.chunks).where(store.chunks.c.document_id == key)).first() is None
        )
