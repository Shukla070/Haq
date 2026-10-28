# Build plan

Submission deadline: Wed Nov 4, 9:00 PM ET (Thu Nov 5, 6:30 AM IST). Live final for the top
five per track: Nov 9. The plan aims to have the submission done on the evening of Nov 4
IST, with a day of slack.

| Day (IST) | Goal | Done when |
|---|---|---|
| Oct 28–29 | **Agent core.** Case record, agent loop, CLI and API skeleton, failed-UPI-debit rule pack | A sample UPI case runs from evidence to a verified bank complaint draft |
| Oct 30 | **Evidence intake.** Screenshots and PDFs transcribed and quote-checked, voice notes via Muse Voice Transcribe, sensitive numbers masked | Real screenshots and a Hinglish voice note produce correct facts |
| Oct 31 | **Verifier.** Checklist coverage from the rule pack, citation checks, evidence-injection screening, run-level report | A planted injection and a made-up citation are both caught in a demo case |
| Nov 1 | **Android app.** Start a case, add evidence, follow progress, approve drafts, deadline reminders | The full UPI flow works on a phone against the dev server |
| Nov 2 | **Second and third disputes.** E-commerce refund rule pack with SAM 3.1 unboxing-video evidence; flight rule pack if time allows | An unboxing video shows the tracked parcel and product in the case file |
| Nov 3 | **Hardening.** Speed (target: first draft in under 2 minutes), errors, privacy policy, README, logged-out repo check | Three end-to-end test cases pass twice in a row |
| Nov 4 | **Ship.** 3-minute demo video, CV platform submission | Submitted, with the public repo link checked logged out |

## After submission

- Nov 5–8: post the demo on X for the Most Viral bonus (closes Nov 8, 11:59 PM ET).
- Nov 9: live final, if selected.
- Play Store: a new personal developer account needs a 14-day closed test with 12 testers
  before production, so recruit testers early.

## Rules for the build

- Every rule, section number and time limit in a rule pack is checked against its official
  source, with the URL and the date it was checked.
- Development uses Contributor model variants with test data only.
- Commit small, push at least daily, add a dated entry to [BUILD_LOG.md](BUILD_LOG.md).
