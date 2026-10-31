"""Operações administrativas locais. Restauração exige aplicação parada."""

import argparse
import os
import sqlite3
from pathlib import Path

from .storage import DATA, db, init


def main():
    parser = argparse.ArgumentParser(description="Administração local SALY")
    parser.add_argument("operation", choices=["init", "check", "backup", "restore"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--confirm-stopped", action="store_true")
    args = parser.parse_args()
    if args.operation == "init":
        init()
        print("SQLite inicializado; migração v1 aplicada de forma idempotente.")
    elif args.operation == "check":
        with db() as c:
            result = c.execute("PRAGMA integrity_check").fetchone()[0]
            print(result)
            if result != "ok":
                raise SystemExit(1)
    elif args.operation == "backup":
        if not args.path:
            parser.error("Informe o destino do backup")
        target = Path(args.path).resolve()
        if target.exists():
            parser.error("Destino já existe; não será sobrescrito")
        target.parent.mkdir(parents=True, exist_ok=True)
        # exclusive create + restrictive permissions before SQLite opens it
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        try:
            with db() as source, sqlite3.connect(target) as backup:
                source.backup(backup)
                if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup inválido")
            print("Backup consistente criado. Proteja este arquivo: contém dados privados.")
        except Exception:
            target.unlink(missing_ok=True)
            raise
    else:
        if not args.confirm_stopped or not args.path:
            parser.error("Pare a aplicação, informe o backup e --confirm-stopped")
        source = Path(args.path).resolve()
        if not source.is_file():
            parser.error("Backup não encontrado")
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as c:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                parser.error("Integridade do backup falhou")
            if c.execute("SELECT version FROM schema_version").fetchone()[0] != 1:
                parser.error("Versão incompatível")
            DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = DATA / "saly.sqlite3"
            if target.exists():
                parser.error(
                    "Banco existente: preserve-o e escolha SALY_DATA_DIR vazio para recuperação"
                )
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with sqlite3.connect(target) as out:
                c.backup(out)
                # Invalidate old authenticated sessions after disaster recovery.
                out.execute("DELETE FROM sessions")
        print("Banco restaurado; sessões antigas invalidadas. Faça login novamente.")


if __name__ == "__main__":
    main()
