"""record_user_statement: what the customer says, kept apart from proven facts."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "record_user_statement",
    "description": "Record something the customer told you (in their story or an answer) that no evidence shows. "
    "It supports a checklist item only as the customer's own statement, never as proof.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "item": {"type": "string", "description": "checklist item id"},
            "statement": {"type": "string", "description": "what the customer said, in their words where possible"},
        },
        "required": ["item", "statement"],
    },
}


def run(ctx, args: dict) -> dict:
    entry = ctx.case.record_user_statement(str(args.get("item", "")), str(args.get("statement", "")))
    return {"recorded": entry, "coverage": ctx.case.coverage()}
