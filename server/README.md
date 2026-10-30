# Haq server

The agent, its tools and rule packs, the verifier, and an HTTP API for the app.

## Setup

Python 3.11 or newer.

```bash
python -m venv .venv
```

Install the dependencies with the venv's pip (`.venv/bin/pip` on Linux and macOS,
`.venv\Scripts\pip` on Windows):

```bash
.venv/bin/pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Meta Model API key. `.env` is git-ignored.

## Run a case from the command line

```bash
python -m haq new "$(cat ../samples/upi-failed-debit/story.txt)" ../samples/upi-failed-debit/bank_sms.txt ../samples/upi-failed-debit/upi_app_status.txt ../samples/upi-failed-debit/statement_extract.txt
```

Other commands: `add`, `run`, `answer`, `show` (see `python -m haq --help`). Set
`HAQ_TODAY=YYYY-MM-DD` to pin the date the agent treats as today. Cases are saved under
`workspace/cases/`.

## Run the API

```bash
uvicorn haq.api:app --reload
```

`POST /cases`, `POST /cases/{id}/evidence`, `POST /cases/{id}/run`, `POST /cases/{id}/answer`,
`GET /cases/{id}`. Interactive docs at `/docs`.

## Tests

Offline, no API calls:

```bash
python -m unittest discover -s tests
```

## Layout

| Path | What it is |
|---|---|
| `haq/agent.py` | The loop: the model picks one tool per turn; code runs it, times it, and saves the run |
| `haq/tools/` | One module per tool |
| `haq/case.py` | The case record; refuses quotes that are not in the evidence |
| `haq/rules/` | Rule packs (JSON) and the deadline and compensation maths |
| `haq/verify.py` | Checks every draft before the customer sees it |
| `haq/guard.py` | Sensitive-number masking and injected-instruction detection |
| `haq/evidence.py` | Adds evidence; transcribes screenshots and PDFs with Muse Spark |
| `haq/prompts/system.md` | The agent's instructions |
