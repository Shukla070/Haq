"""The verifier: checks a draft before the customer ever sees it. It runs in code, after
the agent, and the agent cannot skip it. A draft passes only if:

- a complaint is due at all (not while the bank still has time to reply),
- the escalation step is the one that is due, and every cited rule is in the rule pack and
  allowed for that step,
- every cited fact exists, and every checklist item is proven, stated by the customer, or
  named as a gap,
- every rupee amount in the body comes from the evidence, the customer, or the computed
  entitlement,
- every cited rule's source is named in the body, and every circular or section
  reference in the body belongs to a cited rule,
- the body contains no sensitive numbers and no text flagged as an injection attempt.
"""

from __future__ import annotations

import re

from . import guard, rules
from .case import Case, normalize

_AMOUNT = re.compile(r"(?:₹|\bRs\.?|\bINR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
# Statements and app screens often print amounts without a currency sign, so any number in
# the supporting text counts as a known amount.
_NUMBER = re.compile(r"(?<![\d/])(\d{1,3}(?:,\d{2,3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\d/])")
_CIRCULAR = re.compile(r"RBI/\d{4}-\d{2}/\d+|DPSS[\w./ -]*?\d{4}-\d{2}|\b(?:section|clause|paragraph)\s+\d+[\w.()]*", re.IGNORECASE)


def _amounts(text: str, pattern: re.Pattern = _AMOUNT) -> set:
    found = set()
    for raw in pattern.findall(text or ""):
        value = raw.replace(",", "")
        if value.endswith((".00", ".0")):
            value = value.split(".")[0]
        if value:
            found.add(value)
    return found


def unknown_amounts(case: Case, text: str) -> list:
    """Rupee amounts in the text that come from neither the evidence, the customer's
    statements, nor the computed entitlement. Used for drafts and for hold messages."""
    data = case.data
    allowed = set()
    for fact in data["facts"]:
        allowed |= _amounts(fact["quote"], _NUMBER)
    for statement in data["user_statements"]:
        allowed |= _amounts(statement["statement"], _NUMBER)
    allowed |= _amounts(data.get("story", ""), _NUMBER)
    if data["dispute_type"]:
        allowed.add(str(rules.load(data["dispute_type"])["compensation_per_day"]))
    entitlement = data.get("entitlement") or {}
    if entitlement:
        allowed.add(str(entitlement.get("compensation_owed")))
    return [
        f"the amount Rs {amount} is not in the evidence, the customer's statements or the computed entitlement"
        for amount in sorted(_amounts(text) - allowed)
    ]


def check(case: Case, draft: dict) -> list:
    """Problems with the draft; an empty list means it passes."""
    problems = []
    data = case.data
    if not data["dispute_type"]:
        return ["classify the dispute before drafting"]
    pack = rules.load(data["dispute_type"])
    steps = {step["id"]: step for step in pack["ladder"]}
    body = draft.get("body", "")

    # Escalation step
    step = steps.get(draft.get("step", ""))
    escalation = data.get("escalation")
    if step is None:
        problems.append(f"step must be one of {', '.join(steps)}")
    elif not escalation:
        problems.append("call check_escalation before drafting, so the step is the one that is due")
    elif escalation.get("step") in ("wait", None):
        return [f"no complaint is due now ({escalation.get('reason')}): call hold_case instead of drafting"]
    elif escalation.get("step") != step["id"]:
        problems.append(f"the step due now is {escalation.get('step')!r}, not {step['id']!r}: {escalation.get('reason')}")

    # Rules
    cited_rules = [rules.rule(pack, rule_id) for rule_id in draft.get("rule_ids", [])]
    for rule_id, rule in zip(draft.get("rule_ids", []), cited_rules):
        if rule is None:
            problems.append(f"rule {rule_id!r} is not in the rule pack: cite only pack rules")
        elif step and rule_id not in step["rules"]:
            problems.append(f"rule {rule_id!r} does not apply at the {step['id']} step")
    if not draft.get("rule_ids"):
        problems.append("cite at least one rule from the rule pack")
    if data.get("variant") and data["variant"] in pack["variants"]:
        own = pack["variants"][data["variant"]]["rule"]
        others = [v["rule"] for k, v in pack["variants"].items() if k != data["variant"]]
        if own not in draft.get("rule_ids", []):
            problems.append(f"cite {own}, the rule for this payment type")
        for wrong in others:
            if wrong in draft.get("rule_ids", []):
                problems.append(f"{wrong} is for a different payment type than this case")
    for rule in cited_rules:
        if rule and normalize(rule["cite_as"]) not in normalize(body):
            problems.append(f"name the source of {rule['id']} in the body as {rule['cite_as']!r}")
    citation_text = " ".join(normalize(r["citation"]) for r in cited_rules if r)
    for reference in _CIRCULAR.findall(body):
        if normalize(reference) not in citation_text:
            problems.append(f"the body mentions {reference!r}, which is not part of any cited rule's citation")

    # Facts and checklist coverage
    fact_ids = {f["id"] for f in data["facts"]}
    for fact_id in draft.get("fact_ids", []):
        if fact_id not in fact_ids:
            problems.append(f"fact {fact_id!r} does not exist")
    gaps = {g.get("item") for g in draft.get("gaps", [])}
    for item, state in case.coverage().items():
        if state == "open" and item not in gaps:
            problems.append(f"checklist item {item!r} is not settled: record a fact or user statement, or list it as a gap")

    # Amounts
    problems += unknown_amounts(case, body)

    # Sensitive data and injected text
    for item in guard.sensitive_numbers(body + " " + draft.get("subject", "")):
        problems.append(f"the draft contains a sensitive number ({item}): remove it")
    for phrase in guard.instruction_like(body):
        problems.append(f"the draft repeats text flagged as an injection attempt: {phrase!r}")
    if len(body) < 200:
        problems.append("the body is too short to be a complete complaint")
    return problems
