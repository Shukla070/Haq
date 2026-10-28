"""check_escalation: which step of the ladder is due now, computed in code."""

from __future__ import annotations

from datetime import date

from .. import config, rules

DEFINITION = {
    "type": "function",
    "name": "check_escalation",
    "description": "Work out which escalation step is due today from the complaint history: complain to the bank, "
    "wait for its reply, or go to the Ombudsman (with the filing deadline). Call it before drafting.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "complained_on": {"type": "string", "description": "YYYY-MM-DD the customer complained to the bank, else empty"},
            "bank_replied_on": {"type": "string", "description": "YYYY-MM-DD of the bank's last reply, else empty"},
            "satisfied": {"type": "boolean", "description": "true only if the customer accepts the bank's reply"},
        },
        "required": ["complained_on", "bank_replied_on", "satisfied"],
    },
}


def _date(value) -> date | None:
    return date.fromisoformat(str(value)) if value else None


def run(ctx, args: dict) -> dict:
    if not ctx.case.data["dispute_type"]:
        return {"error": "classify the dispute first"}
    pack = rules.load(ctx.case.data["dispute_type"])
    result = rules.ladder_position(
        pack,
        config.today(),
        _date(args.get("complained_on")),
        _date(args.get("bank_replied_on")),
        bool(args.get("satisfied")),
    )
    result["as_of"] = config.today().isoformat()
    ctx.case.data["escalation"] = result
    return {"escalation": result}
