"""submit_draft: hand the complaint to the verifier. A draft that passes ends the run and
waits for the customer's approval; one that fails comes back with the problems to fix."""

from __future__ import annotations

from ..case import now
from ..verify import check

DEFINITION = {
    "type": "function",
    "name": "submit_draft",
    "description": "Submit the complaint draft for the current escalation step. A verifier checks it: the step, "
    "cited rules, facts, amounts, checklist coverage and sensitive data. If it fails you get the problems to fix. "
    "The customer approves and sends it themselves; nothing is sent automatically.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "step": {"type": "string", "description": "ladder step id, from check_escalation"},
            "recipient": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string", "description": "the full complaint, ready to send, polite and firm"},
            "fact_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "ids of recorded facts (F1, F2, ...) the draft relies on; user statements (U...) are not facts",
            },
            "rule_ids": {"type": "array", "items": {"type": "string"}},
            "gaps": {
                "type": "array",
                "description": "checklist items not settled, and why",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"item": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["item", "why"],
                },
            },
            "next_steps": {"type": "string", "description": "what the customer should do after sending, with dates"},
        },
        "required": ["step", "recipient", "subject", "body", "fact_ids", "rule_ids", "gaps", "next_steps"],
    },
}


def run(ctx, args: dict) -> dict:
    draft = {key: args.get(key) for key in DEFINITION["parameters"]["properties"]}
    for key in ("fact_ids", "rule_ids", "gaps"):
        draft[key] = draft.get(key) or []
    problems = check(ctx.case, draft)
    attempt = {**draft, "submitted": now(), "problems": problems, "passed": not problems}
    ctx.case.data["drafts"].append(attempt)
    if problems:
        ctx.case.log("draft_refused", problems=problems)
        return {"verified": False, "problems": problems, "hint": "Fix every problem and submit again."}
    ctx.case.data["status"] = "draft_ready"
    ctx.case.log("draft_verified", step=draft["step"])
    return {"status": "draft_ready", "verified": True}
