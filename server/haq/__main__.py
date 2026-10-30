"""Command line for working cases without the app.

    python -m haq new "story..." [evidence files...]   start a case, add evidence, run the agent
    python -m haq add CASE_ID FILE [--note TEXT]        add evidence to a case
    python -m haq run CASE_ID [--turns N]               run (or re-run) the agent on a case
    python -m haq answer CASE_ID "answer..."            answer the agent's question and continue
    python -m haq show CASE_ID                          the case summary and latest draft
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import agent, config, evidence
from .case import Case
from .llm import make_client


def show(case: Case) -> None:
    print(json.dumps(case.summary(), indent=2, ensure_ascii=False))
    question = next((q for q in reversed(case.data["questions"]) if not q.get("answer")), None)
    if question:
        print("\nQUESTION FOR THE CUSTOMER:\n" + question["question"])
    hold = case.data.get("hold")
    if hold:
        until = f" until {hold['until']}" if hold["until"] else ""
        print(f"\nON HOLD ({hold['status']}{until}):\n" + hold["message"])
    if case.data["referral"]:
        print("\nREFERRED:\n" + json.dumps(case.data["referral"], indent=2, ensure_ascii=False))
    passed = [d for d in case.data["drafts"] if d["passed"]]
    if passed:
        draft = passed[-1]
        print(f"\nVERIFIED DRAFT ({draft['step']}) to {draft['recipient']}\nSubject: {draft['subject']}\n")
        print(draft["body"])
        print("\nNext steps: " + (draft.get("next_steps") or ""))


def main(argv: list | None = None) -> int:
    config.load_env()
    parser = argparse.ArgumentParser(prog="haq")
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new")
    new.add_argument("story")
    new.add_argument("files", nargs="*")
    new.add_argument("--turns", type=int, default=25)
    new.add_argument("--name", default="", help="the customer's name, to sign the complaint")
    add = commands.add_parser("add")
    add.add_argument("case_id")
    add.add_argument("file")
    add.add_argument("--note", default="")
    run = commands.add_parser("run")
    run.add_argument("case_id")
    run.add_argument("--turns", type=int, default=25)
    answer = commands.add_parser("answer")
    answer.add_argument("case_id")
    answer.add_argument("text")
    answer.add_argument("--turns", type=int, default=15)
    commands.add_parser("show").add_argument("case_id")
    args = parser.parse_args(argv)

    if args.command == "show":
        show(Case.load(args.case_id))
        return 0
    client = make_client()
    if args.command == "new":
        case = Case.create(args.story, name=args.name)
        for file in args.files:
            evidence.add(case, Path(file), client)
        print(f"Case {case.id}: {len(case.data['evidence'])} evidence item(s)", file=sys.stderr)
        result = agent.start(case, client, args.turns)
    elif args.command == "add":
        case = Case.load(args.case_id)
        item = evidence.add(case, Path(args.file), client, args.note)
        print(json.dumps({k: item[k] for k in ("id", "kind", "masked", "instruction_like")}, ensure_ascii=False))
        return 0
    elif args.command == "run":
        case = Case.load(args.case_id)
        result = agent.start(case, client, args.turns)
    else:
        case = Case.load(args.case_id)
        open_questions = [q for q in case.data["questions"] if not q.get("answer")]
        if open_questions:
            open_questions[-1]["answer"] = args.text
        case.save()
        result = agent.resume(case, client, f"The customer answered: {args.text}", args.turns)
    print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
    show(Case.load(case.id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
