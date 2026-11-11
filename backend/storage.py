"""Global owner-only storage. SQLite for local work; PostgreSQL/pgvector for deployment."""

import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    event,
    insert,
    select,
    text,
    update,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

DATA = Path(os.environ.get("SALY_DATA_DIR", "data")).resolve()
metadata = MetaData()
owner_access = Table(
    "owner_access",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("password_hash", Text, nullable=False),
)
sessions = Table(
    "owner_sessions",
    metadata,
    Column("token", String, primary_key=True),
    Column("expires", Float, nullable=False),
)
config = Table(
    "app_config",
    metadata,
    Column("id", String, primary_key=True),
    Column("data", JSON, nullable=False),
)
tables = {}
for name in [
    "memories",
    "versions",
    "conversations",
    "messages",
    "documents",
    "activities",
    "evaluations",
    "lists",
    "reminders",
    "tool_executions",
    "agent_approvals",
    "document_jobs",
]:
    tables[name] = Table(
        name,
        metadata,
        Column("id", String, primary_key=True),
        Column("data", JSON, nullable=False),
        Column("created", String, nullable=False),
        Column("updated", String, nullable=False),
    )
originals = Table(
    "document_originals",
    metadata,
    Column("id", String, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("content", LargeBinary, nullable=False),
)
chunks = Table(
    "document_chunks",
    metadata,
    Column("id", String, primary_key=True),
    Column(
        "document_id",
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("page", Integer, nullable=False),
    Column("position", Integer, nullable=False),
    Column("content", Text, nullable=False),
    Column("embedding", Vector(384).with_variant(JSON, "sqlite")),
    Column("embedding_version", String),
)
memory_vectors = Table(
    "memory_vectors",
    metadata,
    Column("id", String, ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
    Column("embedding", Vector(384).with_variant(JSON, "sqlite"), nullable=False),
    Column("embedding_version", String, nullable=False),
)
engine = None


def now():
    return datetime.now(UTC).isoformat()


def uid():
    return uuid.uuid4().hex


def initialize(url=None, check_legacy=True):
    global engine
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    url = url or os.environ.get("SALY_DATABASE_URL") or "sqlite:///" + str(DATA / "saly-v2.sqlite3")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if (
        check_legacy
        and url.startswith("sqlite:")
        and (DATA / "saly.sqlite3").exists()
        and not (DATA / "saly-v2.sqlite3").exists()
    ):
        raise RuntimeError(
            "Banco legado detectado. Faça backup e execute:\n.venv/bin/python -m backend.manage migrate-legacy data/saly.sqlite3\nNenhum dado foi alterado."
        )
    if engine is not None:
        engine.dispose()
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False}
        if url.startswith("sqlite:")
        else {"prepare_threshold": None},
        pool_pre_ping=True,
    )
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    with engine.begin() as c:
        if engine.dialect.name == "postgresql":
            c.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        # No public SQL/PostgREST role may read personal data. Backend table owner/service role only.
        with engine.begin() as connection:
            for table in metadata.sorted_tables:
                connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
                connection.execute(text(f'REVOKE ALL ON TABLE "{table.name}" FROM PUBLIC'))

    with engine.begin() as c:
        if engine.dialect.name == "sqlite":
            c.execute(
                text(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS smolin_fts USING fts5(id UNINDEXED, content)"
                )
            )
            for name, sql in {
                "smolin_insert": "AFTER INSERT ON document_chunks BEGIN INSERT INTO smolin_fts(id,content) VALUES(new.id,new.content); END",
                "smolin_delete": "AFTER DELETE ON document_chunks BEGIN DELETE FROM smolin_fts WHERE id=old.id; END",
            }.items():
                c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {name} {sql}"))
        else:
            c.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS smolin_text_idx ON document_chunks USING gin(to_tsvector('portuguese', content))"
                )
            )
            c.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS smolin_vector_idx ON document_chunks USING hnsw (embedding vector_cosine_ops)"
                )
            )
            c.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS memory_vector_idx ON memory_vectors USING hnsw (embedding vector_cosine_ops)"
                )
            )
        if not c.execute(select(config.c.id).where(config.c.id == "schema_version")).first():
            c.execute(insert(config).values(id="schema_version", data=2))
    if (
        engine.dialect.name == "sqlite"
        and engine.url.database
        and engine.url.database != ":memory:"
    ):
        os.chmod(engine.url.database, 0o600)
    initial_hash = os.environ.get("SALY_OWNER_PASSWORD_HASH", "")
    if initial_hash:
        if not re.fullmatch(r"[0-9a-f]{32}:[0-9a-f]{128}", initial_hash):
            raise ValueError(
                "SALY_OWNER_PASSWORD_HASH precisa ser gerado pela administração privada"
            )
        with engine.begin() as connection:
            if not connection.execute(select(owner_access.c.id)).first():
                connection.execute(insert(owner_access).values(id=1, password_hash=initial_hash))


def db():
    if engine is None:
        initialize()
    return engine.begin()


def pack(row):
    r = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    return {**r.pop("data"), **r}


def get(kind, key):
    with db() as c:
        r = c.execute(select(tables[kind]).where(tables[kind].c.id == key)).first()
    return pack(r) if r else None


def all_records(kind):
    with db() as c:
        rows = c.execute(select(tables[kind]).order_by(tables[kind].c.created.desc())).all()
    return [pack(r) for r in rows]


def save(kind, data, key=None):
    key = key or uid()
    old = get(kind, key)
    payload = {k: v for k, v in data.items() if k not in ("id", "created", "updated")}
    values = {"data": payload, "updated": now()}
    with db() as c:
        if old:
            c.execute(update(tables[kind]).where(tables[kind].c.id == key).values(**values))
        else:
            c.execute(insert(tables[kind]).values(id=key, created=now(), **values))
    return get(kind, key)


def remove(kind, key):
    with db() as c:
        c.execute(delete(tables[kind]).where(tables[kind].c.id == key))


def setting(key, default=None):
    with db() as c:
        r = c.execute(select(config.c.data).where(config.c.id == key)).first()
    return r[0] if r else default


def set_setting(key, value):
    with db() as c:
        if c.execute(select(config.c.id).where(config.c.id == key)).first():
            c.execute(update(config).where(config.c.id == key).values(data=value))
        else:
            c.execute(insert(config).values(id=key, data=value))


def audit(kind, detail):
    return save("activities", {"kind": kind, "detail": detail[:300]})


def words(value):
    return set(re.findall(r"\w+", value.casefold(), re.UNICODE))


def search_memories(query="", usable=False, category=""):
    records = all_records("memories")
    tokens = words(query)
    records = [m for m in records if not category or m.get("category") == category]
    if usable:
        records = [
            m
            for m in records
            if m.get("enabled", True)
            and not m.get("archived")
            and m.get("verification") != "contested"
            and (not m.get("expires_at") or m["expires_at"] > now())
        ]
    for r in records:
        r["relevance"] = len(
            tokens & words(r.get("content", "") + " " + " ".join(r.get("tags", [])))
        )
    if tokens:
        records = [r for r in records if r["relevance"]]
    return sorted(
        records,
        key=lambda r: (r["relevance"], r.get("importance", 0.5), r["updated"]),
        reverse=True,
    )[:1000]
