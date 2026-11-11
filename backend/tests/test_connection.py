import asyncio
import json

import httpx
import pytest
from dotenv import dotenv_values

from backend import connect_model
from backend.connect_model import persist_configuration
from backend.llm.connection import verify_connection
from backend.llm.provider import Provider, ProviderError


def model_transport(request):
    if request.url.path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": "test-model"}]})
    payload = json.loads(request.content)
    if payload.get("tools"):
        assert payload["tool_choice"]["function"]["name"] == "calculate"
        assert payload["max_tokens"] == 160
        delta = {
            "tool_calls": [
                {
                    "index": 0,
                    "id": "connection-call",
                    "function": {
                        "name": "calculate",
                        "arguments": json.dumps({"expression": "2+2"}),
                    },
                }
            ]
        }
        end = "tool_calls"
    else:
        assert json.loads(payload["messages"][-1]["content"]) == {"result": 4}
        delta = {"content": "O resultado confirmado é 4."}
        end = "stop"
    return httpx.Response(
        200,
        content="data: "
        + json.dumps({"choices": [{"delta": delta}]})
        + "\n\ndata: "
        + json.dumps({"choices": [{"delta": {}, "finish_reason": end}]})
        + "\n\n",
    )


def test_connection_checks_real_http_protocol_and_calculator(monkeypatch):
    p = Provider()
    p.key = "test-only-key"
    p.model = "test-model"
    requests = []

    def handler(request):
        requests.append(request)
        return model_transport(request)

    monkeypatch.setattr(
        p, "client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    result = asyncio.run(verify_connection(p))
    assert (
        result["inference"]
        and result["streaming"]
        and result["agent"]
        and result["tool_result"] == 4
    )
    assert len(requests) == 3 and p.last_probe == result
    assert "test-only-key" not in json.dumps(result)
    assert all("memories" not in r.content.decode() for r in requests)


def test_probe_never_claims_agent_ready_if_model_ignores_tools(monkeypatch):
    p = Provider()
    p.key = "test-only-key"
    p.model = "test-model"

    def handler(request):
        if request.url.path.endswith("/models"):
            return model_transport(request)
        return httpx.Response(
            200, content=b'data: {"choices":[{"delta":{"content":"4"},"finish_reason":"stop"}]}\n\n'
        )

    monkeypatch.setattr(
        p, "client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderError):
        asyncio.run(verify_connection(p))
    assert p.last_probe is None


def test_standard_groq_secret_binding_supported_without_copying(monkeypatch, tmp_path):
    monkeypatch.setenv("SALY_LLM_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "test-injected-key")
    p = Provider()
    assert p.key == "test-injected-key"
    file = tmp_path / ".env"
    file.write_text("SALY_DATA_DIR=./existing-data\n")
    persist_configuration(file, p)
    assert "test-injected-key" not in file.read_text()
    assert dotenv_values(file)["SALY_DATA_DIR"] == "./existing-data"


def test_private_configuration_preserves_existing_settings_and_rejects_symlinks(tmp_path):
    file = tmp_path / ".env"
    file.write_text("SALY_DATA_DIR=./existing-data\n# retain this setting\n")
    p = Provider()
    p.model = "test-model"
    persist_configuration(file, p, "test-new-key")
    assert file.stat().st_mode & 0o777 == 0o600
    assert dotenv_values(file)["SALY_LLM_API_KEY"] == "test-new-key"
    assert dotenv_values(file)["SALY_DATA_DIR"] == "./existing-data"
    assert "# retain this setting" in file.read_text()
    link = tmp_path / "linked"
    link.symlink_to(file)
    before = file.read_bytes()
    with pytest.raises(ValueError):
        persist_configuration(link, p, "another-key")
    assert file.read_bytes() == before
    assert not list(tmp_path.glob(".saly-env-*"))


def test_failed_private_connection_does_not_save_or_print_key(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SALY_LLM_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setattr(connect_model, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["connect_model"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(connect_model.getpass, "getpass", lambda _: "test-secret-not-for-logs")

    async def fail(provider):
        raise ProviderError(403, "Acesso não confirmado")

    async def catalog(provider):
        return [provider.model]

    monkeypatch.setattr(Provider, "available_models", catalog)
    monkeypatch.setattr(connect_model, "verify_connection", fail)
    assert connect_model.main() == 1
    output = capsys.readouterr()
    assert "test-secret-not-for-logs" not in output.out + output.err
    assert not (tmp_path / ".env").exists()


def test_check_mode_needs_no_terminal_and_never_creates_credentials(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SALY_LLM_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setattr(connect_model, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["connect_model", "--check"])
    assert connect_model.main() == 2
    assert "configure SALY_LLM_API_KEY" in capsys.readouterr().err
    assert not (tmp_path / ".env").exists()


def test_groq_binding_not_sent_to_another_provider(monkeypatch):
    monkeypatch.setenv("SALY_LLM_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-only-key")
    monkeypatch.setenv("SALY_LLM_BASE_URL", "https://other-provider.example/v1")
    p = Provider()
    assert p.key == "" and not p.configured


def test_wizard_replaces_retired_model_only_after_explicit_choice_and_probe(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.setenv("SALY_LLM_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("SALY_MODEL", "retired-model")
    monkeypatch.setattr(connect_model, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["connect_model"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr(connect_model.getpass, "getpass", lambda _: "test-private-key")
    choices = iter(["0", "invalid", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(choices))
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers["Authorization"] == "Bearer test-private-key"
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "voice-model"}, {"id": "test-model"}]})
        assert json.loads(request.content)["model"] == "test-model"
        return model_transport(request)

    monkeypatch.setattr(
        Provider, "client", lambda _: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    env = tmp_path / ".env"
    env.write_text("SALY_DATA_DIR=./preserved\nSALY_MODEL=retired-model\n")
    assert connect_model.main() == 0
    values = dotenv_values(env)
    assert values["SALY_MODEL"] == "test-model"
    assert values["SALY_LLM_API_KEY"] == "test-private-key"
    assert values["SALY_DATA_DIR"] == "./preserved"
    assert env.stat().st_mode & 0o777 == 0o600
    assert len(requests) == 4
    output = capsys.readouterr()
    assert "test-private-key" not in output.out + output.err
    assert "1. test-model" in output.out and "2. voice-model" in output.out
    assert "2+2=4" in output.out


@pytest.mark.parametrize("mode", ["check", "explicit", "noninteractive", "cancel"])
def test_missing_model_never_silently_substituted(monkeypatch, capsys, mode):
    p = Provider()
    p.key, p.model = "test-key", "retired-model"

    async def catalog():
        return ["available-model"]

    async def unexpected_probe(provider):
        pytest.fail("An unconfirmed model must never be used for inference")

    def choice(_):
        assert mode == "cancel", "This mode must not request interactive input"
        return ""

    monkeypatch.setattr(p, "available_models", catalog)
    monkeypatch.setattr(connect_model, "verify_connection", unexpected_probe)
    monkeypatch.setattr("sys.stdin.isatty", lambda: mode != "noninteractive")
    monkeypatch.setattr("builtins.input", choice)
    with pytest.raises(ProviderError):
        asyncio.run(
            connect_model.connect(p, check=mode == "check", explicit_model=mode == "explicit")
        )
    assert p.model == "retired-model"
    assert "available-model" in capsys.readouterr().out


def test_empty_catalog_does_not_prompt_or_probe(monkeypatch):
    p = Provider()

    async def catalog():
        return []

    monkeypatch.setattr(p, "available_models", catalog)
    with pytest.raises(ProviderError, match="não anunciou modelos ativos"):
        asyncio.run(connect_model.connect(p))


def test_choose_model_allows_explicit_change_even_when_current_model_exists(monkeypatch):
    p = Provider()
    p.model = "existing-model"

    async def catalog():
        return ["existing-model", "new-model"]

    async def probe(provider):
        assert provider.model == "new-model"
        return {"verified": True}

    monkeypatch.setattr(p, "available_models", catalog)
    monkeypatch.setattr(connect_model, "verify_connection", probe)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: "2")
    assert asyncio.run(connect_model.connect(p, choose_model=True)) == {"verified": True}
