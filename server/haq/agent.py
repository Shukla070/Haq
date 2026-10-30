"""The agent loop. Each turn the model picks one tool; code runs it, records the result,
and saves the run. The loop ends when a tool's status says so (draft_ready, needs_input,
referred, waiting, resolved), or at the turn limit, which pauses the run so it can resume.
Each turn records how long the model and the tool took, so slow runs can be explained."""

from __future__ import annotations

import json
import time
from pathlib import Path

from openai import OpenAI

from . import config, tools
from .case import Case, now, write_json
from .llm import plain

INSTRUCTIONS = (Path(__file__).resolve().parent / "prompts" / "system.md").read_text(encoding="utf-8")
NUDGE = "Call exactly one tool."
LAST_TURN = "This is your last turn: submit your draft with submit_draft, listing anything unsettled as gaps."


def _run_path(case: Case) -> Path:
    return case.folder / "run.json"


def _save_run(case: Case, run: dict) -> None:
    run["updated"] = now()
    write_json(_run_path(case), run)


def _signature(case: Case) -> str:
    name = case.data.get("customer_name")
    if name:
        return f"Sign the complaint with the customer's name: <name>{name}</name>"
    return "The customer has not given their name: sign the complaint \"[Your name]\" for them to fill in."


def _opening(case: Case) -> str:
    return (
        f"Today's date is {config.today().isoformat()}.\n\n"
        f"The customer's story, in their words:\n<story>\n{case.data['story']}\n</story>\n\n"
        f"{_signature(case)}\n\n"
        f"They have shared {len(case.data['evidence'])} evidence item(s). Work the case."
    )


def start(case: Case, client: OpenAI, turns: int = 25) -> dict:
    run = {"case_id": case.id, "model": config.model(), "started": now(), "turn": 0, "tokens": 0, "messages": [], "turns": []}
    run["messages"].append({"role": "user", "content": _opening(case)})
    return _loop(case, client, run, turns)


def resume(case: Case, client: OpenAI, message: str, turns: int = 15) -> dict:
    """Continue a stopped run with a new message: the customer's answer, or a note about new evidence."""
    path = _run_path(case)
    if not path.is_file():
        return start(case, client, turns)
    run = json.loads(path.read_text(encoding="utf-8"))
    run["messages"].append({"role": "user", "content": message})
    return _loop(case, client, run, turns)


def _loop(case: Case, client: OpenAI, run: dict, turns: int) -> dict:
    case.data["status"] = "working"
    case.data["hold"] = None  # a hold is only for now; a resumed run decides again
    case.save()
    began = time.monotonic()
    run.setdefault("seconds", 0.0)
    definitions = tools.definitions()
    ctx = tools.Context(case=case, client=client)
    for index in range(turns):
        if index == turns - 1:
            run["messages"].append({"role": "user", "content": LAST_TURN})
        asked = time.monotonic()
        try:
            response = client.responses.create(
                model=config.model(), instructions=INSTRUCTIONS, input=run["messages"], tools=definitions
            )
        except Exception as error:  # the SDK already retried; pause so the run can resume
            return _stop(case, run, "paused", began, note=str(error) or type(error).__name__)
        model_seconds = round(time.monotonic() - asked, 2)
        run["turn"] += 1
        usage = getattr(response, "usage", None)
        run["tokens"] += getattr(usage, "total_tokens", 0) or 0
        output = [plain(item) for item in (response.output or [])]
        run["messages"].extend(output)
        call = next((item for item in output if item.get("type") == "function_call"), None)
        if call is None:
            run["messages"].append({"role": "user", "content": NUDGE})
            run["turns"].append({"turn": run["turn"], "tool": None, "status": "running", "model_seconds": model_seconds})
            _save_run(case, run)
            continue
        started = time.monotonic()
        result = tools.run(ctx, call)
        tool_seconds = round(time.monotonic() - started, 2)
        status = result.get("status", "running")
        run["messages"].append(
            {"type": "function_call_output", "call_id": call.get("call_id"), "output": json.dumps(result, ensure_ascii=False)}
        )
        run["turns"].append(
            {
                "turn": run["turn"],
                "tool": call.get("name"),
                "status": status,
                "error": result.get("error") or result.get("problems"),
                "model_seconds": model_seconds,
                "tool_seconds": tool_seconds,
            }
        )
        _save_run(case, run)
        if status != "running":
            return _stop(case, run, status, began)
    return _stop(case, run, "paused", began, note="turn limit reached")


def _stop(case: Case, run: dict, status: str, began: float, note: str = "") -> dict:
    seconds = round(time.monotonic() - began, 1)
    run["seconds"] = round(run["seconds"] + seconds, 1)  # across every start and resume
    case.data["status"] = status
    case.log("run_stopped", status=status, turn=run["turn"], seconds=seconds, note=note)
    case.save()
    run["status"] = status
    _save_run(case, run)
    return {
        "case_id": case.id,
        "status": status,
        "turn": run["turn"],
        "tokens": run["tokens"],
        "seconds": seconds,
        "slowest_model_turn": max((t.get("model_seconds", 0) for t in run["turns"]), default=0),
        "note": note,
    }
