"""Private terminal connection wizard. Never accepts a key in argv or exposes it to the browser."""

import argparse
import asyncio
import getpass
import os
import sys
import tempfile
from pathlib import Path

from dotenv import set_key

from . import storage  # noqa: F401 - same .env initialization as the application, no DB initialization
from .llm.connection import verify_connection
from .llm.provider import Provider, ProviderError

ROOT = Path(__file__).resolve().parents[1]


async def connect(provider, *, check=False, explicit_model=False, choose_model=False):
    models = await provider.available_models()
    if not models:
        raise ProviderError(503, "O provedor não anunciou modelos ativos para esta conta.")
    if provider.model not in models or choose_model:
        if provider.model not in models:
            print(f"O modelo configurado {provider.model!r} não aparece no catálogo atual.")
        print("Modelos ativos retornados pelo provedor:")
        for index, model in enumerate(models, start=1):
            print(f"  {index}. {model}")
        print(
            "Escolha um modelo de conversa com ferramentas; modelos de voz/transcrição não servem para este agente. A lista não confirma preço ou cota gratuita."
        )
        if check or explicit_model or not sys.stdin.isatty():
            raise ProviderError(
                503,
                "Escolha um ID da lista com --model IDENTIFICADOR ou execute bash scripts/connect-model.sh em um terminal interativo. Nenhum modelo foi substituído.",
            )
        while True:
            choice = input("Número do modelo (Enter cancela): ").strip()
            if not choice:
                raise ProviderError(503, "Seleção cancelada. Configuração preservada.")
            if choice.isascii() and choice.isdecimal() and 1 <= int(choice) <= len(models):
                provider.model = models[int(choice) - 1]
                break
            print("Digite um dos números da lista.")
    return await verify_connection(provider)


def persist_configuration(path, provider, new_key=None):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("O arquivo .env não pode ser um link simbólico.")
    before = path.read_bytes() if path.exists() else None
    if path.exists() and not path.is_file():
        raise ValueError(".env não é um arquivo regular.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".saly-env-", delete=False
        ) as output:
            temporary = Path(output.name)
            if before is not None:
                output.write(before)
        set_key(temporary, "SALY_LLM_BASE_URL", provider.base, quote_mode="always")
        set_key(temporary, "SALY_MODEL", provider.model, quote_mode="always")
        # Injected bindings, including proxy placeholders, are never copied to disk.
        if new_key is not None:
            set_key(temporary, "SALY_LLM_API_KEY", new_key, quote_mode="always")
        if path.is_symlink() or (path.read_bytes() if path.exists() else None) != before:
            raise ValueError(
                "A configuração foi alterada durante a conexão. Nenhum valor foi sobrescrito."
            )
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Conectar modelo remoto e agente Saly no terminal privado"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verificar configuração existente sem solicitar ou salvar valores",
    )
    parser.add_argument(
        "--model",
        help="Identificador de modelo disponível no provedor; não altera o valor silenciosamente",
    )
    parser.add_argument(
        "--choose-model",
        action="store_true",
        help="Listar e escolher outro modelo do catálogo atual",
    )
    args = parser.parse_args()
    if args.choose_model and (args.check or args.model):
        parser.error("--choose-model não pode ser combinado com --check ou --model")
    provider = Provider()
    if args.model:
        provider.model = args.model
    new_key = None
    if not provider.key:
        if args.check:
            print(
                "Conexão pendente: configure SALY_LLM_API_KEY ou GROQ_API_KEY no servidor. Uma chave pode ser criada em https://console.groq.com/keys. Não envie a chave em chat.",
                file=sys.stderr,
            )
            return 2
        if not sys.stdin.isatty():
            print(
                "Execute este comando em um terminal privado interativo. Não passe a chave como argumento.",
                file=sys.stderr,
            )
            return 2
        print(
            "Agente Saly usa o mesmo modelo; não há assinatura adicional de agente. Confirme a modalidade gratuita/cota da sua conta no provedor."
        )
        print(
            "Para Groq, crie sua chave em https://console.groq.com/keys. Ela será lida de forma oculta e salva somente no .env privado após o teste."
        )
        new_key = getpass.getpass("Chave do provedor (entrada oculta): ").strip()
        if not new_key:
            print("Nenhuma chave fornecida. Configuração preservada.", file=sys.stderr)
            return 2
        provider.key = new_key
    try:
        result = asyncio.run(
            connect(
                provider,
                check=args.check,
                explicit_model=args.model is not None,
                choose_model=args.choose_model,
            )
        )
        if not args.check:
            persist_configuration(ROOT / ".env", provider, new_key)
    except (ProviderError, TimeoutError, ValueError, OSError) as error:
        detail = (
            error.detail
            if isinstance(error, ProviderError)
            else "Não foi possível verificar ou salvar a conexão; configuração anterior preservada."
        )
        print("Conexão não concluída: " + detail, file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("Conexão cancelada. Configuração preservada.", file=sys.stderr)
        return 2
    print(f"Conexão verificada: {result['model']} · streaming · agente · cálculo confirmado 2+2=4.")
    if not args.check:
        print(
            "Reinicie a SALY para carregar a configuração: SALY_SECURE_COOKIE=1 bash scripts/start.sh"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
