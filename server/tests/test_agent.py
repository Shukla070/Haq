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


    def test_a_voice_note_is_never_proof(self):
        self.case.set_dispute(rules.load("upi_failed_debit"), "p2p")
        self.case.add_evidence({"kind": "voice", "text": "I sent four thousand five hundred rupees on UPI."})
        with self.assertRaisesRegex(CaseError, "record_user_statement"):
            self.case.record_fact("debit", "E4", "I sent four thousand five hundred rupees", "debited")


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


WAIT_PATH = HAPPY_PATH[:10] + [
    call("check_escalation", complained_on="2026-10-20", bank_replied_on="", satisfied=False),
    HAPPY_PATH[-1],
    call("hold_case", message="Your bank has until 19 Nov 2026 to reply. Rs 1,500 is owed so far."),
]


class WaitingTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = sample_case()

    def tearDown(self):
        self.workspace.close()

    def test_no_draft_while_the_bank_still_has_time_to_reply(self):
        fake = FakeClient(WAIT_PATH)
        result = agent.start(self.case, fake)
        self.assertEqual("waiting", result["status"])
        case = Case.load(self.case.id)
        self.assertEqual("2026-11-19", case.data["hold"]["until"])
        refused = case.data["drafts"][-1]
        self.assertFalse(refused["passed"])
        self.assertIn("call hold_case", refused["problems"][0])

    def test_hold_is_refused_when_a_complaint_is_due(self):
        hold = call("hold_case", message="Wait for the bank.")
        result = agent.start(self.case, FakeClient(HAPPY_PATH[:-1] + [hold, HAPPY_PATH[-1]]))
        self.assertEqual("draft_ready", result["status"])
        self.assertIsNone(Case.load(self.case.id).data["hold"])
        run = json.loads((self.case.folder / "run.json").read_text(encoding="utf-8"))
        self.assertIn("a complaint is due now", run["turns"][-2]["error"])

    def test_a_hold_message_with_a_made_up_amount_is_refused(self):
        bad = call("hold_case", message="Wait for the bank. You are owed Rs 9,999.")
        result = agent.start(self.case, FakeClient(WAIT_PATH[:-1] + [bad, WAIT_PATH[-1]]))
        self.assertEqual("waiting", result["status"])
        run = json.loads((self.case.folder / "run.json").read_text(encoding="utf-8"))
        self.assertIn("9999", run["turns"][-2]["error"])

    def test_a_resumed_run_clears_the_hold(self):
        fake = FakeClient(WAIT_PATH)
        agent.start(self.case, fake)
        fake.script = [call("ask_user", question="Has the bank replied?", why="complaint_history")]
        result = agent.resume(Case.load(self.case.id), fake, "The customer answered: no reply yet")
        self.assertEqual("needs_input", result["status"])
        self.assertIsNone(Case.load(self.case.id).data["hold"])


class TimingTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = sample_case()

    def tearDown(self):
        self.workspace.close()

    def test_each_turn_and_the_run_are_timed(self):
        result = agent.start(self.case, FakeClient(["thinking", *HAPPY_PATH]))
        self.assertIn("seconds", result)
        run = json.loads((self.case.folder / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(all("model_seconds" in turn for turn in run["turns"]))
        self.assertTrue(all("tool_seconds" in turn for turn in run["turns"] if turn["tool"]))
        self.assertEqual(result["seconds"], run["seconds"])


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

    def test_an_amount_quoted_without_a_currency_sign_is_allowed(self):
        self.case.record_fact("not_reversed", "E3", "Closing balance as on 27-10-2026: 22,004.50", "balance")
        self.draft["body"] = GOOD_BODY + " My closing balance on 27 October was Rs 22,004.50."
        self.assertEqual([], verify.check(self.case, self.draft))

    def test_an_amount_spoken_as_words_is_allowed(self):
        self.case.add_evidence({"kind": "voice", "text": "Bank ne bola tha do hazaar teen sau wapas aayenge."})
        self.draft["body"] = GOOD_BODY + " The bank told me Rs 2,300 would be returned."
        self.assertEqual([], verify.check(self.case, self.draft))

    def test_an_amount_only_in_the_agents_paraphrase_is_refused(self):
        self.case.record_user_statement("not_reversed", "The bank promised Rs 7,000.")
        self.draft["body"] = GOOD_BODY + " The bank promised me Rs 7,000."
        self.assertTrue(any("7000" in p for p in verify.check(self.case, self.draft)))

    def test_an_amount_in_the_customers_answer_is_allowed(self):
        self.case.data["questions"].append({"question": "How much?", "why": "debit", "answer": "Rs 7,000"})
        self.draft["body"] = GOOD_BODY + " The bank promised me Rs 7,000."
        self.assertEqual([], verify.check(self.case, self.draft))

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
