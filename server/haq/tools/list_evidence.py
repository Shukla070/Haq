"""list_evidence: what the customer has shared so far."""

from __future__ import annotations

DEFINITION = {
    "type": "function",
    "name": "list_evidence",
    "description": "List the evidence the customer has shared: id, kind, file name, the customer's note, and a short preview.",
    "parameters": {"type": "object", "additionalProperties": False, "properties": {}},
}


def run(ctx, args: dict) -> dict:
    return {
        "evidence": [
            {
                "id": e["id"],
                "kind": e["kind"],
                "file": e["original_name"],
                "note": e["note"],
                "preview": e["text"][:160],
            }
            for e in ctx.case.data["evidence"]
        ]
    }
