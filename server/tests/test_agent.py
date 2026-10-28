import json
import unittest

from haq import agent, evidence, rules, verify
from haq.case import Case, CaseError

from support import GOOD_BODY, HAPPY_PATH, SAMPLE, FakeClient, Workspace, call


def sample_case() -> Case:
    case = Case.create((SAMPLE / "story.txt").read_text(encoding="utf-8"))
    for name in ("bank_sms.txt", "upi_app_status.txt", "statement_extract.txt"):
        evidence.add(case, SAMPLE / name)
    return case


class CaseRecordTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = sample_case()

    def tearDown(self):
        self.workspace.close()

    def test_sensitive_numbers_are_masked_on_the_way_in(self):
        statement = self.case.evidence("E3")
        self.assertTrue(statement["masked"])
        self.assertNotIn("4111 1111 1111 1111", statement["text"])
        self.assertIn("628512347765", statement["text"])

    def test_facts_need_a_checklist_from_a_rule_pack(self):
        with self.assertRaises(CaseError):
            self.case.record_fact("debit", "E1", "Rs.4,500.00 debited", "debited")

    def test_a_quote_not_in_the_evidence_is_refused(self):
        self.case.set_dispute(rules.load("upi_failed_debit"), "p2p")
        with self.assertRaisesRegex(CaseError, "quote not found"):
            self.case.record_fact("failure", "E2", "Ramesh received the money", "made up")
        self.assertEqual([], self.case.data["facts"])


class AgentLoopTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = sample_case()

    def tearDown(self):
        self.workspace.close()

    def test_the_happy_path_ends_with_a_verified_draft(self):
        fake = FakeClient(HAPPY_PATH)
        result = agent.start(self.case, fake)
        self.assertEqual("draft_ready", result["status"], json.dumps(Case.load(self.case.id).data["drafts"], indent=1))
        case = Case.load(self.case.id)
        self.assertEqual(1500, case.data["entitlement"]["compensation_owed"])
        self.assertTrue(case.data["drafts"][-1]["passed"])

    def test_plain_text_gets_a_nudge_and_the_run_continues(self):
        fake = FakeClient(["I think the bank owes money.", *HAPPY_PATH])
        result = agent.start(self.case, fake)
        self.assertEqual("draft_ready", result["status"])
        self.assertEqual(agent.NUDGE, fake.requests[1]["input"][-1]["content"])

    def test_asking_the_customer_pauses_until_they_answer(self):
        fake = FakeClient([call("ask_user", question="When did you pay?", why="debit")])
        result = agent.start(self.case, fake)
        self.assertEqual("needs_input", result["status"])
        fake.script = list(HAPPY_PATH)
        resumed = agent.resume(Case.load(self.case.id), fake, "The customer answered: 12 October")
        self.assertEqual("draft_ready", resumed["status"])

    def test_an_api_failure_pauses_the_run(self):
        fake = FakeClient([call("list_evidence"), RuntimeError("service_overloaded")])
        result = agent.start(self.case, fake)
        self.assertEqual("paused", result["status"])
        self.assertIn("service_overloaded", result["note"])

    def test_the_last_turn_asks_for_the_draft(self):
        fake = FakeClient(HAPPY_PATH[:3])
        result = agent.start(self.case, fake, turns=3)
        self.assertEqual("paused", result["status"])
        self.assertEqual(agent.LAST_TURN, fake.requests[-1]["input"][-1]["content"])


class VerifierTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = sample_case()
        agent.start(self.case, FakeClient(HAPPY_PATH[:-1] + ["stop"]), turns=len(HAPPY_PATH))
        self.case = Case.load(self.case.id)
        self.draft = dict(json.loads(json.dumps(HAPPY_PATH[-1]["arguments"])))

    def tearDown(self):
        self.workspace.close()

    def test_the_good_draft_passes(self):
        self.assertEqual([], verify.check(self.case, self.draft))

    def test_a_rule_outside_the_pack_is_refused(self):
        self.draft["rule_ids"].append("CONSUMER-PROTECTION-ACT-S35")
        self.assertTrue(any("not in the rule pack" in p for p in verify.check(self.case, self.draft)))

    def test_a_made_up_amount_is_refused(self):
        self.draft["body"] = GOOD_BODY.replace("Rs 1,500", "Rs 25,000")
        self.assertTrue(any("25000" in p for p in verify.check(self.case, self.draft)))

    def test_a_citation_from_memory_is_refused(self):
        self.draft["body"] = GOOD_BODY + " This also breaches Section 72 of the Payment Act."
        self.assertTrue(any("Section 72" in p for p in verify.check(self.case, self.draft)))

    def test_a_cited_rule_must_be_named_in_the_body(self):
        self.draft["body"] = GOOD_BODY.replace("RBI circular RBI/2019-20/67", "the RBI rule")
        self.assertTrue(any("name the source" in p for p in verify.check(self.case, self.draft)))

    def test_skipping_ahead_to_the_ombudsman_is_refused(self):
        self.draft["step"] = "ombudsman"
        self.assertTrue(any("step due now" in p for p in verify.check(self.case, self.draft)))

    def test_the_wrong_payment_type_rule_is_refused(self):
        self.draft["rule_ids"] = ["RBI-TAT-UPI-P2M"]
        problems = verify.check(self.case, self.draft)
        self.assertTrue(any("cite RBI-TAT-UPI-P2P" in p for p in problems))

    def test_a_card_number_in_the_body_is_refused(self):
        self.draft["body"] = GOOD_BODY + " My card is 4111 1111 1111 1111."
        self.assertTrue(any("sensitive number" in p for p in verify.check(self.case, self.draft)))


if __name__ == "__main__":
    unittest.main()
