"""add_timeline_event: one dated event in the dispute."""

from __future__ import annotations

from datetime import date

DEFINITION = {
    "type": "function",
    "name": "add_timeline_event",
    "description": "Add a dated event to the case timeline (payment, failure, complaint, promise, reply, reversal).",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "event": {"type": "string"},
            "evidence_id": {"type": "string", "description": "the evidence showing it, or empty if the customer said it"},
        },
        "required": ["date", "event", "evidence_id"],
    },
}


def run(ctx, args: dict) -> dict:
    when = date.fromisoformat(str(args.get("date", "")))
    evidence_id = str(args.get("evidence_id") or "")
    if evidence_id:
        ctx.case.evidence(evidence_id)
    event = {"date": when.isoformat(), "event": str(args.get("event", "")), "evidence_id": evidence_id or None}
    ctx.case.data["timeline"].append(event)
    return {"added": event, "timeline_events": len(ctx.case.data["timeline"])}
