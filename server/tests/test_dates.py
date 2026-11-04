import unittest
from datetime import date

from haq import dates, evidence, tools, verify
from haq.case import Case

from support import GOOD_BODY, SAMPLE, Workspace

TODAY = date(2026, 11, 4)


class MentionedDatesTest(unittest.TestCase):
    def test_the_ways_people_and_banks_write_dates(self):
        for text in (
            "debited on 21-10-26",
            "Statement 21/10/2026",
            "2026-10-21",
            "On the night of 21 October I paid",
            "on 21st Oct",
            "Oct 21, 2026",
            "21 tarikh aktubar ko",
            "21 अक्टूबर को पैसे कटे",
        ):
            self.assertIn((10, 21), dates.mentioned(text, TODAY), text)

    def test_today_and_yesterday_count_as_the_dates_they_mean(self):
        self.assertIn((11, 4), dates.mentioned("I paid today at a shop", TODAY))
        self.assertIn((11, 3), dates.mentioned("kal raat payment kiya", TODAY))
        self.assertIn((11, 2), dates.mentioned("day before yesterday", TODAY))

    def test_a_story_without_a_date_mentions_none(self):
        self.assertEqual(set(), dates.mentioned("I sent 1000 at a shop but it was showing internet loss", TODAY))


class GuessedDateTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace(today="2026-11-04")
        self.case = Case.create("I sent 1000 at a shop but it was showing internet loss after payment.")
        self.case.data["dispute_type"] = "upi_failed_debit"
        self.ctx = tools.Context(case=self.case, client=None)

    def tearDown(self):
        self.workspace.close()

    def entitle(self, day: str) -> dict:
        args = '{"variant": "p2m", "transaction_date": "%s", "reversed_on": ""}' % day
        return tools.run(self.ctx, {"name": "calculate_entitlement", "arguments": args})

    def test_a_date_nobody_gave_is_refused(self):
        result = self.entitle("2026-11-04")
        self.assertIn("Do not guess dates", result["error"])
        self.assertIsNone(self.case.data["entitlement"])

    def test_a_date_the_customer_answers_with_is_used(self):
        self.case.data["questions"].append({"question": "When did you pay?", "why": "", "answer": "On 2nd November"})
        self.assertEqual(0, self.entitle("2026-11-02")["entitlement"]["compensation_owed"])


class ShortQuestionTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = Case.create("story")
        self.ctx = tools.Context(case=self.case, client=None)

    def tearDown(self):
        self.workspace.close()

    def ask(self, question: str) -> dict:
        import json

        return tools.run(self.ctx, {"name": "ask_user", "arguments": json.dumps({"question": question, "why": "date"})})

    def test_a_long_list_of_questions_is_refused(self):
        long = " ".join(f"{n}) Question number {n} about the payment?" for n in range(1, 8))
        self.assertIn("too long", self.ask(long)["error"])
        self.assertEqual([], self.case.data["questions"])

    def test_a_short_question_is_asked(self):
        self.assertEqual("needs_input", self.ask("On what date did you pay, and did the money leave your account?")["status"])


class InternalWordsTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.case = Case.create((SAMPLE / "story.txt").read_text(encoding="utf-8"))
        for name in ("bank_sms.txt", "upi_app_status.txt", "statement_extract.txt"):
            evidence.add(self.case, SAMPLE / name)

    def tearDown(self):
        self.workspace.close()

    def test_talk_of_haqs_tools_is_refused(self):
        problems = verify.internal_words(self.case, GOOD_BODY + " Plus Rs 100 per day, as the tools calculate.")
        self.assertTrue(any("'tools'" in p for p in problems))

    def test_a_word_from_the_customers_own_material_is_allowed(self):
        self.case.data["story"] += " I ordered a tool kit."
        self.assertEqual([], verify.internal_words(self.case, "The tool kit arrived broken."))
