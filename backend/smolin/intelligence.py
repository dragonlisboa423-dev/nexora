"""Local corpus LSA and evidence-backed co-occurrence, without external API or invented vectors.

LSA learns statistical associations in this collection, not general multilingual understanding.
The bounded corpus and exact term vocabulary/version are persisted privately. Existing remote
384-dimensional encoders remain independent and retain their consent/revision requirements.
"""

import hashlib
import re
import threading
import unicodedata
from collections import Counter, defaultdict

import numpy as np
from sqlalchemy import select

from .. import storage as store

LOCK = threading.Lock()
STOP = {
    "a",
    "o",
    "as",
    "os",
    "um",
    "uma",
    "uns",
    "umas",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "em",
    "no",
    "na",
    "nos",
    "nas",
    "e",
    "ou",
    "que",
    "se",
    "por",
    "para",
    "com",
    "sem",
    "ao",
    "aos",
    "é",
    "são",
    "foi",
    "ser",
    "como",
    "mais",
    "menos",
    "sua",
    "seu",
    "suas",
    "seus",
    "entre",
    "sobre",
    "este",
    "esta",
    "esse",
    "essa",
    "isso",
    "isto",
    "não",
    "sim",
    "também",
    "the",
    "and",
    "of",
    "in",
    "to",
    "is",
    "for",
    "on",
    "this",
    "that",
    "an",
    "be",
    "it",
    "are",
    "with",
}
STOP = {
    "".join(c for c in unicodedata.normalize("NFKD", word) if not unicodedata.combining(c))
    for word in STOP
}
VERSION = "saly-lsa-tfidf-r24-v1"
MAX_CHUNKS = 1000
MAX_TERMS = 6000


def terms(text):
    value = "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )
    return [w for w in re.findall(r"\b[a-z][a-z0-9]{2,35}\b", value) if w not in STOP]


def invalidate():
    with LOCK:
        (store.DATA / "smolin-lsa.npz").unlink(missing_ok=True)


def rows(document_id=None):
    query = select(
        store.chunks.c.id,
        store.chunks.c.document_id,
        store.chunks.c.page,
        store.chunks.c.position,
        store.chunks.c.content,
    ).order_by(store.chunks.c.document_id, store.chunks.c.page, store.chunks.c.position)
    if document_id:
        query = query.where(store.chunks.c.document_id == document_id)
    with store.db() as connection:
        # One extra entry signals partial coverage rather than pretending unlimited capacity.
        return [dict(r) for r in connection.execute(query.limit(MAX_CHUNKS + 1)).mappings()]


def fingerprint(records):
    return hashlib.sha256((VERSION + "|".join(r["id"] for r in records)).encode()).hexdigest()


def model(records):
    signature = fingerprint(records)
    target = store.DATA / "smolin-lsa.npz"
    with LOCK:
        if target.is_file():
            try:
                with np.load(target, allow_pickle=False) as cached:
                    if str(cached["signature"]) == signature:
                        return {k: cached[k] for k in cached.files}
            except (ValueError, OSError, KeyError):
                pass
        counts = [Counter(terms(r["content"])) for r in records]
        frequencies = Counter(word for count in counts for word in count)
        vocabulary = sorted(frequencies, key=lambda word: (-frequencies[word], word))[:MAX_TERMS]
        if len(records) < 3 or len(vocabulary) < 3:
            return None
        positions = {word: i for i, word in enumerate(vocabulary)}
        idf = np.array(
            [np.log((1 + len(records)) / (1 + frequencies[word])) + 1 for word in vocabulary],
            dtype=np.float32,
        )
        matrix = np.zeros((len(records), len(vocabulary)), dtype=np.float32)
        for i, count in enumerate(counts):
            for word, amount in count.items():
                if word in positions:
                    matrix[i, positions[word]] = 1 + np.log(amount)
        matrix *= idf
        matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-8)
        rank = min(24, len(records) - 1, len(vocabulary) - 1)
        # Deterministic randomized range finder, followed by a genuine truncated SVD.
        probe = (
            np.random.default_rng(42)
            .normal(size=(len(vocabulary), min(rank + 8, len(records), len(vocabulary))))
            .astype(np.float32)
        )
        q, _ = np.linalg.qr(matrix @ probe)
        for _ in range(2):
            q, _ = np.linalg.qr(matrix @ (matrix.T @ q))
        _, _, vt = np.linalg.svd(q.T @ matrix, full_matrices=False)
        components = vt[:rank].astype(np.float32)
        vectors = matrix @ components.T
        vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-8)
        result = {
            "signature": np.array(signature),
            "vocabulary": np.array(vocabulary),
            "idf": idf,
            "components": components,
            "vectors": vectors,
            "ids": np.array([r["id"] for r in records]),
        }
        store.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = target.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, **result)
        temporary.chmod(0o600)
        temporary.replace(target)
        return result


