# Haq design

Working design. It will change as the build goes on; decisions and their reasons are
recorded here.

## Shape of the system

```
Android app ──► Haq API server ──► Agent loop ──► Meta Model API
 (evidence,       (cases, users,     (Muse Spark      (muse-spark, sam-3.1,
  approvals,       reminders)         picks tools)     voice-transcribe, image)
  reminders)                              │
                                          ▼
                                 Verifier (outside the agent)
                                 rule pack checks, citation checks,
                                 sensitive-data checks
```

- **App:** captures evidence, shows the case and its deadlines, asks the user to approve
  each draft, and sends reminders.
- **Server:** Python. Holds cases and runs the agent. Keeps the API key; the app never
  sees it.
- **Agent loop:** the model chooses every tool call; code runs the tool, records the
  result, and saves progress every turn so a case can pause and resume.
- **Verifier:** runs after the agent and before the user sees a draft. The agent cannot
  turn it off.

## Case record

A case holds:

- **Evidence:** each uploaded item, with extracted text or transcript.
- **Facts:** each fact links to its evidence item and the exact quote or image region.
  Facts with no evidence behind them are stored as *user-stated*.
- **Checklist:** loaded from the rule pack for the dispute type, not invented by the model.
- **Timeline:** dated events (order, payment, complaint sent, promised refund date,
  reply received).
- **Escalation state:** the current step on the ladder and its deadline.
- **Drafts:** each draft complaint and its verification result.

## Rule packs

One rule pack per dispute type, written and checked by hand:

- what must be established (for example, for a failed UPI debit: the debit happened,
  the transaction failed, the amount was not reversed),
- which rules apply, with exact citations from the verified corpus,
- the escalation ladder and the time allowed at each step,
- the evidence that settles each checklist item.

Every rule, section number and time limit is checked against its official source
before it goes into a rule pack. Nothing is cited from model memory.

## Tools (first cut)

| Tool | What it does |
|---|---|
| `read_evidence` | Read one evidence item (image, PDF, email text) and return quote-checked facts |
| `transcribe_voice` | Turn a voice note into text with Muse Voice Transcribe |
| `locate_in_media` | Find and track an object in a photo or video with SAM 3.1 |
| `record_fact` | Add a fact to the case; refused unless its quote is in the evidence |
| `classify_dispute` | Pick the dispute type and load its rule pack |
| `add_timeline_event` | Record a dated event |
| `draft_complaint` | Draft the complaint for the current escalation step |
| `request_from_user` | Ask the user for missing evidence or a decision |

## What the workshop run taught us

The first run of the workshop agent (19 turns, about 27 minutes) filed a memo that
called every checklist item proven. The problems map directly onto Haq:

| Workshop problem | Haq equivalent | Fix in code |
|---|---|---|
| A signature was marked proven because meeting minutes said it was signed | "The company promised a refund by the 15th" based only on what the user says | Proven only with a source; otherwise *user-stated* |
| A privileged memo was read; only model judgment kept it out of the memo | Aadhaar, card numbers, OTPs in screenshots | Mask before the model reads; hard block in outgoing drafts |
| The model wrote its own checklist and nothing checked it | The model deciding what a refund claim must prove | Checklist comes from the rule pack; the verifier checks drafts against it |
| 27 minutes, with the whole history resent every turn | A phone user will not wait that long | One evidence item per call, a short case summary instead of full history, live progress in the app |

## Privacy

Development uses the Contributor model variants covered by hackathon credits; content
sent to them may be used for product improvement. Only test data is used with them.
Real users' data goes only to standard (non-Contributor) models, and the privacy policy
will say what is sent and why.
