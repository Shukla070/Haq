"""HTTP API for the app. Each agent run executes in its own thread, apart from the
request that started it, and the app polls GET /cases/{id} for progress.

Each app install makes a random device token and sends it in the X-Haq-Device header.
A case belongs to the install that created it: the server stores only a hash of the
token, and any other token gets 404, as if the case did not exist. There are no
accounts, so nothing ties a case to a person's name or phone number.

    uvicorn haq.api:app --reload      (from server/)
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import re
import secrets
import shutil
import tempfile
import threading
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import agent, config, evidence, rules
from .case import Case, CaseError, cases_dir, now
from .llm import make_client

config.load_env()
app = FastAPI(title="Haq API", version="0.2.0")
log = logging.getLogger("haq.api")
_running: set = set()
_lock = threading.Lock()

_DEVICE = re.compile(r"[A-Za-z0-9_-]{32,128}")
_CASE_ID = re.compile(r"case-\d{8}-\d{6}-[0-9a-f]{6}")
MAX_UPLOAD = 32 * 1024 * 1024  # the voice transcriber's own limit, and plenty for a screenshot or statement

# What the app shows while the agent works, by the tool it last called.
PROGRESS = {
    "list_evidence": "Reading your evidence",
    "read_evidence": "Reading your evidence",
    "classify_dispute": "Working out what went wrong",
    "record_fact": "Checking facts against your evidence",
    "record_user_statement": "Noting what you told us",
    "add_timeline_event": "Putting the dates in order",
    "calculate_entitlement": "Calculating what you are owed",
    "check_escalation": "Checking where to complain",
    "ask_user": "Preparing a question for you",
    "refer_out": "Finding the right place for this",
    "submit_draft": "Writing your complaint",
    "hold_case": "Checking your deadlines",
}


class NewCase(BaseModel):
    story: str
    name: str = ""  # the customer's name, to sign the complaint


class Answer(BaseModel):
    text: str


class Sent(BaseModel):
    on: str = ""  # YYYY-MM-DD; empty means today


def _owner(device: str | None) -> str:
    if not device or not _DEVICE.fullmatch(device):
        raise HTTPException(status_code=401, detail="send this install's device token in the X-Haq-Device header")
    return hashlib.sha256(device.encode()).hexdigest()


def _load(case_id: str, device: str | None) -> Case:
    owner = _owner(device)
    missing = HTTPException(status_code=404, detail="no such case")
    if not _CASE_ID.fullmatch(case_id):
        raise missing
    try:
        case = Case.load(case_id)
    except CaseError:
        raise missing from None
    if not secrets.compare_digest(case.data.get("owner") or "", owner):
        raise missing
    return case


def _attachable(item: dict) -> bool:
    """Can this file go out with the customer's email? The stored file is the original, so a
    file with a sensitive number in it stays back, and a voice note is not proof for a bank."""
    return item["kind"] != "voice" and not item["masked"]


def _progress(case: Case) -> dict | None:
    path = case.folder / "run.json"
    if not path.is_file():
        return None
    run = json.loads(path.read_text(encoding="utf-8"))
    steps = []
    for turn in run.get("turns", []):
        label = PROGRESS.get(turn.get("tool"))
        if label and label not in steps:
            steps.append(label)
    return {
        "current": steps[-1] if steps else "Starting",
        "steps": steps,
        "turn": run.get("turn", 0),
        "drafts_refused": sum(1 for t in run.get("turns", []) if t.get("tool") == "submit_draft" and t.get("error")),
        "seconds": run.get("seconds"),
    }


def _view(case: Case) -> dict:
    data = case.data
    passed = [d for d in data["drafts"] if d["passed"]]
    return {
        **case.summary(),
        "running": case.id in _running,
        "progress": _progress(case),
        "checklist": data["checklist"],
        "evidence": [
            {**{k: e[k] for k in ("id", "kind", "original_name", "note", "masked", "instruction_like")}, "attachable": _attachable(e)}
            for e in data["evidence"]
        ],
        "escalation": data["escalation"],
        "question": next((q for q in reversed(data["questions"]) if not q.get("answer")), None),
        "referral": data["referral"],
        "draft": passed[-1] if passed else None,
        "sent": data.get("sent", []),
    }


def _card(case: Case) -> dict:
    """One line on the home screen."""
    data = case.data
    entitlement = data.get("entitlement") or {}
    return {
        "id": case.id,
        "created": data["created"],
        "status": data["status"],
        "running": case.id in _running,
        "title": data["story"][:80],
        "dispute_type": data["dispute_type"],
        "compensation_owed": entitlement.get("compensation_owed"),
        "until": (data.get("hold") or {}).get("until"),
    }


def _work(case_id: str, message: str | None) -> None:
    try:
        case = Case.load(case_id)
        client = make_client()
        if message is None:
            agent.start(case, client)
        else:
            agent.resume(case, client, message)
    except Exception as error:  # never leave a case stuck at "working": pause it so the app can retry
        log.exception("run failed for %s", case_id)
        case = Case.load(case_id)
        case.data["status"] = "paused"
        case.log("run_failed", error=type(error).__name__)
        case.save()
    finally:
        with _lock:
            _running.discard(case_id)


def _schedule(case_id: str, message: str | None = None) -> None:
    with _lock:
        if case_id in _running:
            raise HTTPException(status_code=409, detail="the agent is already working on this case")
        _running.add(case_id)
    threading.Thread(target=_work, args=(case_id, message), name=f"run-{case_id}", daemon=True).start()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "model": config.model()}


@app.post("/cases")
def create_case(body: NewCase, x_haq_device: str | None = Header(None)) -> dict:
    owner = _owner(x_haq_device)
    if not body.story.strip():
        raise HTTPException(status_code=422, detail="tell us what happened")
    try:
        case = Case.create(body.story, owner=owner, name=body.name)
    except CaseError as problem:
        raise HTTPException(status_code=422, detail=str(problem)) from problem
    return _view(case)


@app.get("/cases")
def list_cases(x_haq_device: str | None = Header(None)) -> list:
    owner = _owner(x_haq_device)
    cards = []
    for path in cases_dir().glob("case-*/case.json"):
        case = Case(json.loads(path.read_text(encoding="utf-8")))
        if secrets.compare_digest(case.data.get("owner") or "", owner):
            cards.append(_card(case))
    return sorted(cards, key=lambda c: c["created"], reverse=True)


@app.get("/cases/{case_id}")
def get_case(case_id: str, x_haq_device: str | None = Header(None)) -> dict:
    return _view(_load(case_id, x_haq_device))


@app.delete("/cases/{case_id}")
def delete_case(case_id: str, x_haq_device: str | None = Header(None)) -> dict:
    case = _load(case_id, x_haq_device)
    with _lock:
        if case.id in _running:
            raise HTTPException(status_code=409, detail="the agent is working on this case; try again when it stops")
        shutil.rmtree(case.folder)
    return {"deleted": case.id}


@app.post("/cases/{case_id}/evidence")
def add_evidence(
    case_id: str, file: UploadFile = File(...), note: str = Form(""), x_haq_device: str | None = Header(None)
) -> dict:
    case = _load(case_id, x_haq_device)
    content = file.file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="the file is over 32 MB")
    name = Path(file.filename or "upload")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"{name.stem[:60]}{name.suffix}"
        path.write_bytes(content)
        try:
            item = evidence.add(case, path, make_client(), note)
        except CaseError as problem:
            raise HTTPException(status_code=422, detail=str(problem)) from problem
    return {k: item[k] for k in ("id", "kind", "original_name", "masked", "instruction_like")}


@app.get("/cases/{case_id}/evidence/{evidence_id}/file")
def evidence_file(case_id: str, evidence_id: str, x_haq_device: str | None = Header(None)) -> FileResponse:
    """The original file, for the customer's email to the bank."""
    case = _load(case_id, x_haq_device)
    try:
        item = case.evidence(evidence_id)
    except CaseError:
        raise HTTPException(status_code=404, detail="no such evidence") from None
    if not _attachable(item):
        raise HTTPException(status_code=409, detail="this file cannot be attached to the email")
    media_type = mimetypes.guess_type(item["original_name"])[0] or "application/octet-stream"
    return FileResponse(case.folder / "evidence" / item["file"], media_type=media_type, filename=item["original_name"])


