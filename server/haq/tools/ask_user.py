"""ask_user: pause the case until the customer answers or adds evidence."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "ask_user",
    "description": "Ask the customer for something only they can provide (a missing screenshot, a date, whether they "
    "already complained). The run pauses until they answer. Ask at most two short things at once, the most "
    "decisive first; ask again later for the rest.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "question": {"type": "string", "description": "plain and friendly, under 50 words, no numbered lists"},
            "why": {"type": "string", "description": "which checklist item it settles"},
        },
        "required": ["question", "why"],
    },
}


MAX_LENGTH = 350  # about 50 words: one phone screen, read at a glance
MAX_QUESTIONS = 3


def run(ctx, args: dict) -> dict:
    text = str(args.get("question", ""))
    if len(text) > MAX_LENGTH or text.count("?") > MAX_QUESTIONS:
        return {
            "error": f"the question is too long for the customer to answer at once ({len(text)} characters, "
            f"{text.count('?')} question marks). Ask at most two short things, under 50 words, the most decisive first."
        }
    question = {"question": str(args.get("question", "")), "why": str(args.get("why", "")), "answer": None}
    ctx.case.data["questions"].append(question)
    ctx.case.data["status"] = "needs_input"
    ctx.case.log("asked_user", question=question["question"])
    return {"status": "needs_input", "asked": question["question"]}