def semantic(query, document_id=None):
    records = rows(document_id)
    truncated = len(records) > MAX_CHUNKS
    records = records[:MAX_CHUNKS]
    encoded = model(records)
    if not encoded:
        return [], {
            "state": "insufficient_corpus",
            "indexed_chunks": len(records),
            "limited": truncated,
        }
    count = Counter(terms(query))
    vector = np.array(
        [(1 + np.log(count[w])) if count[w] else 0 for w in encoded["vocabulary"]], dtype=np.float32
    )
    vector *= encoded["idf"]
    projected = vector @ encoded["components"].T
    norm = np.linalg.norm(projected)
    if norm < 1e-8:
        return [], {
            "state": "no_vocabulary_match",
            "indexed_chunks": len(records),
            "limited": truncated,
        }
    scores = encoded["vectors"] @ (projected / norm)
    found = [
        {**records[int(i)], "semantic_score": round(float(scores[i]), 4), "retrieval": "local_lsa"}
        for i in np.argsort(-scores)[:8]
        if scores[i] >= 0.22
    ]
    return found, {
        "state": "ready",
        "method": VERSION,
        "indexed_chunks": len(records),
        "limited": truncated,
        "detail": "Associações estatísticas do acervo; não é um encoder neural nem garantia de relevância.",
    }


def graph(query=""):
    from .service import source_metadata, source_url

    records = rows()
    truncated = len(records) > MAX_CHUNKS
    records = records[:MAX_CHUNKS]
    documents = {}
    counts = [Counter(terms(r["content"])) for r in records]
    frequencies = Counter(word for count in counts for word in count)
    nodes = defaultdict(lambda: {"occurrences": 0, "sources": []})
    edges = {}
    requested = set(terms(query))
    for row, count in zip(records, counts, strict=True):
        if requested and not requested.intersection(count):
            continue
        doc_id = row["document_id"]
        if doc_id not in documents:
            full = store.get("documents", doc_id)
            documents[doc_id] = (
                {
                    **{k: v for k, v in full.items() if k not in {"content", "pages"}},
                    "pages": [
                        {k: v for k, v in page.items() if k != "content"}
                        for page in full.get("pages", [])
                    ],
                }
                if full
                else None
            )
        doc = documents[doc_id]
        if not doc or doc.get("status") not in {"ready", "partial", "legacy_text_only"}:
            continue
        ranked = sorted(
            count,
            key=lambda w: (
                -(1 + np.log(count[w])) * (np.log((1 + len(records)) / (1 + frequencies[w])) + 1),
                w,
            ),
        )[:4]
        evidence = {
            "chunk_id": row["id"],
            "document_id": doc_id,
            "name": doc.get("title") or doc["name"],
            "author": doc.get("author") or "Não informado",
            "page": row["page"],
            "excerpt": row["content"][:700],
            "url": source_url(doc, row["page"]),
            **source_metadata(doc, row["page"]),
        }
        for word in ranked:
            nodes[word]["occurrences"] += count[word]
            if len(nodes[word]["sources"]) < 5:
                nodes[word]["sources"].append(evidence)
        for i, word in enumerate(ranked):
            for other in ranked[i + 1 :]:
                pair = tuple(sorted((word, other)))
                edge = edges.setdefault(
                    pair,
                    {
                        "source": pair[0],
                        "target": pair[1],
                        "kind": "documented_cooccurrence",
                        "count": 0,
                        "sources": [],
                        "review": "Coocorrência no mesmo trecho; não comprova causalidade ou concordância.",
                    },
                )
                edge["count"] += 1
                if len(edge["sources"]) < 4:
                    edge["sources"].append(evidence)
    chosen = sorted(nodes, key=lambda w: (-nodes[w]["occurrences"], w))[:60]
    selected = set(chosen)
    links = sorted(
        (v for (a, b), v in edges.items() if a in selected and b in selected),
        key=lambda e: -e["count"],
    )[:150]
    contrasts = []
    for edge in links:
        authors = {s["author"] for s in edge["sources"] if s["author"] != "Não informado"}
        markers = [
            s
            for s in edge["sources"]
            if re.search(
                r"\b(porém|contudo|discorda|ao contrário|contradiz)\b", s["excerpt"], re.IGNORECASE
            )
        ]
        if len(authors) > 1 and markers:
            contrasts.append(
                {
                    "concepts": [edge["source"], edge["target"]],
                    "sources": edge["sources"],
                    "kind": "contrast_candidate",
                    "review": "Autores diferentes e marcador de contraste: exige leitura humana; divergência não confirmada.",
                }
            )
    return {
        "nodes": [dict(id=w, label=w, **nodes[w]) for w in chosen],
        "edges": links,
        "contrast_candidates": contrasts[:20],
        "covered_chunks": len(records),
        "limited": truncated,
        "method": "Termos normalizados e coocorrência documental; sem relações geradas por IA ou retreinamento.",
    }
