"""Native text generation only; no cloud, no fake responses, no owner DB modification."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

report = {"models": [], "scope": "Geração textual em português; ferramentas/visão não verificadas"}
for name in ("granite4:3b", "ministral-3:3b", "phi4-mini", "gemma3:4b"):
    started = time.monotonic()
    item = {"model": name, "status": "unavailable"}
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(
                {
                    "model": name,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Em português, explique em uma frase por que plantas precisam de luz.",
                        }
                    ],
                    "stream": False,
                    "keep_alive": 0,
                    "options": {"num_ctx": 8192, "num_predict": 96, "num_thread": 4},
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=240) as response:
            result = json.load(response)
        item.update(
            status="functional"
            if result.get("done") and result.get("message", {}).get("content", "").strip()
            else "generation_failed",
            response=result.get("message", {}).get("content", "")[:2000],
        )
    except urllib.error.HTTPError as error:
        item.update(error="HTTPError", http_status=error.code)
    except (OSError, ValueError, TimeoutError) as error:
        item["error"] = type(error).__name__  # Never print arbitrary provider logs or credentials.
    item["seconds"] = round(time.monotonic() - started, 3)
    report["models"].append(item)
    print(json.dumps(item, ensure_ascii=False))
Path(".tools/ollama/probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
