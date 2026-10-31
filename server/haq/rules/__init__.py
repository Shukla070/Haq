"""Rule packs: one JSON file per dispute type, written and checked by hand. A pack sets
the checklist, the rules that may be cited (each with its official source and the date it
was checked), and the escalation ladder. The model never invents any of these."""

from __future__ import annotations

import json
from calendar import monthrange
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


def _add_months(day: date, months: int) -> date:
    """The same day of the month, or the month's last day if it is shorter (31 Oct → 30 Nov)."""
    index = day.year * 12 + day.month - 1 + months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def _reply_due(step: dict, sent_on: date) -> date:
    if "wait_months" in step:
        return _add_months(sent_on, step["wait_months"])
    return sent_on + timedelta(days=step["wait_days"])


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
    if "compensation_per_day" not in pack:
        file_by = _add_months(transaction_date, pack["commission_limit_months"])
        return {
            "variant": variant,
            "rule": rules["rule"],
            "transaction_date": transaction_date.isoformat(),
            "refunded_on": reversed_on.isoformat() if reversed_on else None,
            "as_of": today.isoformat(),
            "compensation_owed": 0,
            "consumer_commission_file_by": file_by.isoformat(),
            "consumer_commission_window_closed": today > file_by,
            "note": "No rule sets a daily compensation or a fixed refund date here: ask for the refund and name no "
            "compensation figure. The two-year limit is counted from the order date, the earliest it could start.",
        }
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
    replied_on: date | None = None,
    satisfied: bool = False,
) -> dict:
    """Which escalation step is due, and the dates that govern it."""
    first, second = pack["ladder"][0], pack["ladder"][1]
    party = pack["party"].capitalize()
    if complained_on is None:
        return {
            "step": first["id"],
            "reason": f"{party} has not been complained to yet.",
            "reply_due_if_sent_today": _reply_due(first, today).isoformat(),
        }
    if satisfied:
        return {"step": None, "reason": f"The customer is satisfied with the reply from {pack['party']}."}
    reply_due = _reply_due(first, complained_on)
    if replied_on is None and today < reply_due:
        return {
            "step": "wait",
            "reason": f"{party} still has time to reply.",
            "reply_due_by": reply_due.isoformat(),
        }
    position = {
        "step": second["id"],
        "reason": f"{party} replied unsatisfactorily." if replied_on else f"{party} did not reply in time.",
    }
    if "filing_window_days" in second:
        # Counted from the end of the reply period or the last communication, whichever is later.
        start = max(reply_due, replied_on) if replied_on else reply_due
        file_by = start + timedelta(days=second["filing_window_days"])
        position.update(file_by=file_by.isoformat(), window_closed=today > file_by)
    return position
