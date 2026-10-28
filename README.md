# Haq

**Get your money back from companies that owe it to you.**

Haq (हक़, "what is rightfully yours") is an AI agent that takes an Indian consumer from
"they refused my refund" to an escalation the company has to answer. You show it what
happened: screenshots, bills, emails, bank SMS, or a voice note in Hindi or Hinglish.
Haq builds an evidence-backed case file, works out which rules apply and who to complain
to, drafts each complaint, and tracks the deadlines until the money comes back.

> Built for the [Meta Global AI Developer Hackathon](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)
> (Oct 26 – Nov 4, 2026). Indie Developer track, theme **Build for Your World**.

## The problem

Every day Indians lose money they are legally owed: a refund that never arrives, a
cancelled flight, a failed UPI payment that was debited but never reversed, a wrong
bank charge. The rules are often on the consumer's side, with company grievance
officers, sector ombudsmen and consumer commissions. Most people still give up, because
they don't know:

- which forum handles their problem, and in what order to escalate,
- what deadline the company has to reply, and when it has passed,
- how to write a complaint that cites the right rule and the right evidence.

Today's options don't close that gap. Helplines are slow and generic, a lawyer costs
more than the claim, a general chatbot writes one generic letter (sometimes citing rules
that don't exist) and never follows up, and claim-agency apps cover only flights and
keep a large cut.

## What Haq does

1. **Intake.** The user shares evidence in any form. Haq reads it and records each fact
   with the exact quote or image region it came from.
2. **Diagnose.** It classifies the dispute and loads a **rule pack** for that type: what
   must be proven, which rules apply, the escalation ladder, and the deadline at each step.
3. **Draft.** It writes the complaint for the current step, citing only verified rules and
   recorded facts. A verifier outside the agent blocks anything unsupported.
4. **Follow through.** It tracks the company's promised and legal deadlines ("they
   promised a refund by the 15th; it's the 17th") and prepares the next escalation. When
   the company replies, the user adds the reply and Haq re-plans.

The user approves every message before it is sent. Haq never sends anything by itself.

**Launch scope:** e-commerce refunds, flight cancellations and delays, and failed UPI or
wrong bank debits.

## Meta models

| Model | Role in Haq |
|---|---|
| **Muse Spark** (`muse-spark-1.3`) | The agent: planning, tool calls, reading screenshots and PDFs, drafting complaints |
| **SAM 3.1** | Evidence from photos and unboxing videos: finds and tracks the parcel and product to show damage or a wrong item |
| **Muse Voice Transcribe** | Hindi and Hinglish voice-note intake |
| **Muse Image** | Evidence exhibit sheet: labelled crops and a timeline for the complaint |
| **Muse Code** | Coding agent used to build Haq |

## Guardrails

Guardrails are part of the design, not an add-on:

- **Rule packs define the checklist, not the model.** For each dispute type, what must
  be proven is written by us, and code checks every draft against it.
- **Every claim needs its source.** A fact is "proven" only if it points to a quote or
  image region in the evidence. Something the user says without evidence is marked as
  the user's statement.
- **Verified citations only.** A rule or section can be cited only if it is in the
  verified rule corpus.
- **Text inside evidence is data, never instructions.** Screenshots and PDFs can contain
  text that tries to steer the agent; it is screened and never obeyed.
- **Sensitive numbers are hidden.** Aadhaar, card numbers and OTPs are masked before
  storage and can never appear in an outgoing draft.
- **Evidence is never edited.** Haq refuses to alter or generate evidence images.
- **Out of scope is referred on.** Criminal and family matters, and claims past their
  time limit, are referred to free legal aid instead of drafted.

Haq helps people use consumer grievance channels. It is not a law firm and does not
give legal advice.

## Status

Early build. The agent core works end to end on a failed-UPI-debit case: from evidence to
a verified bank complaint in about two minutes. See [server/README.md](server/README.md) to
run it, [docs/BUILD_LOG.md](docs/BUILD_LOG.md) for progress, [docs/PLAN.md](docs/PLAN.md)
for the plan, and [docs/DESIGN.md](docs/DESIGN.md) for the architecture.

## Acknowledgements

The agent design (a tool-calling loop, quote-checked facts, and verification outside the
agent's control) follows the patterns taught in Meta's
[legal-agent-workshop](https://github.com/meta-models/legal-agent-workshop). Haq's code is
written separately for this project.
