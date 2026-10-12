"""The pace of the model client, without a model: it sends ten calls one after the other and then waits half a
second; a call the service turns down with a 4xx is sent once more after half a second; turned down twice in a
row with a 403 or 429, the client is halted and sends nothing more; a call that is wrong twice has no answer and
halts nothing. A stand-in answers in the place of the service.

    python3 tests/client.py
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import Config  # noqa: E402
from docket.model import client as model  # noqa: E402


class Reply:
    """What the service sends back for a call it answers."""

    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return json.dumps({"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]}).encode("utf-8")


def main() -> int:
    failed = False

    def ok(passed: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not passed
        print(("ok   " if passed else "FAIL ") + text)

    waits = [model.rest(calls) for calls in range(81)]
    ok(waits[0] == 0 and all(w == 0 for w in waits[1:10]) and waits[10] == 0.5 and waits[11] == 0 and waits[40] == 0.5
       and sum(waits) == 4.0,
       "the client sends ten calls one after the other and then waits half a second: four seconds in eighty calls")

    script: list[int] = []
    times: list[float] = []

    def stand_in(request, timeout=None):
        times.append(time.time())
        status = script.pop(0) if script else 200
        if status == 200:
            return Reply()
        raise urllib.error.HTTPError(request.full_url, status, "turned down", {}, io.BytesIO(b"{}"))

    real = model.urllib.request.urlopen
    model.urllib.request.urlopen = stand_in
    try:
        config = Config(model="none", base_url="http://localhost:9", api_key="made-up", data_dir=ROOT, storage_dir=ROOT)

        client = model.Client(config)
        script[:] = [200, 403, 200, 200]
        answers = [model.ask(client, "x") for _ in range(3)]
        ok(all(a is not None and a.text == "ok" for a in answers) and len(times) == 4 and times[2] - times[1] >= 0.48
           and times[3] - times[2] < 0.4 and client.halted == 0,
           "a call answered with a 403 is sent once more after half a second; answered then, the client goes on")

        client = model.Client(config)
        script[:] = [400, 400, 200]
        times.clear()
        answers = [model.ask(client, "x"), model.ask(client, "x")]
        ok(answers[0] is None and answers[1] is not None and len(times) == 3 and client.halted == 0,
           "a call that is wrong twice has no answer and halts nothing")

        client = model.Client(config)
        script[:] = [200, 429, 429, 200]
        times.clear()
        answers = [model.ask(client, "x") for _ in range(4)]
        ok(answers[0] is not None and all(a is None for a in answers[1:]) and len(times) == 3 and client.halted == 429,
           "turned down twice in a row with a 403 or 429, the client is halted: the calls behind it are not sent")
    finally:
        model.urllib.request.urlopen = real
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
