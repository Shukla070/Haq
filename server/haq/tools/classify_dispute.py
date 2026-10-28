"""classify_dispute: pick the rule pack, which sets the checklist, the citable rules and the
escalation ladder."""

from __future__ import annotations

from .. import rules

DEFINITION = {
    "type": "function",
    "name": "classify_dispute",
    "description": "Classify the dispute and load its rule pack. Returns the checklist you must settle, "
    "the only rules you may cite, and the escalation ladder. Call it once you understand what happened. "
    "If no rule pack fits, use refer_out instead.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dispute_type": {"type": "string", "enum": sorted(rules.available())},
            "variant": {
                "type": "string",
                "description": "for upi_failed_debit: p2p (transfer to a person) or p2m (payment to a merchant); "
                "use unknown if the evidence does not show it yet",
            },
            "reason": {"type": "string", "description": "one sentence: why this pack fits"},
        },
        "required": ["dispute_type", "variant", "reason"],
    },
}


def run(ctx, args: dict) -> dict:
    pack = rules.load(str(args.get("dispute_type", "")))
    variant = str(args.get("variant") or "unknown")
    if variant != "unknown" and variant not in pack["variants"]:
        return {"error": f"variant must be one of {', '.join(pack['variants'])} or unknown"}
    ctx.case.set_dispute(pack, None if variant == "unknown" else variant)
    return {
        "dispute_type": pack["id"],
        "variant": ctx.case.data["variant"],
        "variants": {k: v["label"] for k, v in pack["variants"].items()},
        "checklist": ctx.case.data["checklist"],
        "rules": [{"id": r["id"], "citation": r["citation"], "cite_as": r["cite_as"], "says": r["says"]} for r in pack["rules"]],
        "ladder": pack["ladder"],
        "out_of_scope": pack["out_of_scope"],
    }
