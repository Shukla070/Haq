"""record_fact: add evidence-backed support for one checklist item."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "record_fact",
    "description": "Record a fact for one checklist item, backed by an exact quote from one evidence item. "
    "Refused unless the quote appears in that evidence's text.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "item": {"type": "string", "description": "checklist item id"},
            "evidence_id": {"type": "string"},
            "quote": {"type": "string", "description": "copied exactly from the evidence text"},
            "claim": {"type": "string", "description": "what the quote establishes, in one sentence"},
        },
        "required": ["item", "evidence_id", "quote", "claim"],
    },
}


def run(ctx, args: dict) -> dict:
    fact = ctx.case.record_fact(
        str(args.get("item", "")),
        str(args.get("evidence_id", "")),
        str(args.get("quote", "")),
        str(args.get("claim", "")),
    )
    return {"recorded": fact, "coverage": ctx.case.coverage()}
