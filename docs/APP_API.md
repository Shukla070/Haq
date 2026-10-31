# App ↔ server API

What the Android app relies on. The server is `server/haq/api.py`; interactive docs are at
`/docs` when it runs.

## Device token

On first launch the app makes a random token (32 bytes, URL-safe base64, 43 characters)
and keeps it in private app storage. Every request sends it:

```
X-Haq-Device: <token>
```

A case belongs to the install that created it. The server stores only a SHA-256 hash of
the token; any other token gets **404** for that case, as if it did not exist. No token, or
a malformed one, gets **401**. There are no accounts: losing the token (app data cleared)
means losing access to its cases.

## Endpoints

| Method and path | Body | Returns |
|---|---|---|
| `GET /health` | | `{ok, model}` |
| `POST /cases` | JSON `{story, name}`; `name` signs the complaint (letters, spaces, `.` `'` `-`; up to 80) | the case view |
| `GET /cases` | | the home list: `[{id, created, status, running, title, dispute_type, compensation_owed, until}]`, newest first |
| `GET /cases/{id}` | | the case view; poll it every 2–3 s while `running` |
| `POST /cases/{id}/evidence` | multipart: `file`, optional `note` | `{id, kind, original_name, masked, instruction_like}`. Screenshots and PDFs are transcribed, voice notes (`.m4a`, `.ogg`, `.wav`, ...) transcribed. Max 32 MB (**413**); unreadable file **422**. Takes a few seconds. |
| `GET /cases/{id}/evidence/{evidence_id}/file` | | the original file, for the customer's email. **409** for a voice note or a file with a sensitive number (`attachable` is false). |
| `POST /cases/{id}/run` | | **202** `{case_id, running: true}`; **409** if already running |
| `POST /cases/{id}/answer` | JSON `{text}` | **202**; answers the open question and resumes the agent |
| `POST /cases/{id}/sent` | JSON `{on}` (YYYY-MM-DD, empty for today) | the case view; the customer sent the verified draft themselves. A bank complaint puts the case in `waiting` until the bank's reply deadline. **409** if there is no verified draft. |
| `DELETE /cases/{id}` | | `{deleted}`; the case and its evidence are removed from the server. **409** while running. |

To answer with a voice note: upload it with `POST /evidence`, then `POST /answer` with
text such as "I recorded a voice note with my answer".

## Case view

The fields the app uses:

| Field | Use |
|---|---|
| `status` | which screen to show; see below |
| `running` | show the progress screen and keep polling |
| `progress` | `{current, steps[], turn, drafts_refused, seconds}`; `current` is a friendly label like "Calculating what you are owed" |
| `evidence[]` | `{id, kind, original_name, masked, instruction_like, attachable}`; show a shield when `masked`, a warning when `instruction_like` is not empty; `attachable` files go with the email |
| `coverage` | checklist item → `proven` / `user_stated` / `open` |
| `facts[]`, `user_statements[]` | what is proven (with its evidence id) vs what the customer said |
| `entitlement` | `{reversal_due_by, days_late, compensation_owed, compensation_still_growing, ...}` |
| `draft` | the latest verified draft: `{step, recipient, subject, body, rule_ids, fact_ids, gaps, next_steps}` |
| `question` | the open question `{question, why}` when `needs_input` |
| `hold` | `{status, until, reason, message}` when `waiting` or `resolved` |
| `referral` | `{reason, where}` when `referred` |
| `sent[]` | `{step, on}` for each complaint the customer marked as sent |

## Statuses

| Status | Screen |
|---|---|
| `new` | evidence picker, then Run |
| `working` | progress (`running` is true) |
| `draft_ready` | the draft: amount owed, proven vs said, Copy / Send by email / Mark as sent |
| `waiting` | countdown to `hold.until`, with `hold.message`; a reminder on that date |
| `needs_input` | `question`, answered by text or voice |
| `referred` | `referral`, with tap-to-call for 1930 and 14448 |
| `resolved` | done |
| `filed` | an Ombudsman complaint was sent |
| `sent` | sent, and the bank's reply period has already passed |
| `paused` | something went wrong (API error, turn limit); offer Retry (`POST /run`) |
