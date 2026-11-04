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
- Tested on a real phone (Nothing A059, Android 16): a Hinglish voice note, a screenshot and a
  statement ended in a verified complaint for Rs 4,500 plus Rs 1,700, signed with the
  customer's name. The USB tunnel dropped once when the phone reconnected, which the app
  showed as "check your connection"; `adb reverse` has to be run again after that.
- "Send by email" now attaches the proof, so the bank gets more than text. The stored file is
  the customer's original, and masking only covers the text the agent reads, so a file with a
  sensitive number stays back and the app says why; voice notes stay back too. The server
  enforces this. Tried with Gmail on 2026-11-01, see below.

## 2026-10-31

- Reminders: a waiting case now notifies the customer at 10 am on the bank's reply date, using
  WorkManager, which is built to survive a reboot (not yet tested). The text names no bank or
  amount because it can show on a locked phone. The app asks for the notification permission at the moment it is needed, and
  says to use a calendar if refused.
- The reminder needed somewhere to lead: a waiting case had no next step at all. It now asks
  "Has the bank fixed this?". Yes resolves the case. No restarts the agent with today's date.
- Tested on the emulator with the date moved on: the reminder fired and opened the right case;
  before the bank's 30 days were up the agent put the case back on hold and the reminder
  moved to the new date; after them, it asked whether the bank had replied, then wrote an
  Ombudsman complaint for Rs 3,800 (38 days late, file by 11 Feb 2027), verified first time.
  83 offline tests.

## 2026-11-01

