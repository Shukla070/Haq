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

## 2026-10-29

- Voice notes are routed to a new voice module (Muse Voice Transcribe, Hindi and English
  with code-switching; WAV only, so other formats are converted with ffmpeg). The module,
  `haq/voice.py`, and its offline tests were built with Muse Code. Live check: an .m4a note
  was converted and transcribed accurately in about 5 seconds.
- Screenshot and PDF intake tested live on rendered fictional evidence: exact
  transcription, and the card number in a scanned PDF masked before the agent saw it.
- Fixed a verifier false positive: statements print amounts without "Rs", so any number in
  the quoted evidence now counts as a known amount.
- New test case with a planted prompt injection in a bank support chat screenshot. The
  agent ignored it and escalated correctly to the RBI Ombudsman (Rs 3,800 compensation,
  file by 18 Jan 2027), but the code-level detector had missed it because the phrase was
  split across screenshot lines. Fixed: the detector now collapses whitespace and catches
  "note for AI assistants". Re-run: flagged, and the run finished in about 2 minutes.

## 2026-10-30

- Kept the hand-written agent loop rather than adopting an agent framework: the value is
  in the tools, the case record and the verifier, and the loop's exact stop, nudge and
  resume behaviour is easier to control in 100 lines of our own code.
- New outcome when no complaint is due yet: if the customer complained recently and the
  bank still has time to reply, the agent now puts the case on hold until the bank's reply
  deadline (`hold_case`) instead of being stuck unable to draft. The verifier refuses any
  draft while the bank still has time, and the customer-facing hold message gets the same
  amount and sensitive-number checks as a draft. Live run on a new sample: 14 turns, no
  draft, held until 19 Nov 2026 with the Rs 1,500 owed so far explained.
- Run timing: every model call and tool is now timed in `run.json`. The live run took 68
  seconds; model calls took 3–7 seconds each and tools under 0.1 seconds, so speed comes
  from fewer turns.
- Amounts spoken as words: a new module, `haq/amounts.py`, reads them in English, Hinglish
  ("saadhe chaar hazaar", "dedh sau") and Devanagari ("चार हज़ार पांच सौ", "४,५००"), and the
  verifier now counts them. Built with Muse Code. In review we fixed two cases real Hindi
  transcripts would hit: the danda (।) glued to the last word hid the amount, and "chaar
  hazaar paise" (Hinglish for Rs 4,000) was dropped as paise.
- A live voice-only case exposed two guardrail holes, both fixed:
  - The agent marked items *proven* by quoting the customer's own voice note. A voice note
    is the customer's account, like the story, so the case record now refuses facts from
    voice notes; they become user statements.
  - The transcriber misheard the fictional "Kaveri Bank" as a real bank's name, and the
    agent addressed the complaint to it. The agent is now told that evidence wins when the
    customer's words and the evidence disagree. Re-run: addressed to Kaveri Bank.
- Amounts are now checked against the customer's own words (story, voice notes, answers)
  rather than the agent's paraphrase of them, which the model writes itself.
- Live voice-only run after the fixes: draft verified first time, 13 turns, about 2 minutes.
- 61 offline tests.
- Started the Android app: Kotlin and Jetpack Compose, tested on a real phone. Server
  work for it first:
  - Each install sends a random device token; a case is visible only to the install that
    created it (the server keeps only a hash). No accounts, so nothing ties a case to a
    name or phone number.
  - Case list for the home screen, friendly progress labels while the agent works, delete
    a case, a 32 MB upload limit, and "mark as sent", which starts the bank's 30 days so
    the app can remind the customer.
  - Case ids from the URL are validated, so a crafted id cannot point outside the cases
    folder.
- Drove the API end to end like the app (create, upload a screenshot and two texts, run,
  poll every second). The first try crashed: on Windows a save fails while another request
  is reading the same file, and the crash left the case stuck at "working". Fixed: saves
  retry briefly, each run gets its own thread apart from the request that started it, and
  a run that fails is paused so the app can retry. Re-run: 82 polls, draft verified in 83
  seconds, another device's token gets 404.
- The app's API contract: [APP_API.md](APP_API.md). 69 offline tests.
