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
        self.assertEqual("2026-11-27", result["bank_reply_due_if_sent_today"])

    def test_the_bank_gets_30_days_to_reply(self):
        result = rules.ladder_position(PACK, date(2026, 10, 28), complained_on=date(2026, 10, 20))
        self.assertEqual("wait", result["step"])
        self.assertEqual("2026-11-19", result["bank_reply_due_by"])

    def test_no_reply_after_30_days_opens_the_ombudsman_for_90_days(self):
        result = rules.ladder_position(PACK, date(2026, 11, 25), complained_on=date(2026, 10, 20))
        self.assertEqual("ombudsman", result["step"])
        self.assertEqual("2027-02-17", result["file_ombudsman_by"])

    def test_an_early_rejection_counts_from_the_later_date(self):
        result = rules.ladder_position(
            PACK, date(2026, 10, 28), complained_on=date(2026, 10, 20), bank_replied_on=date(2026, 10, 25)
        )
        self.assertEqual("ombudsman", result["step"])
        self.assertEqual("2027-02-17", result["file_ombudsman_by"])

    def test_every_citable_rule_has_a_source_and_a_check_date(self):
        for rule in PACK["rules"]:
            self.assertTrue(rule["source"].startswith("https://www.rbi.org.in/"), rule["id"])
            self.assertTrue(rule["verified_on"], rule["id"])


if __name__ == "__main__":
    unittest.main()