- Second dispute type: online order refunds (`ecommerce_refund`), checked against the official
  texts: the Consumer Protection (E-Commerce) Rules, 2020 (refund duties in rules 6(3) and 7(4);
  the grievance officer's 48 hours and one month in rules 4(5) and 6(4)(b)), the Consumer
  Protection Act, 2019, and a 2026 Lok Sabha reply for the National Consumer Helpline's channels.
- The ladder is the company's grievance officer, then the helpline. Filing in a consumer
  commission is named as the next step but not drafted, because it is a formal court filing.
- These rules set no daily compensation and no fixed refund date, so Haq asks only for the
  refund. The verifier refuses any compensation figure nobody computed, and now also refuses a
  rule number that is not in a cited rule. One month is a calendar month, not 30 days.
- An amendment notified on 9 September 2026 starts on 1 January 2027. From law-firm summaries,
  not the Gazette text, it keeps these rule numbers and the refund duties, and adds a copy of the
  recorded complaint to rule 4(5). Check the Gazette text before relying on it after that date.
- The rest of the agent no longer assumes a bank: the pack names who the customer is waiting on
  and the next step, and the app's wording is neutral.
- Live runs: a cracked mixer grinder from a marketplace seller gave a verified complaint to the
  company for Rs 3,499 and noticed the customer reported it inside the return window. Shoes that
  never came, with no reply in a month, gave a verified helpline grievance for Rs 2,199. A fake
  shop was referred to 1930. The UPI sample still gives its Rs 1,500 bank complaint.
- Reading those drafts found two faults the verifier missed, both fixed in the agent's
  instructions and gone on re-running: a reply date with no source, and the customer's own email
  and chat lines recorded as proof of what they claim. The verifier still does not check dates.
- On the emulator: the complaint appeared in the app, and "I've sent it" gave a wait until 1 Dec
  2026 naming the helpline. 97 offline tests.
- Getting ready for a public server, not yet deployed:
  - Anyone can make a device token, so daily limits apply per device, per IP address and across
    the server, with caps on agent runs at once, text length, files per case and low disk. Counts
    stay in memory, so no IP address is stored.
  - `HAQ_PUBLIC=1` refuses to start with a Contributor model. A live run on standard
    `muse-spark-1.3` gave a verified complaint: 16 turns, about 111K tokens.
  - A restart pauses any cut-off run so it can be retried, and cases with no activity for 180 days
    are deleted.
  - Writing the privacy policy exposed a false claim: the app said sensitive numbers were hidden
    "before anything reads them" and the README said "before storage". Files go to the model to be
    read first, and originals are stored as given. Corrected, and the policy says so plainly.
- The server is live on AWS Lightsail in Mumbai (Ubuntu 24.04, 1 GB, https through Caddy), on the
  standard model. Over https, a screenshot, a PDF with a card number and a voice note gave a
  verified bank complaint in 74 seconds; the PDF stayed out of the email, another device got 404,
  and delete removed the case from disk. The emulator app ran a case with no USB tunnel. The
  machine's clock was on UTC, which would have dated deadlines a day early before 5:30 am in
  India, so the service now runs on India time.

- The first real try of "Send by email" failed: with proof attached, the app said no email app was
  found, on a phone with Gmail. The file type set on the request also applied to the email-only
  filter, so no app matched. Removing it fixed the emulator and the phone. On the phone, Gmail
  opened with the subject, complaint and attachments filled in (not sent).
- SAM 3.1 now marks damage in photos, in `mark_damage`. A live test changed the design: SAM returned
  nothing for "crack", "damage" or "jar", and marked the wrong things for "broken plastic", but found
  "blender" at 96%. So Muse Spark locates the damage, SAM separately finds the product, and a copy is
  marked only if they agree. In the app on the live server, an online-order case with a generated
  photo of a cracked jar reached a verified complaint with the marked copy attached, in about 70
  seconds. A generated photo of an undamaged product and a UPI screenshot were both refused. Not yet
  tried on a real photo from a phone. Unboxing video is not built.
- The first signed release build crashed on launch, twice, for reasons the debug build could not
  show, because only release builds are shrunk. The template's `packageScope` left a class extending
  one it could no longer reach, and shrinking then removed the constructor WorkManager's database is
  created through. Dropping `packageScope` and adding one keep rule fixed both. A release build now
  also refuses to build without an https server address and the signing key, which lives outside the
  repo. On the emulator, against the live server, the release build ran an online-order case to a
  verified complaint with the marked photo, opened Gmail with all 4 attachments, fired the reminder
  when its job was forced, and opened the case from the notification. "Not fixed" on the day the
  complaint was sent asked about a reply, then kept waiting until the deadline instead of escalating.
  Not yet run on a real phone.
- The online-order rules now name e-Jagriti as where to file with a consumer commission. They said
  to file but not where, which an outside review of the plan pointed out.
- The app had still been on Android's stock theme. It now looks like a complaint file: ledger green
  and paper, a marigold action, stamp red for money owed, in Rozha One and Hind, which both cover
  Hindi. A new icon is drawn from the word हक़. A first-launch guide and `docs/USER_GUIDE.md` explain
  the app. No case logic changed. Looking at the screens caught two bugs the build did not: "Your
  cases" was paper-coloured text on paper, and outlined buttons were grey. On the emulator, the
  release build ran an online-order case and a UPI case to verified complaints. The home screen and
  guide were also checked in dark mode. Not yet on a real phone.
- The first run on a real phone worked, and reading its two complaints found three problems. The next
  steps said "marked damage photo E4", Haq's own label, so the verifier now refuses those labels in
  anything the customer reads. A UPI complaint said the payee did not receive the money, which neither
  the customer nor the proof had said. And it treated "not refunded" as the customer's word alone,
  though the statement showed no credit up to 27 Oct. The last two are instructions to the agent, not
  checks in code: the first wording still stated the claim as fact in 1 of 3 runs, the second was right
  in 5 of 5, and that lowers the risk without removing it. All five samples still give their expected
  results.
- Using the app on a real phone showed that its screens did not explain themselves: links looked like
  plain text, and a status or ₹2,000 sat alone with no label. Each value now has a label, the amount
  says why it is owed, buttons look like buttons, and a case shows what the customer said instead of
  "I explained what happened in my voice note."
- A pass over the remaining gaps. A sent complaint can now be reread, and the app says the customer adds
  the email address themselves, because Haq has no verified list of addresses. "No cases yet" showed when
  the server could not be reached, which is untrue, so it now says the cases could not load. A referred
  case showed the agent's own note ("outside both rule packs"), so it now shows only where to go. On the
  emulator, the complaint read well in dark mode, "not fixed" asked about a reply and went back to
  waiting, a scam story went to 1930, and the reminder job survived a full restart and fired when forced.
- Haq now runs in the browser too, so anyone can try it without Android. The website is plain HTML,
  CSS and JavaScript in `server/web`, served by the same server as the app's API, with headers that
  let only its own code run; text from the server is only ever shown as text. It does what the app
  does, except that the email cannot carry the proof (there is a download for each file) and there is
  no reminder notification (it offers a calendar file). On a local server it ran a UPI case from
  three files through the complaint, "sent", "not fixed", an answer and deletion; on the live server
  it showed a damaged-order case with the marked photo. Voice notes on the web are not tested yet.
