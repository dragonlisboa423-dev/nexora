"""Private administration. No public registration endpoint exists."""

import argparse
import getpass
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from sqlalchemy import insert, select, text

from . import storage as store
from .security import password_hash, set_owner


def migrate_legacy(source, owner_id=None):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError("Banco legado não encontrado")
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as old:
        old.row_factory = sqlite3.Row
        accounts = old.execute("SELECT * FROM users").fetchall()
        if len(accounts) > 1 and not owner_id:
            raise ValueError(
                "Há múltiplos espaços legados. Informe --owner-id; o banco original não será alterado."
            )
        account = (
            next((r for r in accounts if r["id"] == owner_id), None)
            if owner_id
            else accounts[0]
            if accounts
            else None
        )
        snapshot = source.with_name(source.name + ".before-global.bak")
        if not snapshot.exists():
            fd = os.open(snapshot, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with sqlite3.connect(snapshot) as backup:
                old.backup(backup)
        if owner_id and not account:
            raise ValueError("Proprietária não encontrada")
        store.initialize(check_legacy=False)
        if store.setting("legacy_migrated"):
            raise ValueError("Migração já realizada; nenhuma duplicação aplicada")
        if account:
            if owner_id and account["id"] != owner_id:
                raise ValueError("Proprietária não encontrada")
            with store.db() as c:
                if c.execute(select(store.owner_access)).first():
                    raise ValueError("Acesso já configurado no destino; use um diretório novo")
                c.execute(
                    insert(store.owner_access).values(id=1, password_hash=account["password"])
                )
            counts = {}
            for table in (
                "memories",
                "versions",
                "conversations",
                "documents",
                "activities",
                "evaluations",
                "lists",
            ):
                rows = old.execute(
                    f"SELECT * FROM {table} WHERE user_id=?", (account["id"],)
                ).fetchall()
                for row in rows:
                    data = dict(row)
                    key = str(data.pop("id"))
                    data.pop("user_id", None)
                    for field in ("tags", "relations", "snapshot", "results"):
                        if field in data and isinstance(data[field], str):
                            data[field] = json.loads(data[field])
                    if isinstance(data.get("snapshot"), dict):
                        data["snapshot"].pop("user_id", None)
                    if table == "documents":
                        data.update(
                            status="legacy_text_only",
                            original_missing=True,
                            pages=[],
                            page_count=None,
                            chunks=0,
                            mime="text/plain",
                            file_size=0,
                            sha256=hashlib.sha256(data["content"].encode()).hexdigest(),
                            embedding_status="unavailable",
                        )
                    store.save(table, data, key)
                    from sqlalchemy import update

                    with store.db() as connection:
                        values = {
                            field: data[field]
                            for field in ("created", "updated")
                            if data.get(field)
                        }
                        if values:
                            connection.execute(
                                update(store.tables[table])
                                .where(store.tables[table].c.id == key)
                                .values(**values)
                            )
                counts[table] = len(rows)
            conversations = [r["id"] for r in store.all_records("conversations")]
            for row in old.execute("SELECT * FROM messages"):
                if row["conversation_id"] in conversations:
                    store.save("messages", {**dict(row), "epoch": 0}, row["id"])
            for row in old.execute("SELECT * FROM chunks WHERE user_id=?", (account["id"],)):
                with store.db() as c:
                    c.execute(
                        insert(store.chunks).values(
                            id=store.uid(),
                            document_id=row["document_id"],
                            page=0,
                            position=row["position"],
                            content=row["content"],
                        )
                    )
            prefs = old.execute(
                "SELECT value FROM settings WHERE user_id=?", (account["id"],)
            ).fetchone()
            if prefs:
                data = json.loads(prefs["value"])
                data.setdefault("privacy", {})["remoteConsent"] = False
                store.set_setting("preferences", data)
        else:
            counts = {}
        store.set_setting("legacy_migrated", True)
        return counts


def main():
    parser = argparse.ArgumentParser(description="SALY · administração privada da proprietária")
    parser.add_argument(
        "operation",
        choices=["init", "owner", "hash-owner", "check", "backup", "restore", "migrate-legacy"],
    )
    parser.add_argument("path", nargs="?")
    parser.add_argument("--owner-id")
    parser.add_argument("--confirm-stopped", action="store_true")
    args = parser.parse_args()
    if args.operation == "hash-owner":
        password = getpass.getpass("Senha privada (mínimo 12 caracteres): ")
        if len(password) < 12 or password != getpass.getpass("Repita a senha: "):
            parser.error("Use senha forte e confirme o mesmo valor")
        print(password_hash(password))
        return
    if args.operation == "migrate-legacy":
        if not args.path:
            parser.error("Informe o banco legado")
        print("Migração concluída:", migrate_legacy(args.path, args.owner_id))
        return
    if args.operation == "restore":
        if not args.path or not args.confirm_stopped:
            parser.error("Pare o servidor e informe o backup com --confirm-stopped")
        target = store.DATA / "saly-v2.sqlite3"
        store.DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.exists():
            parser.error("Use SALY_DATA_DIR novo para preservar dados existentes")
        with sqlite3.connect(f"file:{Path(args.path).resolve()}?mode=ro", uri=True) as source:
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                parser.error("Backup inválido")
            source.execute("SELECT password_hash FROM owner_access LIMIT 1")
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with sqlite3.connect(target) as out:
                source.backup(out)
                out.execute("DELETE FROM owner_sessions")
        print("Backup restaurado. Sessões invalidadas.")
        return
    store.initialize()
    if args.operation == "init":
        print(
            "Esquema global v2 inicializado; acesso privado pode ser configurado com: python -m backend.manage owner"
        )
    elif args.operation == "owner":
        password = getpass.getpass("Senha privada da proprietária (mínimo 12 caracteres): ")
        if password != getpass.getpass("Repita a senha: "):
            parser.error("Senhas não conferem")
        set_owner(password)
        print("Acesso da proprietária configurado. Nenhum cadastro público foi criado.")
    elif args.operation == "check":
        with store.db() as c:
            print(
                c.execute(
                    text(
                        "PRAGMA integrity_check"
                        if store.engine.dialect.name == "sqlite"
                        else "SELECT 1"
                    )
                ).scalar()
            )
    elif args.operation == "backup":
        if not args.path:
            parser.error("Informe destino privado")
        if store.engine.dialect.name != "sqlite":
            parser.error("Use pg_dump e exporte o Storage privado, conforme README")
        target = Path(args.path).resolve()
        if target.exists():
            parser.error("Destino existe; não será sobrescrito")
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(store.engine.url.database) as source, sqlite3.connect(target) as out:
            source.backup(out)
            if out.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup inválido")
        print("Backup integral privado criado, incluindo originais e vetores locais.")


if __name__ == "__main__":
    main()
