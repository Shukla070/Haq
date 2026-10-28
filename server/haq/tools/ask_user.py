"""ask_user: pause the case until the customer answers or adds evidence."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "ask_user",
    "description": "Ask the customer for something only they can provide (a missing screenshot, a date, whether they "
    "already complained). The run pauses until they answer. Ask everything you need in one question.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question": {"type": "string", "description": "plain, friendly, one message"},
            "why": {"type": "string", "description": "which checklist item it settles"},
        },
        "required": ["question", "why"],
    },
}


def run(ctx, args: dict) -> dict:
    question = {"question": str(args.get("question", "")), "why": str(args.get("why", "")), "answer": None}
    ctx.case.data["questions"].append(question)
    ctx.case.data["status"] = "needs_input"
    ctx.case.log("asked_user", question=question["question"])
    return {"status": "needs_input", "asked": question["question"]}
