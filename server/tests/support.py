"""Test helpers: a temporary data folder, a pinned date, and a fake model client that
replays scripted tool calls instead of calling the API."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "upi-failed-debit"


class Workspace:
    """Points HAQ_DATA_DIR at a fresh temp folder and pins today's date."""

    def __init__(self, today: str = "2026-10-28"):
        self._folder = tempfile.TemporaryDirectory()
        self._saved = {key: os.environ.get(key) for key in ("HAQ_DATA_DIR", "HAQ_TODAY")}
        os.environ["HAQ_DATA_DIR"] = self._folder.name
        os.environ["HAQ_TODAY"] = today

    def close(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._folder.cleanup()


def call(name: str, **arguments) -> dict:
    return {"name": name, "arguments": arguments}


class FakeClient:
    """Answers each agent request with the next scripted step: a tool call (dict), plain
    text (str), or an exception to raise. Records every request."""

    def __init__(self, script: list):
        self.script = list(script)
        self.requests: list = []
        self.responses = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs)))  # a snapshot: the loop keeps appending to input
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        usage = SimpleNamespace(total_tokens=10)
        if isinstance(step, str):
            return SimpleNamespace(output=[{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": step}]}], usage=usage)
        item = {
            "type": "function_call",
            "name": step["name"],
            "arguments": json.dumps(step["arguments"]),
            "call_id": f"call_{len(self.requests)}",
        }
        return SimpleNamespace(output=[item], usage=usage)


GOOD_BODY = (
    "Dear Sir or Madam,\n\nOn 12 October 2026 my Kaveri Bank account XX4821 was debited Rs 4,500 for a UPI "
    "transfer to Ramesh Kumar (UPI Ref No 628512347765). The transaction failed and the beneficiary was not "
    "credited, but the amount has not been reversed. Under RBI circular RBI/2019-20/67 the amount should have "
    "been auto-reversed by T + 1 day, and compensation of Rs 100 per day is payable for the delay. As of today "
    "the compensation owed is Rs 1,500. Please reverse Rs 4,500 and credit the compensation within 7 days.\n\n"
    "Yours faithfully"
)

HAPPY_PATH = [
    call("list_evidence"),
    call("read_evidence", evidence_ids=["E1", "E2", "E3"]),
    call("classify_dispute", dispute_type="upi_failed_debit", variant="p2p", reason="transfer to a person failed"),
    call("record_fact", item="debit", evidence_id="E1", quote="Rs.4,500.00 debited from A/c XX4821 on 12-10-26", claim="debited"),
    call("record_fact", item="failure", evidence_id="E2", quote="Transaction failed", claim="failed"),
    call("record_fact", item="payment_type", evidence_id="E2", quote="To: Ramesh Kumar", claim="a person"),
    call("record_fact", item="reference", evidence_id="E1", quote="UPI Ref No 628512347765", claim="reference"),
    call("record_user_statement", item="not_reversed", statement="It is still not back in my account."),
    call("record_user_statement", item="complaint_history", statement="I have not complained to the bank yet"),
    call("calculate_entitlement", variant="p2p", transaction_date="2026-10-12", reversed_on=""),
    call("check_escalation", complained_on="", bank_replied_on="", satisfied=False),
    call(
        "submit_draft",
        step="bank",
        recipient="Kaveri Bank grievance cell",
        subject="Failed UPI transfer not reversed - UPI Ref 628512347765",
        body=GOOD_BODY,
        fact_ids=["F1", "F2", "F3", "F4"],
        rule_ids=["RBI-TAT-UPI-P2P", "RBI-TAT-SUO-MOTO"],
        gaps=[],
        next_steps="Send it today; if there is no reply by 2026-11-27, escalate to the RBI Ombudsman.",
    ),
]
