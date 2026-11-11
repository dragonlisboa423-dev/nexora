"""Optional semantic retrieval shares the same global memory and immutable encoder as Smolin."""

import math

from sqlalchemy import delete, insert, select

from . import storage as store
from .smolin.service import embedding_provider


async def index_memory(key):
    memory = store.get("memories", key)
    if (
        not memory
        or not embedding_provider.configured
        or not store.setting("preferences", {}).get("privacy", {}).get("remoteConsent")
    ):
        return
    try:
        vector = (await embedding_provider.encode([memory["content"]]))[0]
        if not store.get("memories", key):
            return
        with store.db() as c:
            c.execute(delete(store.memory_vectors).where(store.memory_vectors.c.id == key))
            c.execute(
                insert(store.memory_vectors).values(
                    id=key, embedding=vector, embedding_version=embedding_provider.version
                )
            )
    except Exception:  # noqa: BLE001 - a failed optional index must not discard the approved memory
        store.audit("embedding_error", "Indexação semântica de memória indisponível: " + key)


async def search_memories(query="", usable=False, category=""):
    lexical = store.search_memories(query, usable, category)
    if (
        not query
        or not embedding_provider.configured
        or not store.setting("preferences", {}).get("privacy", {}).get("remoteConsent")
    ):
        return lexical
    try:
        vector = (await embedding_provider.encode([query]))[0]
        with store.db() as c:
            statement = select(store.memory_vectors).where(
                store.memory_vectors.c.embedding_version == embedding_provider.version
            )
            if store.engine.dialect.name == "postgresql":
                statement = statement.order_by(
                    store.memory_vectors.c.embedding.cosine_distance(vector)
                ).limit(20)
            rows = c.execute(statement).mappings().all()

        def score(r):
            v = r["embedding"]
            return sum(a * b for a, b in zip(vector, v, strict=True)) / (
                math.sqrt(sum(a * a for a in vector)) * math.sqrt(sum(a * a for a in v)) or 1
            )

        rows = sorted(rows, key=score, reverse=True)
        allowed = {m["id"]: m for m in store.search_memories("", usable, category)}
        candidates = [allowed[r["id"]] for r in rows if r["id"] in allowed and score(r) > 0.45][:20]
        ranking = {}
        for group in (lexical, candidates):
            for rank, m in enumerate(group):
                ranking[m["id"]] = ranking.get(m["id"], 0) + 1 / (60 + rank)
        by_id = {m["id"]: m for m in lexical + candidates}
        return [by_id[key] for key in sorted(ranking, key=ranking.get, reverse=True)]
    except Exception:  # noqa: BLE001 - lexical retrieval remains honest and available
        store.audit(
            "embedding_error", "Busca semântica de memória indisponível; usando busca textual"
        )
        return lexical
