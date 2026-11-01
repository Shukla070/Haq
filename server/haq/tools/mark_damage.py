"""mark_damage: mark the damage in a customer's photo, on a copy that goes with the complaint."""

from __future__ import annotations

from .. import damage

DEFINITION = {
    "type": "function",
    "name": "mark_damage",
    "description": "For a damaged or defective item: mark the damage on a copy of the customer's photo, which goes with "
    "their complaint beside the original. Haq does this only when the damage sits on the product it finds in the photo. "
    "The mark is a pointer, not proof: it gives you nothing to quote, so the damage stays the customer's statement.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"evidence_id": {"type": "string", "description": "a photo of the damaged item"}},
        "required": ["evidence_id"],
    },
}


def run(ctx, args: dict) -> dict:
    item = damage.mark(ctx.case, ctx.client, str(args.get("evidence_id", "")))
    return {
        "marked": item["id"],
        "file": item["original_name"],
        "seen": item["visual_notes"],
        "note": "The complaint may say the attached photo marks the damage. Say nothing about it being checked or proven.",
    }
