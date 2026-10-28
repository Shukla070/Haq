"""calculate_entitlement: the reversal deadline and compensation owed, computed in code."""

from __future__ import annotations

from datetime import date

from .. import config, rules

DEFINITION = {
    "type": "function",
    "name": "calculate_entitlement",
    "description": "Compute the reversal deadline and the compensation owed under the rule pack. "
    "Never do this date or money arithmetic yourself: use this tool and quote its numbers.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "variant": {"type": "string", "description": "p2p or p2m"},
            "transaction_date": {"type": "string", "description": "YYYY-MM-DD, the day of the transaction"},
            "reversed_on": {"type": "string", "description": "YYYY-MM-DD if the money came back, else empty"},
        },
        "required": ["variant", "transaction_date", "reversed_on"],
    },
}


def run(ctx, args: dict) -> dict:
    if not ctx.case.data["dispute_type"]:
        return {"error": "classify the dispute first"}
    pack = rules.load(ctx.case.data["dispute_type"])
    variant = str(args.get("variant", ""))
    reversed_on = str(args.get("reversed_on") or "")
    result = rules.entitlement(
        pack,
        variant,
        date.fromisoformat(str(args.get("transaction_date", ""))),
        config.today(),
        date.fromisoformat(reversed_on) if reversed_on else None,
    )
    ctx.case.data["variant"] = variant
    ctx.case.data["entitlement"] = result
    return {"entitlement": result}
