"""hold_case: end the run without a draft when check_escalation says nothing is due yet."""

from __future__ import annotations

from .. import guard
from ..case import now
from ..verify import unknown_amounts

DEFINITION = {
    "type": "function",
    "name": "hold_case",
    "description": "End the run without a complaint when check_escalation says none is due: the bank still has time "
    "to reply (the case waits until its reply deadline), or the customer is satisfied (the case is resolved). "
    "Use it only after check_escalation; if a step is due, draft it with submit_draft instead.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "message": {
                "type": "string",
                "description": "for the customer, plain and short: where the case stands, what they are owed so far, "
                "and what to do if the bank has not fixed it by the date",
            },
        },
        "required": ["message"],
    },
}


def run(ctx, args: dict) -> dict:
    escalation = ctx.case.data.get("escalation")
    if not escalation:
        return {"error": "call check_escalation first"}
    step = escalation.get("step")
    if step == "wait":
        hold = {"status": "waiting", "until": escalation["bank_reply_due_by"], "then": "check again with check_escalation"}
    elif step is None:
        hold = {"status": "resolved", "until": None, "then": None}
    else:
        return {"error": f"a complaint is due now at the {step!r} step: draft it with submit_draft"}
    message = str(args.get("message", ""))
    # The customer reads this message as it is, so it gets the draft's checks on amounts and sensitive numbers.
    problems = unknown_amounts(ctx.case, message)
    problems += [f"the message contains a sensitive number ({item}): remove it" for item in guard.sensitive_numbers(message)]
    if problems:
        return {"error": "; ".join(problems)}
    hold.update(reason=escalation.get("reason"), message=message, set=now())
    ctx.case.data["hold"] = hold
    ctx.case.data["status"] = hold["status"]
    ctx.case.log("held", status=hold["status"], until=hold["until"])
    return {"status": hold["status"], "until": hold["until"]}
