"""The agent's tools, one module per tool. Each module has DEFINITION (the function
schema the model sees) and run(ctx, args) -> dict. A result's "status" other than
"running" ends the agent run: draft_ready, needs_input, referred, waiting or resolved."""

from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI

from ..case import Case, CaseError
from . import (
    add_timeline_event,
    ask_user,
    calculate_entitlement,
    check_escalation,
    classify_dispute,
    hold_case,
    list_evidence,
    read_evidence,
    record_fact,
    record_user_statement,
    refer_out,
    submit_draft,
)

MODULES = [
    list_evidence,
    read_evidence,
    classify_dispute,
    record_fact,
    record_user_statement,
    add_timeline_event,
    calculate_entitlement,
    check_escalation,
    ask_user,
    refer_out,
    submit_draft,
    hold_case,
]
BY_NAME = {module.DEFINITION["name"]: module for module in MODULES}


@dataclass
class Context:
    case: Case
    client: OpenAI | None


def definitions() -> list:
    return [module.DEFINITION for module in MODULES]


def run(ctx: Context, call: dict) -> dict:
    """Run one function call from the model. Errors come back as results the model can read."""
    name = call.get("name", "")
    module = BY_NAME.get(name)
    if module is None:
        return {"status": "running", "error": f"unknown tool {name!r}"}
    try:
        args = json.loads(call.get("arguments") or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except ValueError as problem:
        return {"status": "running", "error": f"invalid arguments: {problem}"}
    try:
        result = module.run(ctx, args)
    except (CaseError, KeyError, ValueError) as problem:
        result = {"error": str(problem).strip("'\"")}
    ctx.case.save()
    return {"status": "running", **result}
