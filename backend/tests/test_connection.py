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
