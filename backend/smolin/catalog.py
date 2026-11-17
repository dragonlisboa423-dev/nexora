"""Metadata projections: listing a large collection must not materialize book texts."""

from sqlalchemy import select

from .. import storage as store

FIELDS = (
    "name",
    "mime",
    "kind",
    "unit",
    "sha256",
    "file_size",
    "status",
    "page_count",
    "chunks",
    "embedding_status",
    "pipeline",
    "interpretation_notice",
    "media_info",
    "transcribed",
    "title",
    "author",
    "empty_pages",
    "revision",
    "text_size",
)


def documents():
    table = store.tables["documents"]
    with store.db() as connection:
        rows = (
            connection.execute(
                select(
                    table.c.id,
                    table.c.created,
                    table.c.updated,
                    *(table.c.data[field].label(field) for field in FIELDS),
                ).order_by(table.c.created.desc())
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]
