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
- Android app, first working version (`android/`): Kotlin and Jetpack Compose on Android
  Gradle Plugin 9.5, from Android Studio's own template so the versions match. Home (your
  cases), new case (story plus screenshots and files through Android's photo picker, which
  shares only the photos picked), live progress, and a screen per outcome: the verified
  draft with Copy, Send by email and "I've sent it"; waiting; a question to answer;
  referral with tap-to-call; retry. No networking library: plain `HttpURLConnection`.
- End to end on the emulator: typed a story, attached the UPI screenshot, and watched the
  progress screen step through the agent's work; after about two minutes it showed the
  verified bank complaint (Rs 1,700 compensation, 17 days late, citing RBI/2019-20/67).
- The emulator could not reach the laptop through its usual address (10.0.2.2). Switched
  to `adb reverse`, which gives the device the laptop's server at its own 127.0.0.1 and
  works the same for a phone on USB. Debug builds allow plain http only to 127.0.0.1;
  release builds are https only.
- Voice notes and "Share to Haq" in the app, built with Muse Code from our brief:
  - Record a voice note on the new-case screen, or answer the agent's question with one.
    A case can be started from a voice note alone, with nothing typed.
  - Haq appears in Android's share sheet for screenshots, PDFs, audio and text. A bank SMS
    shared as text becomes evidence ("Shared message 1.txt"), not the customer's story.
    Shared files are copied into private storage at once, because the sending app's
    permission to read them can expire.
  - Photo-picker names like "36.png" are shown as "Screenshot 1.png".
- Review and testing on the emulator found two bugs the compiler couldn't:
  - Tapping Record made 2,474 empty files. Inside the recorder's setup block, `start()`
    called the screen's own `start()` function instead of the recorder's, so each start
    opened another recorder until the system refused. Renamed, and a recorder that fails
    to start is now released.
  - A share was attached again after rotating the phone or reopening Haq from recents.
- Tested by sharing from the Files app (one file, then a screenshot and a voice note
  together) and from text: a case with no typed story, only a spoken account and the
  screenshot, ended in a verified complaint to Kaveri Bank (Rs 1,700, 17 days late) in
  about 100 seconds. The voice note's claims stayed the customer's statements.
- Complaints are signed with the customer's name instead of "Customer". The app asks for
  it once ("as your bank knows it") and remembers it on the phone; the server keeps it on
  the case. Because the name goes into the agent's prompt, it is limited to letters (any
  script, so Devanagari names work), spaces and . ' -, and refused if it reads like an
  instruction. The verifier refuses a draft that is not signed with it. Live run: the
  agent asked whether the customer had already complained, then the draft was verified
  first time and signed "Meera Iyer".
- A voice note with no speech now asks the customer to record it again, instead of
  showing "missing transcript". 74 offline tests.
