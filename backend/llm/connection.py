"""A real, minimal inference/tool roundtrip; no private memory or documents are sent."""

import asyncio
import json
import time
from datetime import UTC, datetime

from ..agent.registry import REGISTRY
from ..tools import calculate
from .provider import ProviderError


async def verify_connection(provider):
    provider.last_probe = None
    started = time.monotonic()
    health = await provider.health()
    if not health["model_ready"]:
        raise ProviderError(503, health["detail"])
    definition = {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calcular uma expressão aritmética.",
            "parameters": REGISTRY["calculate"][0].model_json_schema(),
        },
    }
    messages = [
        {
            "role": "system",
            "content": "Teste técnico de conexão. Use calculate para calcular 2+2 e depois confirme o resultado em português. Não há dados pessoais neste teste.",
        },
        {"role": "user", "content": "Calcule 2+2 usando a ferramenta."},
    ]
    calls = {}
    first_text = ""
    completed = False
    async with asyncio.timeout(60):
        async for event in provider.stream(
            messages,
            [definition],
            tool_choice={"type": "function", "function": {"name": "calculate"}},
            max_tokens=160,
        ):
            first_text += event.get("text", "")
            completed = completed or event.get("done", False)
            for part in event.get("tool_calls", []):
                index = part["index"]
                if index not in calls:
                    calls[index] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                call = calls[index]
                if part.get("id"):
                    call["id"] = part["id"]
                for key in ("name", "arguments"):
                    call["function"][key] += part.get("function", {}).get(key, "")
                if len(calls) > 1 or len(call["function"]["arguments"]) > 1000:
                    raise ProviderError(
                        502, "Teste de ferramenta fora dos limites; nenhum comando foi executado."
                    )
        if not completed or len(calls) != 1:
            raise ProviderError(
                502,
                "O modelo não confirmou uma chamada de ferramenta. Revise o modelo configurado.",
            )
        call = next(iter(calls.values()))
        if call["function"]["name"] != "calculate" or not call["id"]:
            raise ProviderError(502, "O modelo não confirmou a ferramenta de cálculo.")
        try:
            args = REGISTRY["calculate"][0].model_validate(
                json.loads(call["function"]["arguments"])
            )
            result = calculate(args.expression)
        except (ValueError, SyntaxError, ArithmeticError):
            raise ProviderError(
                502, "O modelo enviou argumentos inválidos no teste de conexão."
            ) from None
        if result != 4:
            raise ProviderError(502, "O cálculo de diagnóstico não confirmou o resultado esperado.")
        messages += [
            {"role": "assistant", "content": first_text or None, "tool_calls": [call]},
            {"role": "tool", "tool_call_id": call["id"], "content": json.dumps({"result": result})},
        ]
        response = ""
        completed = False
        async for event in provider.stream(messages, max_tokens=160):
            response += event.get("text", "")
            completed = completed or event.get("done", False)
        if not completed or not response.strip():
            raise ProviderError(
                502, "O provedor não concluiu a resposta após receber o resultado da ferramenta."
            )
    verified = {
        "model": provider.model,
        "inference": True,
        "streaming": True,
        "agent": True,
        "tool": "calculate",
        "tool_result": result,
        "checked_at": datetime.now(UTC).isoformat(),
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "detail": "Modelo remoto respondeu, chamou a calculadora e recebeu o resultado confirmado.",
    }
    provider.last_probe = verified
    return verified
