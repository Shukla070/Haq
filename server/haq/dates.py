"""Finds the dates a piece of text mentions, so code can check that a date the agent uses
came from the evidence or the customer and was not guessed.

Dates are compared by day and month only: statements, SMS and people write the year in
many ways or leave it out. Indian order (day before month) is assumed for numeric dates.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    # Hindi, in Latin letters and Devanagari, as voice notes and chats write them
    "janvari": 1, "farvari": 2, "march": 3, "aprail": 4, "mai": 5, "joon": 6, "julai": 7, "agast": 8,
    "sitambar": 9, "aktubar": 10, "aktoobar": 10, "navambar": 11, "disambar": 12,
    "जनवरी": 1, "फरवरी": 2, "फ़रवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7,
    "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10, "अक्तूबर": 10, "नवंबर": 11, "नवम्बर": 11,
    "दिसंबर": 12, "दिसम्बर": 12,
}
_MONTH = "|".join(sorted((re.escape(m) for m in _MONTHS), key=len, reverse=True))
_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"

_NUMERIC = re.compile(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})(?!\d)")
_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_DAY_MONTH = re.compile(rf"(?<![\w]){_DAY}\s*(?:of\s+|tarikh\s+|तारीख\s+)?[-,]?\s*({_MONTH})(?![a-z])", re.IGNORECASE)
_MONTH_DAY = re.compile(rf"(?<![\w])({_MONTH})\.?\s+{_DAY}(?!\d)", re.IGNORECASE)
_TODAY = re.compile(r"\b(today|aaj|abhi|this morning|tonight)\b|आज", re.IGNORECASE)
_YESTERDAY = re.compile(r"\b(yesterday|last night|kal raat|kal)\b|कल", re.IGNORECASE)
_DAY_BEFORE = re.compile(r"\b(day before yesterday|parso|parson)\b|परसों", re.IGNORECASE)


def _add(found: set, day: int, month: int) -> None:
    if 1 <= day <= 31 and 1 <= month <= 12:
        found.add((month, day))


def mentioned(text: str, today: date) -> set:
    """(month, day) pairs the text mentions, including today and yesterday when it says so."""
    found: set = set()
    text = text or ""
    for day, month, _ in _NUMERIC.findall(text):
        _add(found, int(day), int(month))
    for _, month, day in _ISO.findall(text):
        _add(found, int(day), int(month))
    for day, month in _DAY_MONTH.findall(text):
        _add(found, int(day), _MONTHS[month.lower()])
    for month, day in _MONTH_DAY.findall(text):
        _add(found, int(day), _MONTHS[month.lower()])
    for pattern, back in ((_TODAY, 0), (_YESTERDAY, 1), (_DAY_BEFORE, 2)):
        if pattern.search(text):
            then = today - timedelta(days=back)
            found.add((then.month, then.day))
    return found


def supported(day: date, texts: list, today: date) -> bool:
    """Whether any of the texts mentions this day."""
    return any((day.month, day.day) in mentioned(text, today) for text in texts)
