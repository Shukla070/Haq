import os
import time
import unittest
import unittest.mock

from fastapi.testclient import TestClient

from haq import agent, api, config, evidence, limits, rules
from haq.__main__ import purge
from haq.case import Case

from support import HAPPY_PATH, SAMPLE, FakeClient, Workspace

ME = {"X-Haq-Device": "a" * 40}
SOMEONE_ELSE = {"X-Haq-Device": "b" * 40}
STORY = {"story": "My UPI payment failed but the money was cut."}


class DeviceTokenTest(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.workspace.close()

    def test_a_case_needs_a_device_token(self):
        self.assertEqual(401, self.client.post("/cases", json=STORY).status_code)
        self.assertEqual(401, self.client.post("/cases", json=STORY, headers={"X-Haq-Device": "short"}).status_code)

    def test_only_the_install_that_made_a_case_can_see_it(self):
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        self.assertEqual(200, self.client.get(f"/cases/{case_id}", headers=ME).status_code)
        self.assertEqual(404, self.client.get(f"/cases/{case_id}", headers=SOMEONE_ELSE).status_code)
        self.assertEqual(404, self.client.delete(f"/cases/{case_id}", headers=SOMEONE_ELSE).status_code)
        self.assertEqual([], self.client.get("/cases", headers=SOMEONE_ELSE).json())
        self.assertEqual([case_id], [c["id"] for c in self.client.get("/cases", headers=ME).json()])

    def test_the_token_itself_is_not_stored(self):
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        stored = (Case.load(case_id).folder / "case.json").read_text(encoding="utf-8")
        self.assertNotIn(ME["X-Haq-Device"], stored)

    def test_a_case_id_cannot_walk_out_of_the_cases_folder(self):
        self.assertEqual(404, self.client.get("/cases/..%2F..%2Fsecrets", headers=ME).status_code)
        self.assertEqual(404, self.client.get("/cases/case-..", headers=ME).status_code)

    def test_a_deleted_case_is_gone(self):
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        self.assertEqual(200, self.client.delete(f"/cases/{case_id}", headers=ME).status_code)
        self.assertEqual(404, self.client.get(f"/cases/{case_id}", headers=ME).status_code)


    def test_the_name_is_kept_and_checked(self):
        made = self.client.post("/cases", json={**STORY, "name": "Meera Iyer"}, headers=ME)
        self.assertEqual(200, made.status_code)
        self.assertEqual("Meera Iyer", Case.load(made.json()["id"]).data["customer_name"])
        self.assertEqual(422, self.client.post("/cases", json={**STORY, "name": "<script>"}, headers=ME).status_code)


class LimitsTest(unittest.TestCase):
    """A public server must not let anyone run up the model bill."""

    def setUp(self):
        self.workspace = Workspace()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.workspace.close()

    def _token(self, n):
        return {"X-Haq-Device": f"{n:0>43}"}

    def test_one_device_is_stopped_and_counts_reset_the_next_day(self):
        for _ in range(10):
            self.assertEqual(200, self.client.post("/cases", json=STORY, headers=ME).status_code)
        self.assertEqual(429, self.client.post("/cases", json=STORY, headers=ME).status_code)
        self.assertEqual(200, self.client.post("/cases", json=STORY, headers=SOMEONE_ELSE).status_code)
        with unittest.mock.patch.dict("os.environ", {"HAQ_TODAY": "2026-10-29"}):
            self.assertEqual(200, self.client.post("/cases", json=STORY, headers=ME).status_code)

    def test_new_tokens_from_one_address_do_not_get_around_it(self):
        for n in range(40):
            self.assertEqual(200, self.client.post("/cases", json=STORY, headers=self._token(n)).status_code)
        self.assertEqual(429, self.client.post("/cases", json=STORY, headers=self._token(99)).status_code)

    def test_the_whole_server_has_a_daily_run_limit(self):
        for address in ("a", "b"):
            limits.spend("run", address, address)
        with unittest.mock.patch.dict("os.environ", {"HAQ_MAX_RUNS_PER_DAY": "2"}):
            with self.assertRaises(limits.LimitReached):
                limits.spend("run", "c", "c")

    def test_a_refused_request_is_not_counted(self):
        for _ in range(8):
            limits.spend("run", "d", "x")
        with self.assertRaises(limits.LimitReached):
            limits.spend("run", "d", "y")
        limits.spend("run", "e", "y")  # "y" was not charged for the refusal

    def test_runs_are_limited_and_too_many_at_once_are_refused(self):
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        with unittest.mock.patch.object(api, "_schedule"):
            for _ in range(8):
                self.assertEqual(202, self.client.post(f"/cases/{case_id}/run", headers=ME).status_code)
            self.assertEqual(429, self.client.post(f"/cases/{case_id}/run", headers=ME).status_code)
        limits.reset()
        with unittest.mock.patch.object(api, "_running", {"1", "2", "3", "4"}):
            self.assertEqual(503, self.client.post(f"/cases/{case_id}/run", headers=ME).status_code)

    def test_long_text_and_too_many_files_are_refused(self):
        self.assertEqual(422, self.client.post("/cases", json={"story": "x" * 6001}, headers=ME).status_code)
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        case = Case.load(case_id)
        case.data["evidence"] = [{}] * limits.MAX_EVIDENCE
        case.save()
        got = self.client.post(f"/cases/{case_id}/evidence", files={"file": ("a.txt", b"hello")}, headers=ME)
        self.assertEqual(422, got.status_code)

    def test_a_public_server_refuses_a_contributor_model(self):
        with unittest.mock.patch.dict("os.environ", {"HAQ_PUBLIC": "1", "MODEL_API_MODEL": "muse-spark-1.3-contributor"}):
            with self.assertRaises(RuntimeError):
                config.check_public()
        with unittest.mock.patch.dict("os.environ", {"HAQ_PUBLIC": "1", "MODEL_API_MODEL": "muse-spark-1.3"}):
            config.check_public()

    def test_old_cases_are_purged_and_recent_ones_kept(self):
        old = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        recent = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        path = Case.load(old).folder / "case.json"
        long_ago = time.time() - 181 * 86400
        os.utime(path, (long_ago, long_ago))
        self.assertEqual(1, purge())
        self.assertEqual(404, self.client.get(f"/cases/{old}", headers=ME).status_code)
        self.assertEqual(200, self.client.get(f"/cases/{recent}", headers=ME).status_code)

    def test_a_run_cut_off_by_a_restart_can_be_retried(self):
        case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        case = Case.load(case_id)
        case.data["status"] = "working"
        case.save()
        api._pause_interrupted()
        self.assertEqual("paused", Case.load(case_id).data["status"])


class EvidenceFileTest(unittest.TestCase):
    """The customer's email can carry their proof, but not a file with a sensitive number."""

    def setUp(self):
        self.workspace = Workspace()
        self.client = TestClient(api.app)
        self.case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        evidence.add(Case.load(self.case_id), SAMPLE / "bank_sms.txt")
        self.url = f"/cases/{self.case_id}/evidence/E1/file"

    def tearDown(self):
        self.workspace.close()

    def _set(self, **fields):
        case = Case.load(self.case_id)
        case.data["evidence"][0].update(fields)
        case.save()

    def test_the_owner_gets_the_original_file(self):
        self._set(masked=False)
        got = self.client.get(self.url, headers=ME)
        self.assertEqual(200, got.status_code)
        self.assertEqual((SAMPLE / "bank_sms.txt").read_bytes(), got.content)
        view = self.client.get(f"/cases/{self.case_id}", headers=ME).json()
        self.assertTrue(view["evidence"][0]["attachable"])

    def test_nobody_else_gets_it(self):
        self._set(masked=False)
        self.assertEqual(404, self.client.get(self.url, headers=SOMEONE_ELSE).status_code)
        self.assertEqual(401, self.client.get(self.url).status_code)

    def test_a_file_with_a_sensitive_number_stays_back(self):
        self._set(masked=True)
        self.assertEqual(409, self.client.get(self.url, headers=ME).status_code)
        view = self.client.get(f"/cases/{self.case_id}", headers=ME).json()
        self.assertFalse(view["evidence"][0]["attachable"])

    def test_a_voice_note_stays_back(self):
        self._set(masked=False, kind="voice")
        self.assertEqual(409, self.client.get(self.url, headers=ME).status_code)

    def test_unknown_evidence_is_not_found(self):
        self.assertEqual(404, self.client.get(f"/cases/{self.case_id}/evidence/E9/file", headers=ME).status_code)


class OutcomeTest(unittest.TestCase):
    """When the customer is waiting on the bank, they tell Haq how it went."""

    def setUp(self):
        self.workspace = Workspace()
        self.client = TestClient(api.app)
        self.case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]

    def tearDown(self):
        self.workspace.close()

    def _wait(self, sent=()):
        case = Case.load(self.case_id)
        case.data["status"] = "waiting"
        case.data["sent"] = list(sent)
        case.save()

    def test_a_fixed_case_is_resolved(self):
        self._wait()
        view = self.client.post(f"/cases/{self.case_id}/fixed", headers=ME).json()
        self.assertEqual("resolved", view["status"])
        self.assertIsNone(view["hold"]["until"])

    def test_not_fixed_restarts_the_agent_with_the_dates(self):
        case = Case.load(self.case_id)
        case.set_dispute(rules.load("upi_failed_debit"), "p2p")
        case.save()
        self._wait(sent=[{"step": "bank", "on": "2026-10-30"}])
        with unittest.mock.patch.object(api, "_schedule") as schedule:
            got = self.client.post(f"/cases/{self.case_id}/not-fixed", headers=ME)
        self.assertEqual(202, got.status_code)
        message = schedule.call_args.args[1]
        self.assertIn("2026-10-30", message)
        self.assertIn("check_escalation", message)

    def test_not_fixed_names_the_company_on_an_online_order(self):
        case = Case.load(self.case_id)
        case.set_dispute(rules.load("ecommerce_refund"), "marketplace")
        case.save()
        self._wait(sent=[{"step": "company", "on": "2026-10-01"}])
        with unittest.mock.patch.object(api, "_schedule") as schedule:
            self.client.post(f"/cases/{self.case_id}/not-fixed", headers=ME)
        message = schedule.call_args.args[1]
        self.assertIn("the company on 2026-10-01", message)
        self.assertNotIn("bank", message)

    def test_only_a_case_waiting_on_the_bank(self):
        self.assertEqual(409, self.client.post(f"/cases/{self.case_id}/fixed", headers=ME).status_code)
        self.assertEqual(409, self.client.post(f"/cases/{self.case_id}/not-fixed", headers=ME).status_code)

    def test_nobody_else_can_answer(self):
        self._wait()
        self.assertEqual(404, self.client.post(f"/cases/{self.case_id}/fixed", headers=SOMEONE_ELSE).status_code)