@app.post("/cases/{case_id}/run", status_code=202)
def run_case(case_id: str, x_haq_device: str | None = Header(None)) -> dict:
    _load(case_id, x_haq_device)
    _schedule(case_id)
    return {"case_id": case_id, "running": True}


@app.post("/cases/{case_id}/answer", status_code=202)
def answer(case_id: str, body: Answer, x_haq_device: str | None = Header(None)) -> dict:
    case = _load(case_id, x_haq_device)
    open_questions = [q for q in case.data["questions"] if not q.get("answer")]
    if open_questions:
        open_questions[-1]["answer"] = body.text
        case.save()
    _schedule(case_id, f"The customer answered: {body.text}")
    return {"case_id": case_id, "running": True}


@app.post("/cases/{case_id}/sent")
def mark_sent(case_id: str, body: Sent, x_haq_device: str | None = Header(None)) -> dict:
    """The customer sent the verified draft themselves. A bank complaint starts the bank's
    reply period, so the case waits until it ends; the app reminds them on that date."""
    case = _load(case_id, x_haq_device)
    if case.id in _running:
        raise HTTPException(status_code=409, detail="the agent is working on this case")
    passed = [d for d in case.data["drafts"] if d["passed"]]
    if not passed:
        raise HTTPException(status_code=409, detail="there is no verified draft to send yet")
    step = passed[-1]["step"]
    try:
        sent_on = date.fromisoformat(body.on) if body.on else config.today()
    except ValueError:
        raise HTTPException(status_code=422, detail="on must be YYYY-MM-DD") from None
    if sent_on > config.today():
        raise HTTPException(status_code=422, detail="the date cannot be in the future")
    pack = rules.load(case.data["dispute_type"])
    data = case.data
    data.setdefault("sent", []).append({"step": step, "on": sent_on.isoformat(), "recorded": now()})
    data["timeline"].append({"date": sent_on.isoformat(), "event": f"Customer sent the {step} complaint", "evidence_id": None})
    if step == pack["ladder"][0]["id"]:
        position = rules.ladder_position(pack, config.today(), complained_on=sent_on)
        data["escalation"] = {**position, "as_of": config.today().isoformat()}
        until = position.get("bank_reply_due_by")
        data["status"] = "waiting" if until else "sent"
        data["hold"] = {
            "status": data["status"],
            "until": until,
            "then": "check again with check_escalation",
            "reason": f"Complaint sent to the bank on {sent_on.isoformat()}.",
            "message": f"You sent your complaint on {sent_on:%d %b %Y}. The bank has until {date.fromisoformat(until):%d %b %Y} "
            "to reply. If it has not fixed this by then, Haq will help you take it to the RBI Ombudsman."
            if until
            else "You sent your complaint. The bank's time to reply has already passed, so you can take it further now.",
            "set": now(),
        }
    else:
        data["status"] = "filed"
        data["hold"] = None
    case.log("sent", step=step, on=sent_on.isoformat())
    case.save()
    return _view(case)
