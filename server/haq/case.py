"""The case record: everything the agent has established about one dispute, saved as
JSON under <data_dir>/cases/<case_id>/. Code, not the model, enforces its rules:

- a fact is accepted only if its quote appears in the evidence it cites,
- the checklist comes from the rule pack, never from the model,
- what the user says without evidence is kept apart, as a user statement.
"""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from . import config

_SPACE = re.compile(r"\s+")
_QUOTES = str.maketrans(
    {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}
)
MIN_QUOTE = 6


class CaseError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize(text: str) -> str:
    return _SPACE.sub(" ", (text or "").translate(_QUOTES)).strip().lower()


def quote_in(quote: str, text: str) -> bool:
    q = normalize(quote)
    return len(q) >= MIN_QUOTE and q in normalize(text)


def cases_dir() -> Path:
    path = config.data_dir() / "cases"
    path.mkdir(parents=True, exist_ok=True)
    return path


class Case:
    def __init__(self, data: dict):
        self.data = data

    # ---- storage ------------------------------------------------------------

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def folder(self) -> Path:
        return cases_dir() / self.id

    @classmethod
    def create(cls, story: str) -> Case:
        case_id = "case-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)
        case = cls(
            {
                "id": case_id,
                "created": now(),
                "story": story.strip(),
                "status": "new",
                "dispute_type": None,
                "variant": None,
                "checklist": [],
                "evidence": [],
                "facts": [],
                "user_statements": [],
                "timeline": [],
                "entitlement": None,
                "escalation": None,
                "questions": [],
                "drafts": [],
                "referral": None,
                "audit": [],
            }
        )
        (case.folder / "evidence").mkdir(parents=True, exist_ok=True)
        case.save()
        return case

    @classmethod
    def load(cls, case_id: str) -> Case:
        path = cases_dir() / case_id / "case.json"
        if not path.is_file():
            raise CaseError(f"no case {case_id!r}")
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def save(self) -> None:
        path = self.folder / "case.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def log(self, event: str, **details) -> None:
        self.data["audit"].append({"at": now(), "event": event, **details})

    # ---- evidence -----------------------------------------------------------

    def evidence(self, evidence_id: str) -> dict:
        for item in self.data["evidence"]:
            if item["id"] == evidence_id:
                return item
        raise CaseError(f"no evidence {evidence_id!r}; known: {', '.join(e['id'] for e in self.data['evidence']) or 'none'}")

    def add_evidence(self, item: dict) -> dict:
        item = {"id": f"E{len(self.data['evidence']) + 1}", **item}
        self.data["evidence"].append(item)
        self.log("evidence_added", evidence_id=item["id"], kind=item.get("kind"))
        return item

    # ---- checklist and facts ------------------------------------------------

    def set_dispute(self, pack: dict, variant: str | None) -> None:
        self.data["dispute_type"] = pack["id"]
        self.data["variant"] = variant
        self.data["checklist"] = [
            {"id": c["id"], "question": c["question"], "settled_by": c["settled_by"]} for c in pack["checklist"]
        ]
        self.log("dispute_classified", dispute_type=pack["id"], variant=variant)

    def checklist_ids(self) -> list:
        return [item["id"] for item in self.data["checklist"]]

    def _require_item(self, item: str) -> None:
        if not self.data["checklist"]:
            raise CaseError("classify the dispute first: the checklist comes from its rule pack")
        if item not in self.checklist_ids():
            raise CaseError(f"unknown checklist item {item!r}; items: {', '.join(self.checklist_ids())}")

    def record_fact(self, item: str, evidence_id: str, quote: str, claim: str) -> dict:
        self._require_item(item)
        evidence = self.evidence(evidence_id)
        if not quote_in(quote, evidence.get("text", "")):
            self.log("fact_refused", item=item, evidence_id=evidence_id, quote=quote)
            raise CaseError(
                f"quote not found in {evidence_id}: copy it exactly from the evidence text (at least {MIN_QUOTE} characters)"
            )
        fact = {"id": f"F{len(self.data['facts']) + 1}", "item": item, "evidence_id": evidence_id, "quote": quote, "claim": claim}
        self.data["facts"].append(fact)
        self.log("fact_recorded", fact_id=fact["id"], item=item)
        return fact

    def record_user_statement(self, item: str, statement: str) -> dict:
        self._require_item(item)
        entry = {"id": f"U{len(self.data['user_statements']) + 1}", "item": item, "statement": statement}
        self.data["user_statements"].append(entry)
        self.log("user_statement_recorded", statement_id=entry["id"], item=item)
        return entry

    def coverage(self) -> dict:
        """Checklist item → how it is supported: proven (evidence), user_stated, or open."""
        result = {}
        for item in self.checklist_ids():
            if any(f["item"] == item for f in self.data["facts"]):
                result[item] = "proven"
            elif any(s["item"] == item for s in self.data["user_statements"]):
                result[item] = "user_stated"
            else:
                result[item] = "open"
        return result

    def summary(self) -> dict:
        """A compact view of the case for the model and the app."""
        return {
            "id": self.id,
            "status": self.data["status"],
            "dispute_type": self.data["dispute_type"],
            "variant": self.data["variant"],
            "coverage": self.coverage(),
            "facts": [{k: f[k] for k in ("id", "item", "evidence_id", "claim")} for f in self.data["facts"]],
            "user_statements": self.data["user_statements"],
            "timeline": sorted(self.data["timeline"], key=lambda e: e["date"]),
            "entitlement": self.data["entitlement"],
            "open_questions": [q for q in self.data["questions"] if not q.get("answer")],
            "drafts": len(self.data["drafts"]),
        }
