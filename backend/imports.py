"""Explicit formats and sanitized validation errors for personal memory imports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .services import Memory


class MemoryImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["saly-memory-v2"] = "saly-memory-v2"
    memories: list[Memory] = Field(min_length=1, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def separate_core(cls, value):
        if isinstance(value, dict) and (
            value.get("arquivo") == "SALY_CORE_MEMORY_v1.json"
            or value.get("tipo") == "semente_de_conhecimento_politicas_e_testes"
        ):
            raise ValueError(
                "Este arquivo é Core Memory. Use a verificação administrativa do Core; ele não é uma lista de memórias pessoais."
            )
        return value


def validation_details(errors):
    """Never return input values, secrets or Pydantic context objects."""
    fields = []
    for error in errors[:20]:
        location = ".".join(str(part)[:80] for part in error["loc"] if part != "body") or "arquivo"
        messages = {
            "missing": "campo obrigatório ausente",
            "list_type": "deve ser uma lista",
            "string_type": "deve ser texto",
            "string_too_short": "texto vazio ou curto demais",
            "too_short": "a lista está vazia",
            "too_long": "limite de itens excedido",
            "literal_error": "valor fora das opções permitidas",
            "extra_forbidden": "campo não permitido neste formato",
            "model_attributes_type": "deve ser um objeto JSON",
            "model_type": "deve ser um objeto JSON",
        }
        message = messages.get(error["type"], "valor incompatível com o formato esperado")
        if error["type"] == "value_error":
            safe_message = error.get("msg", "").removeprefix("Value error, ")
            if safe_message in {
                "Fuso horário inválido",
                "Horário inexistente neste fuso",
                "Horário ambíguo: forneça um deslocamento UTC explícito",
                "Intervalo do evento inválido ou acima de um ano",
                "Alarme deve estar entre os anos 2000 e 2200",
                "A data inicial deve corresponder ao padrão de repetição",
                "A recorrência não pode iniciar em horário civil ambíguo; escolha outro início",
                "Use recorrência diária, semanal, mensal ou anual",
                "Campo de recorrência não suportado",
                "Intervalo/contagem de recorrência fora do limite",
                "Dias da semana inválidos",
                "Dia do mês inválido",
                "UNTIL deve ser um instante UTC YYYYMMDDTHHMMSSZ",
                "Escolha UNTIL ou COUNT, não os dois",
            }:
                message = safe_message
        if error["type"] == "value_error" and "Core Memory" in error.get("msg", ""):
            message = "Core Memory não é memória pessoal; use a verificação administrativa do Core."
        fields.append({"field": location, "message": message, "type": error["type"]})
    return fields
