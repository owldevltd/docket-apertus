"""The queue of runs behind the admin: an uploaded PDF or a document of OpenParlData goes in, one worker
takes the runs one after the other (the model is called one call at a time anyway), every run lands under
storage/runs/<id>/ with its lines and its result, so it can be read after a restart."""

from __future__ import annotations

import json
import queue
import re
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from docket.config import Config
from docket.runner import run_affairs
from docket.store.base import stamp

API = "https://api.openparldata.ch/v1"
PDF_LIMIT = 64 * 1024 * 1024
TIMEOUT = 60


@dataclass
class Job:
    id: str
    name: str
    source: str
    model: bool
    state: str = "queued"
    created: str = field(default_factory=stamp)
    started: str | None = None
    finished: str | None = None
    lines: list[str] = field(default_factory=list)
    affairs: list[dict] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    calls: int = 0
    error: str | None = None


class Jobs:
    def __init__(self, config: Config):
        self.config = config
        self.folder = config.storage_dir / "runs"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.queue: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._load()
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    # ---- submitting

    def submit_pdf(self, name: str, data: bytes, model: bool) -> Job:
        """A PDF from an upload."""
        if not data.startswith(b"%PDF"):
            raise ValueError("the upload is not a PDF")
        if len(data) > PDF_LIMIT:
            raise ValueError("the PDF is too large")
        job = self._new(_safe(name) or "upload", "upload", model)
        (self.folder / job.id / f"{job.name}.pdf").write_bytes(data)
        self._enqueue(job)
        return job

    def submit_document(self, doc_id: int, model: bool) -> Job:
        """A document of OpenParlData by its id: the file comes from their file server."""
        with urllib.request.urlopen(f"{API}/docs/{int(doc_id)}", timeout=TIMEOUT) as r:
            answer = json.loads(r.read().decode("utf-8"))
        doc = answer.get("data", answer)
        url = doc.get("url_oparl") or doc.get("url")
        if not url:
            raise ValueError(f"document {doc_id} has no file")
        name = _safe(str(doc.get("name") or f"doc-{doc_id}"))[:60] or f"doc-{doc_id}"
        job = self._new(name, f"openparldata:{int(doc_id)}", model)
        request = urllib.request.Request(url, headers={"User-Agent": "docket"})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as r:
            data = r.read(PDF_LIMIT + 1)
        if not data.startswith(b"%PDF") or len(data) > PDF_LIMIT:
            job.state, job.error = "failed", "the file is not a PDF or too large"
            self._save(job)
            return job
        (self.folder / job.id / f"{job.name}.pdf").write_bytes(data)
        self._enqueue(job)
        return job

    def list(self) -> list[dict]:
        with self._lock:
            jobs = sorted(self.jobs.values(), key=lambda j: j.created, reverse=True)
            return [self._summary(j) for j in jobs]

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            job = self.jobs.get(job_id)
            return asdict(job) if job else None

    def stop(self) -> None:
        self.queue.put(None)

    # ---- inside

    def _new(self, name: str, source: str, model: bool) -> Job:
        job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + format(int(time.time() * 1000) % 1000, "03d")
        job = Job(job_id, name, source, model)
        (self.folder / job_id).mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.jobs[job_id] = job
        self._save(job)
        return job

    def _enqueue(self, job: Job) -> None:
        self.queue.put(job.id)

    def _work(self) -> None:
        while True:
            job_id = self.queue.get()
            if job_id is None:
                return
            job = self.jobs.get(job_id)
            if job is None:
                continue
            job.state, job.started = "running", stamp()
            self._save(job)
            try:
                pdf = self.folder / job.id / f"{job.name}.pdf"
                result = run_affairs([pdf], self.folder / job.id, self.config, job.model, say=job.lines.append)
                job.affairs, job.documents, job.calls = result.affairs, result.documents, result.calls
                job.state = "failed" if result.halted or result.failed else "done"
                if result.halted:
                    job.error = f"halted after HTTP {result.halted}"
            except Exception as e:  # noqa: BLE001 - the worker must go on
                job.state, job.error = "failed", str(e)
            job.finished = stamp()
            self._save(job)

    def _save(self, job: Job) -> None:
        path = self.folder / job.id / "run.json"
        path.write_text(json.dumps(asdict(job), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _load(self) -> None:
        for path in self.folder.glob("*/run.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job = Job(**data)
            except (OSError, TypeError, ValueError):
                continue
            if job.state in ("queued", "running"):
                job.state, job.error = "failed", "the server stopped during the run"
                self._save(job)
            self.jobs[job.id] = job

    @staticmethod
    def _summary(job: Job) -> dict:
        data = asdict(job)
        data["lines"] = job.lines[-6:]
        return data


def _safe(name: str) -> str:
    stem = re.sub(r"\.pdf$", "", name.strip(), flags=re.I)
    return re.sub(r"[^\w.-]+", "_", stem).strip("_")
