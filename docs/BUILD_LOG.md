# Build log

Dates are in IST.

## 2026-10-28

- Chose the project: Haq, a consumer-side money-recovery agent. Indie Developer track,
  theme "Build for Your World". Checked it against the event's list of overdone projects.
- Set up the toolchain: Meta Model API key with hackathon credits, Muse Code 1.4.14 in
  WSL Ubuntu, Meta's legal-agent-workshop kit.
- Workshop Session 1: built the agent loop with Muse Code. All offline tests pass.
- First full agent run: 19 turns, about 27 minutes, memo filed. Reviewed it against the
  workshop's planted flaws; two of three got through. The lessons are written up in
  [DESIGN.md](DESIGN.md#what-the-workshop-run-taught-us) and shape Haq's verifier.
- Started this repository: README, design notes, build log, 7-day plan.
- Agent core, first cut (`server/`):
  - Case record where facts are refused unless their quote is in the evidence, and the
    customer's unsupported statements are kept apart from proven facts.
  - Failed-UPI-debit rule pack, checked against RBI's own pages: the 2019 turnaround-time
    circular (T+1 / T+5 and Rs 100 per day) and the Integrated Ombudsman Scheme, 2026
    (in force from 1 July 2026; 90-day filing window).
  - 11 tools, including deadline and compensation maths done in code, never by the model.
  - Verifier outside the agent: escalation step, cited rules, amounts, checklist coverage,
    sensitive numbers, injected text.
  - Sensitive-number masking (cards, Aadhaar, OTPs) that keeps UPI references intact.
  - CLI and an HTTP API skeleton for the app. 31 offline tests.
- First live runs on the sample case: about 1.5–2 minutes, 14 turns, about 89K tokens, ending
  in a verified bank complaint asking for the Rs 4,500 reversal and Rs 1,500 compensation.
  The verifier caught the agent citing a customer statement as a fact; it fixed it.
