import unittest
from datetime import date

from haq import rules

PACK = rules.load("upi_failed_debit")


class EntitlementTest(unittest.TestCase):
    def test_p2p_is_due_next_day_and_owes_100_per_day_after(self):
        result = rules.entitlement(PACK, "p2p", date(2026, 10, 12), date(2026, 10, 28))
        self.assertEqual("2026-10-13", result["reversal_due_by"])
        self.assertEqual(15, result["days_late"])
        self.assertEqual(1500, result["compensation_owed"])
        self.assertTrue(result["compensation_still_growing"])

    def test_p2m_allows_five_days(self):
        result = rules.entitlement(PACK, "p2m", date(2026, 10, 12), date(2026, 10, 16))
        self.assertEqual("2026-10-17", result["reversal_due_by"])
        self.assertEqual(0, result["compensation_owed"])

    def test_a_late_reversal_stops_the_count(self):
        result = rules.entitlement(PACK, "p2p", date(2026, 10, 12), date(2026, 10, 28), date(2026, 10, 16))
        self.assertEqual(300, result["compensation_owed"])
        self.assertFalse(result["compensation_still_growing"])


class LadderTest(unittest.TestCase):
    def test_no_complaint_means_the_bank_comes_first(self):
        result = rules.ladder_position(PACK, date(2026, 10, 28))
        self.assertEqual("bank", result["step"])
        self.assertEqual("2026-11-27", result["reply_due_if_sent_today"])

    def test_the_bank_gets_30_days_to_reply(self):
        result = rules.ladder_position(PACK, date(2026, 10, 28), complained_on=date(2026, 10, 20))
        self.assertEqual("wait", result["step"])
        self.assertEqual("2026-11-19", result["reply_due_by"])

    def test_no_reply_after_30_days_opens_the_ombudsman_for_90_days(self):
        result = rules.ladder_position(PACK, date(2026, 11, 25), complained_on=date(2026, 10, 20))
        self.assertEqual("ombudsman", result["step"])
        self.assertEqual("2027-02-17", result["file_by"])

    def test_an_early_rejection_counts_from_the_later_date(self):
        result = rules.ladder_position(
            PACK, date(2026, 10, 28), complained_on=date(2026, 10, 20), replied_on=date(2026, 10, 25)
        )
        self.assertEqual("ombudsman", result["step"])
        self.assertEqual("2027-02-17", result["file_by"])

    def test_every_citable_rule_has_a_source_and_a_check_date(self):
        for rule in PACK["rules"]:
            self.assertTrue(rule["source"].startswith("https://www.rbi.org.in/"), rule["id"])
            self.assertTrue(rule["verified_on"], rule["id"])


class EcommerceTest(unittest.TestCase):
    PACK = rules.load("ecommerce_refund")

    def test_no_compensation_is_computed_and_the_two_years_run_from_the_order(self):
        result = rules.entitlement(self.PACK, "marketplace", date(2026, 9, 28), date(2026, 11, 1))
        self.assertEqual(0, result["compensation_owed"])
        self.assertEqual("ECOM-REFUND-MARKETPLACE", result["rule"])
        self.assertEqual("2028-09-28", result["consumer_commission_file_by"])
        self.assertFalse(result["consumer_commission_window_closed"])

    def test_the_company_comes_first_and_gets_one_calendar_month(self):
        result = rules.ladder_position(self.PACK, date(2026, 10, 31))
        self.assertEqual("company", result["step"])
        self.assertEqual("2026-11-30", result["reply_due_if_sent_today"])

    def test_the_company_still_has_time(self):
        result = rules.ladder_position(self.PACK, date(2026, 11, 1), complained_on=date(2026, 10, 15))
        self.assertEqual("wait", result["step"])
        self.assertEqual("2026-11-15", result["reply_due_by"])

    def test_no_reply_in_a_month_opens_the_helpline(self):
        result = rules.ladder_position(self.PACK, date(2026, 11, 1), complained_on=date(2026, 9, 20))
        self.assertEqual("helpline", result["step"])
        self.assertNotIn("file_by", result)

    def test_a_refusal_opens_the_helpline_at_once(self):
        result = rules.ladder_position(self.PACK, date(2026, 11, 1), complained_on=date(2026, 10, 25), replied_on=date(2026, 10, 28))
        self.assertEqual("helpline", result["step"])

    def test_every_rule_has_a_government_source_a_check_date_and_a_step(self):
        steps = {rule_id for step in self.PACK["ladder"] for rule_id in step["rules"]}
        for rule in self.PACK["rules"]:
            self.assertRegex(rule["source"], r"^https://[\w.-]+\.(gov|nic)\.in/", rule["id"])
            self.assertTrue(rule["verified_on"], rule["id"])
            self.assertIn(rule["id"], steps)
            self.assertIn(rule["cite_as"].split(" of the ")[0].lower(), rule["citation"].lower(), rule["id"])


if __name__ == "__main__":
    unittest.main()
