import unittest

from fastapi.testclient import TestClient

from haq import agent, api, evidence
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