class SentTest(unittest.TestCase):
    """A verified bank complaint, sent by the customer, starts the bank's 30 days."""

    def setUp(self):
        self.workspace = Workspace()
        self.client = TestClient(api.app)
        self.case_id = self.client.post("/cases", json=STORY, headers=ME).json()["id"]
        case = Case.load(self.case_id)
        for name in ("bank_sms.txt", "upi_app_status.txt", "statement_extract.txt"):
            evidence.add(case, SAMPLE / name)
        case.data["story"] = (SAMPLE / "story.txt").read_text(encoding="utf-8")
        case.save()

    def tearDown(self):
        self.workspace.close()

    def test_a_complaint_to_a_company_waits_one_month_and_names_the_helpline(self):
        case = Case.load(self.case_id)
        case.set_dispute(rules.load("ecommerce_refund"), "marketplace")
        case.data["drafts"].append({"step": "company", "passed": True})
        case.save()
        view = self.client.post(f"/cases/{self.case_id}/sent", json={"on": "2026-10-28"}, headers=ME).json()
        self.assertEqual("waiting", view["status"])
        self.assertEqual("2026-11-28", view["hold"]["until"])
        self.assertIn("The company has until 28 Nov 2026", view["hold"]["message"])
        self.assertIn("the National Consumer Helpline", view["hold"]["message"])

    def test_no_draft_means_nothing_to_send(self):
        self.assertEqual(409, self.client.post(f"/cases/{self.case_id}/sent", json={}, headers=ME).status_code)

    def test_progress_and_sending_the_draft(self):
        agent.start(Case.load(self.case_id), FakeClient(HAPPY_PATH))
        view = self.client.get(f"/cases/{self.case_id}", headers=ME).json()
        self.assertEqual("draft_ready", view["status"])
        self.assertEqual("Writing your complaint", view["progress"]["current"])
        self.assertIn("Calculating what you are owed", view["progress"]["steps"])

        sent = self.client.post(f"/cases/{self.case_id}/sent", json={"on": "2026-10-28"}, headers=ME).json()
        self.assertEqual("waiting", sent["status"])
        self.assertEqual("2026-11-27", sent["hold"]["until"])
        self.assertEqual([{"step": "bank", "on": "2026-10-28"}], [{k: s[k] for k in ("step", "on")} for s in sent["sent"]])
        card = self.client.get("/cases", headers=ME).json()[0]
        self.assertEqual(("waiting", "2026-11-27", 1500), (card["status"], card["until"], card["compensation_owed"]))

    def test_a_future_send_date_is_refused(self):
        agent.start(Case.load(self.case_id), FakeClient(HAPPY_PATH))
        response = self.client.post(f"/cases/{self.case_id}/sent", json={"on": "2026-12-01"}, headers=ME)
        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
