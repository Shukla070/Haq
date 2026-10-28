"""refer_out: the case is outside what Haq handles; tell the customer where to go."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "refer_out",
    "description": "End the case when it is outside every rule pack or must go elsewhere: fraud or scams (1930 and "
    "cybercrime.gov.in), criminal or family matters, or claims past their time limit (free legal aid: NALSA, 15100).",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "reason": {"type": "string"},
            "where": {"type": "string", "description": "where the customer should go instead, and how"},
        },
        "required": ["reason", "where"],
    },
}


def run(ctx, args: dict) -> dict:
    referral = {"reason": str(args.get("reason", "")), "where": str(args.get("where", ""))}
    ctx.case.data["referral"] = referral
    ctx.case.data["status"] = "referred"
    ctx.case.log("referred", **referral)
    return {"status": "referred", "referral": referral}
