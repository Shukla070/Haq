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

## Tools

Evidence is transcribed when it is added (screenshots and PDFs with Muse Spark, voice
notes with Muse Voice Transcribe), so the agent reads text. Its tools:

| Tool | What it does |
|---|---|
| `list_evidence`, `read_evidence` | See what the customer shared, and read it (masked, with injection warnings) |
| `classify_dispute` | Pick the dispute type and payment type; loads the rule pack's checklist |
| `record_fact` | Add a fact; refused unless its quote is in the evidence |
| `record_user_statement` | Record what only the customer says, kept apart from proof |
| `add_timeline_event` | Record a dated event |
| `calculate_entitlement` | Reversal deadline and compensation owed, computed in code |
| `check_escalation` | Which step is due: complain to the bank, wait for its reply, or the Ombudsman |
| `ask_user` | Ask the customer for something only they can provide |
| `refer_out` | Send fraud, scams and other out-of-scope cases where they belong |
| `submit_draft` | Hand the complaint to the verifier |
| `hold_case` | End without a draft when none is due: the bank still has time, or the customer is satisfied |

Planned: SAM 3.1 to locate damage in unboxing photos and videos for the e-commerce pack.

## How a run ends

| Status | Meaning | What the app shows |
|---|---|---|
| `draft_ready` | A verified complaint for the step that is due | The draft, to approve and send |
| `waiting` | Complained recently; the bank still has time to reply | The reply deadline and what is owed so far |
| `needs_input` | The agent needs something only the customer knows | The question |
| `referred` | Outside what Haq handles | Where to go instead |
| `resolved` | The customer accepts the bank's reply | Done |
| `paused` | API error or turn limit | Retry |

Each run records how long every model call and tool took (`run.json`). In the first live
runs, model calls took 3–7 seconds each and tools under 0.1 seconds, so run time is the
number of turns.

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
