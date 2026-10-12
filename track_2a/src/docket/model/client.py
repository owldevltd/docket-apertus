"""The one door to the model.

Every call goes through one client, one after the other. The client takes a breath of half a second after every
BLOCK calls. When the service turns a call down with a 4xx, the client waits half a second and sends the same call
once more; if that one comes back with a 403 or 429 as well, nothing more is sent, so a run never looks like a
load test. The raw exchange is written per call with prompt, model, duration and finish reason, so a run can be
read back without the model.

Until 12 October 2026 the client paused two seconds before every call and twenty seconds before every fiftieth,
and halted at the first 403 or 429. Measured that day on 60 documents, 583 calls: 13 minutes were the model's and
about 20 minutes the client's own pauses. The pace below was set that day and is not measured against a limit:
the service names no limit in the headers of its answers.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from docket.config import Config

BLOCK = 10
PAUSE = 0.5
REFUSED = 0.5
TIMEOUT = 180


def rest(calls: int) -> float:
    """How long the client waits before its next call, after this many calls."""
    return PAUSE if calls > 0 and calls % BLOCK == 0 else 0.0


@dataclass
class Answer:
    text: str
    http: int
    usage: dict | None
    finish: str | None


@dataclass
class Client:
    config: Config
    calls: int = 0
    halted: int = 0
    # the raw exchange is numbered per process; the stamp keeps runs of several processes apart
    stamp: str = field(default_factory=lambda: format(int(time.time()), "x"))


def ask(
    client: Client,
    prompt: str,
    *,
    image: bytes | None = None,
    room: int = 400,
    log: Path | None = None,
    tag: str | None = None,
    model: str | None = None,
) -> Answer | None:
    """Asks the model and returns the answer, or None after a halt, without a key or on an error."""
    if client.halted or not client.config.api_key:
        return None
    http, result = _once(client, prompt, image, room, log, tag, model)
    if 400 <= http < 500:
        time.sleep(REFUSED)
        http, result = _once(client, prompt, image, room, log, tag, model)
        if http in (403, 429):
            client.halted = http
    return result


def _once(
    client: Client,
    prompt: str,
    image: bytes | None,
    room: int,
    log: Path | None,
    tag: str | None,
    model: str | None,
) -> tuple[int, Answer | None]:
    """One call as it goes out: the status and the answer."""
    wait = rest(client.calls)
    if wait:
        time.sleep(wait)
    client.calls += 1

    content: list[dict] = [{"type": "text", "text": prompt}]
    if image:
        data = base64.b64encode(image).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + data}})
    body = {
        "model": model or client.config.model,
        "temperature": 0,
        "max_tokens": room,
        "messages": [{"role": "user", "content": content}],
    }
    started = time.time()
    http = 0
    answer: dict = {}
    error = None
    request = urllib.request.Request(
        client.config.base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + client.config.api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            http = response.status
            answer = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        http = e.code
        answer = {"body": e.read().decode("utf-8", errors="replace")}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        error = "timeout" if isinstance(e, TimeoutError) else str(e)

    choices = answer.get("choices") or [{}]
    text = (choices[0].get("message") or {}).get("content") if choices else None
    result = None
    if isinstance(text, str):
        result = Answer(text.strip(), http, answer.get("usage"), choices[0].get("finish_reason"))
    if log is not None:
        log.mkdir(parents=True, exist_ok=True)
        record = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(started)),
            "tag": tag,
            "model": body["model"],
            "temperature": 0,
            "room": room,
            "prompt": prompt,
            "image": len(image) if image else 0,
            "ms": int((time.time() - started) * 1000),
            "http": http,
            "error": error,
            "answer": answer,
        }
        target = log / f"{client.stamp}-{client.calls:04d}.json"
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return http, result
