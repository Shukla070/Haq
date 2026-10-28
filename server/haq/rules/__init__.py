"""Rule packs: one JSON file per dispute type, written and checked by hand. A pack sets
the checklist, the rules that may be cited (each with its official source and the date it
was checked), and the escalation ladder. The model never invents any of these."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

PACKS_DIR = Path(__file__).resolve().parent


def available() -> dict:
    """Pack id → one-line description of when it applies."""
    packs = {}
    for path in sorted(PACKS_DIR.glob("*.json")):
        pack = json.loads(path.read_text(encoding="utf-8"))
        packs[pack["id"]] = pack["applies_when"]
    return packs


def load(pack_id: str) -> dict:
    path = PACKS_DIR / f"{pack_id}.json"
    if not path.is_file():
        raise KeyError(f"no rule pack {pack_id!r}; available: {', '.join(available())}")
    return json.loads(path.read_text(encoding="utf-8"))


def rule(pack: dict, rule_id: str) -> dict | None:
    return next((r for r in pack["rules"] if r["id"] == rule_id), None)


def entitlement(
    pack: dict,
    variant: str,
    transaction_date: date,
    today: date,
    reversed_on: date | None = None,
) -> dict:
    """Reversal deadline and compensation owed, computed in code so the model never does
    date arithmetic. T is the calendar date of the transaction; days count as calendar days."""
    if variant not in pack["variants"]:
        raise KeyError(f"variant must be one of {', '.join(pack['variants'])}")
    rules = pack["variants"][variant]
    due = transaction_date + timedelta(days=rules["reversal_days"])
    until = reversed_on or today
    days_late = max(0, (until - due).days)
    return {
        "variant": variant,
        "rule": rules["rule"],
        "transaction_date": transaction_date.isoformat(),
        "reversal_due_by": due.isoformat(),
        "reversed_on": reversed_on.isoformat() if reversed_on else None,
        "as_of": today.isoformat(),
        "days_late": days_late,
        "compensation_owed": days_late * pack["compensation_per_day"],
        "compensation_still_growing": reversed_on is None and days_late > 0,
        "note": "Calendar days assumed: the circular defines T as a calendar date.",
    }


def ladder_position(
    pack: dict,
    today: date,
    complained_on: date | None = None,
    bank_replied_on: date | None = None,
    satisfied: bool = False,
) -> dict:
    """Which escalation step is due, and the dates that govern it."""
    bank, ombudsman = pack["ladder"][0], pack["ladder"][1]
    if complained_on is None:
        return {
            "step": bank["id"],
            "reason": "The bank has not been complained to yet.",
            "bank_reply_due_if_sent_today": (today + timedelta(days=bank["wait_days"])).isoformat(),
        }
    if satisfied:
        return {"step": None, "reason": "The customer is satisfied with the bank's reply."}
    reply_due = complained_on + timedelta(days=bank["wait_days"])
    if bank_replied_on is None and today < reply_due:
        return {
            "step": "wait",
            "reason": "The bank still has time to reply.",
            "bank_reply_due_by": reply_due.isoformat(),
        }
    # 90 days from the end of the bank's reply period or its last communication, whichever is later.
    start = max(reply_due, bank_replied_on) if bank_replied_on else reply_due
    file_by = start + timedelta(days=ombudsman["filing_window_days"])
    return {
        "step": ombudsman["id"],
        "reason": "The bank replied unsatisfactorily."
        if bank_replied_on
        else "The bank did not reply within 30 days.",
        "file_ombudsman_by": file_by.isoformat(),
        "window_closed": today > file_by,
    }
