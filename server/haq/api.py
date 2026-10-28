"""HTTP API for the app. Skeleton: runs execute in a background thread, and the app polls
GET /cases/{id} for progress.

    uvicorn haq.api:app --reload      (from server/)
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from . import agent, config, evidence
from .case import Case, CaseError
from .llm import make_client

config.load_env()
app = FastAPI(title="Haq API", version="0.1.0")
_running: set = set()
_lock = threading.Lock()


class NewCase(BaseModel):
    story: str


class Answer(BaseModel):
    text: str


def _load(case_id: str) -> Case:
    try:
        return Case.load(case_id)
    except CaseError as problem:
        raise HTTPException(status_code=404, detail=str(problem)) from problem


def _view(case: Case) -> dict:
    data = case.data
    passed = [d for d in data["drafts"] if d["passed"]]
    return {
        **case.summary(),
        "running": case.id in _running,
        "checklist": data["checklist"],
        "evidence": [{k: e[k] for k in ("id", "kind", "original_name", "note", "masked", "instruction_like")} for e in data["evidence"]],
        "escalation": data["escalation"],
        "question": next((q for q in reversed(data["questions"]) if not q.get("answer")), None),
        "referral": data["referral"],
        "draft": passed[-1] if passed else None,
    }


def _work(case_id: str, message: str | None) -> None:
    try:
        case = Case.load(case_id)
        client = make_client()
        if message is None:
            agent.start(case, client)
        else:
            agent.resume(case, client, message)
    finally:
        with _lock:
            _running.discard(case_id)


def _schedule(case_id: str, background: BackgroundTasks, message: str | None = None) -> None:
    with _lock:
        if case_id in _running:
            raise HTTPException(status_code=409, detail="the agent is already working on this case")
        _running.add(case_id)
    background.add_task(_work, case_id, message)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": config.model()}


@app.post("/cases")
def create_case(body: NewCase) -> dict:
    if not body.story.strip():
        raise HTTPException(status_code=422, detail="tell us what happened")
    return _view(Case.create(body.story))


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict:
    return _view(_load(case_id))


@app.post("/cases/{case_id}/evidence")
def add_evidence(case_id: str, file: UploadFile = File(...), note: str = Form("")) -> dict:
    case = _load(case_id)
    suffix = Path(file.filename or "upload").suffix
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"{Path(file.filename or 'upload').stem[:60]}{suffix}"
        path.write_bytes(file.file.read())
        try:
            item = evidence.add(case, path, make_client(), note)
        except CaseError as problem:
            raise HTTPException(status_code=422, detail=str(problem)) from problem
    return {k: item[k] for k in ("id", "kind", "original_name", "masked", "instruction_like")}


@app.post("/cases/{case_id}/run", status_code=202)
def run_case(case_id: str, background: BackgroundTasks) -> dict:
    _load(case_id)
    _schedule(case_id, background)
    return {"case_id": case_id, "running": True}


@app.post("/cases/{case_id}/answer", status_code=202)
def answer(case_id: str, body: Answer, background: BackgroundTasks) -> dict:
    case = _load(case_id)
    open_questions = [q for q in case.data["questions"] if not q.get("answer")]
    if open_questions:
        open_questions[-1]["answer"] = body.text
        case.save()
    _schedule(case_id, background, f"The customer answered: {body.text}")
    return {"case_id": case_id, "running": True}
