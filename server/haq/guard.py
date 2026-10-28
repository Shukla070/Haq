"""Checks that run in code, outside the model's control: masking sensitive numbers in
evidence text, spotting text in evidence that tries to instruct the agent, and finding
sensitive numbers in outgoing drafts.

Masking is deliberately narrow. UPI references (UTR/RRN) are also 12 digits, so a bare
12-digit number is only treated as Aadhaar when it is written 4-4-4 or labelled as
Aadhaar; references must survive, because complaints need them.
"""

from __future__ import annotations

import re

_AADHAAR_SPACED = re.compile(r"(?<!\d)(\d{4})[ -](\d{4})[ -](\d{4})(?![ -]?\d)")
_AADHAAR_LABELLED = re.compile(
    r"(?i)(aadhaa?r|\bUID\b)(\D{0,20}?)(\d{4}[ -]?\d{4}[ -]?\d{4})(?!\d)"
)
_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_OTP = re.compile(r"(?i)\b(OTP|one[- ]time password)(\D{0,25}?)(\d{4,8})\b")
_CVV = re.compile(r"(?i)\b(CVV2?|CVC)(\D{0,10}?)(\d{3,4})\b")


def _luhn(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def _last4(number: str) -> str:
    return re.sub(r"\D", "", number)[-4:]


def _mask_card(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if 13 <= len(digits) <= 19 and _luhn(digits):
        return "[CARD XXXX" + digits[-4:] + "]"
    return match.group(0)


def mask_sensitive(text: str) -> str:
    """The text with Aadhaar, card numbers, OTPs and CVVs masked."""
    text = _OTP.sub(lambda m: f"{m.group(1)}{m.group(2)}[OTP MASKED]", text)
    text = _CVV.sub(lambda m: f"{m.group(1)}{m.group(2)}[CVV MASKED]", text)
    text = _AADHAAR_LABELLED.sub(
        lambda m: f"{m.group(1)}{m.group(2)}[AADHAAR XXXX{_last4(m.group(3))}]", text
    )
    text = _CARD.sub(_mask_card, text)
    text = _AADHAAR_SPACED.sub(lambda m: f"[AADHAAR XXXX{m.group(3)}]", text)
    return text


def sensitive_numbers(text: str) -> list:
    """Sensitive numbers still visible in text, for blocking outgoing drafts."""
    found = []
    for match in _CARD.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            found.append("card number ending " + digits[-4:])
    if _AADHAAR_SPACED.search(text) or _AADHAAR_LABELLED.search(text):
        found.append("Aadhaar number")
    if _OTP.search(text):
        found.append("OTP")
    if _CVV.search(text):
        found.append("CVV")
    return found


_INSTRUCTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|rules|messages)",
    r"disregard (all |any )?(the )?(previous|prior|above|your) (instructions|rules)",
    r"you are (now )?(an? )?(ai|assistant|agent|language model|chatbot)",
    r"(as|dear) (an? )?(ai|assistant|agent|language model)",
    r"system prompt",
    r"new instructions",
    r"do not (file|send|draft|submit) (a |the |any )?(complaint|draft)",
    r"(mark|treat) (this|the) (case|complaint|claim) as (closed|resolved|invalid|withdrawn)",
    r"(tell|inform) the (user|customer) (that|to)",
]
_INSTRUCTIONS = re.compile("|".join(_INSTRUCTION_PATTERNS), re.IGNORECASE)


def instruction_like(text: str) -> list:
    """Phrases in evidence that read as instructions to an AI agent."""
    return sorted({match.group(0) for match in _INSTRUCTIONS.finditer(text or "")})
