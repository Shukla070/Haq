"""Rupee amounts written as words, from voice transcripts.

Transcripts arrive as words ("four thousand five hundred", "saadhe chaar
hazaar", "चार हज़ार"), which digit-only matching would miss. This module
finds those phrases and returns plain digit strings ("4500").

A phrase counts only with a magnitude word (thousand, lakh, sau, hazaar,
...) or a currency word right next to it (rupees, rupaye, rs, ...), so
"teen din pehle" or "12 October" give nothing. Digit-only amounts
("Rs 4,500") are handled elsewhere and ignored here, as are paise.
"""

from __future__ import annotations

import math
import re

_DEV_DIGITS = "०१२३४५६७८९"
# The Devanagari block, minus the danda and double danda (U+0964, U+0965): Hindi
# transcripts end sentences with them, glued to the last word ("सौ।").
_DEV_BLOCK = "".join(chr(c) for c in range(0x0900, 0x0980) if c not in (0x0964, 0x0965))
_SYMBOLS = chr(0x20B9) + "$£€¥"  # ₹ first
_TOKEN = re.compile(
    "[0-9][0-9,]*(?:[.][0-9]+)?|[" + _DEV_DIGITS + "]+(?:,[" + _DEV_DIGITS + "]+)*"
    "|[A-Za-z]+|[" + _DEV_BLOCK + "]+|[" + _SYMBOLS + "]"
)

# Token kinds: plain number, magnitude, fraction, currency, paise, foreign currency
# (blocks a phrase), glue ("and"), anything else (breaks a phrase).
_NUM, _SCALE, _FRAC, _CURR, _PAISE, _BLOCK, _GLUE, _OTHER = (
    "num", "scale", "frac", "curr", "paise", "block", "glue", "other"
)
_RUNNABLE = frozenset({_NUM, _SCALE, _FRAC, _GLUE})

_NUMBERS: dict[str, float] = {
    "a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}

# Hindi 1-99 in Latin script with common spellings. saat is 7, saath is 60;
# "sath" (with) and "no" (the English word) are left out on purpose.
_HINDI = [
    (1, "ek ik"), (2, "do"), (3, "teen tin"), (4, "char chaar caar"),
    (5, "paanch panch paach"), (6, "chhah chah chhe chha che"), (7, "saat"),
    (8, "aath ath"), (9, "nau nao"), (10, "das dus"),
    (11, "gyarah gyara gyaarah"), (12, "barah bara baarah"), (13, "terah tera"),
    (14, "chaudah chauda chodah"), (15, "pandrah pandra"), (16, "solah sola"),
    (17, "satrah satra"), (18, "atharah athara athaarah"), (19, "unnis unnis"),
    (20, "bees bis"), (21, "ikkees ikkis"), (22, "baees bais baaees"),
    (23, "teis taees"), (24, "chaubees chaubis"),
    (25, "pachees pachis pacchees pachees"), (26, "chhabbees chhabbis"),
    (27, "sattais satais sattaaees"), (28, "atthais athais atthaaees"),
    (29, "untees untis"), (30, "tees tis"), (31, "iktees iktis"),
    (32, "battees battis"), (33, "taintees taintis"), (34, "chauntees chauntis"),
    (35, "paintees paintis"), (36, "chhattees chhattis"), (37, "saintees saintis"),
    (38, "adtees adtis"), (39, "untalis untaalis"), (40, "chalis chalees"),
    (41, "iktalis ektalis iktaalis"), (42, "bayalis bealis bayaalis"),
    (43, "taintalis tetalis taintaalis"), (44, "chavalis chauvalis chavaalis"),
    (45, "paintalis paitalis paintaalis"), (46, "chhiyalis chayalis chhiyaalis"),
    (47, "saintalis saitalis saintaalis"), (48, "adtalis adtaalis"),
    (49, "unchas unchaas"), (50, "pachaas pachas"),
    (51, "ikyavan ekyavan ikyaavan"), (52, "baavan bavan"), (53, "tirpan tirepan"),
    (54, "chauvan chauwan"), (55, "pachpan pachapan"), (56, "chhappan chhapan"),
    (57, "sattavan satawan sattaavan"), (58, "atthavan athawan atthaavan"),
    (59, "unsath unsath"), (60, "saath"), (61, "iksath eksath"),
    (62, "basath baisath baasath"), (63, "tresath tirsath"),
    (64, "chausath chousath chaunsath"), (65, "painsath paisath"),
    (66, "chhiyasath chhayasath chhiyaasath"), (67, "sadsath sarsath"),
    (68, "adsath athsath arsath"), (69, "unhattar unhattar"), (70, "sattar"),
    (71, "ikhattar ekhattar"), (72, "bahattar"), (73, "tihattar tehattar"),
    (74, "chauhattar"), (75, "pachhattar pachattar"),
    (76, "chhihattar chhahattar"), (77, "sattahattar sattattar satattar"),
    (78, "atthahattar atthattar athattar"), (79, "unasi unaasi"),
    (80, "assi asi"), (81, "ikyaasi ekyaasi ikasi"), (82, "bayaasi bayasi beasi"),
    (83, "tiraasi tirasi teyaasi"), (84, "chauraasi chaurasi chaurasi"),
    (85, "pachaasi pachasi"), (86, "chhiyaasi chhiyasi chhayaasi"),
    (87, "sattaasi sattasi sataasi"), (88, "atthaasi atthasi athaasi"),
    (89, "navaasi navasi"), (90, "nabbe nave"),
    (91, "ikyaanve ikyanve ekyanve"), (92, "baanve banve"),
    (93, "tiraanve tiranve"), (94, "chauraanve chauranve"),
    (95, "pachaanve pachanve panchanve"), (96, "chhaanve chhiyanve"),
    (97, "sataanve sattanve"), (98, "athaanve atthanve"),
    (99, "ninyaanve ninyanve"),
]
_NUMBERS.update({word: value for value, words in _HINDI for word in words.split()})

# Same table in Devanagari, as _fold leaves it (plain letters, no nukta),
# so each spelling matches whatever codepoints the transcriber used.
_DEVANAGARI = [
    (1, "एक"), (2, "दो"), (3, "तीन"), (4, "चार"), (5, "पांच पाँच"),
    (6, "छह"), (7, "सात"), (8, "आठ"), (9, "नौ"), (10, "दस"),
    (11, "ग्यारह"), (12, "बारह"), (13, "तेरह"), (14, "चौदह"),
    (15, "पंद्रह पन्द्रह"), (16, "सोलह"), (17, "सत्रह"), (18, "अठारह"),
    (19, "उन्नीस"), (20, "बीस"), (21, "इक्कीस"), (22, "बाईस"),
    (23, "तेईस"), (24, "चौबीस"), (25, "पच्चीस"), (26, "छब्बीस"),
    (27, "सत्ताईस सत्ताइस"), (28, "अट्ठाईस अट्ठाइस"), (29, "उनतीस"),
    (30, "तीस"), (31, "इकतीस"), (32, "बत्तीस"), (33, "तैंतीस"),
    (34, "चौंतीस"), (35, "पैंतीस"), (36, "छत्तीस"), (37, "सैंतीस"),
    (38, "अदतीस"), (39, "उनतालीस"), (40, "चालीस"), (41, "इकतालीस"),
    (42, "बयालीस"), (43, "तैंतालीस"), (44, "चवालीस"), (45, "पैंतालीस"),
    (46, "छियालीस"), (47, "सैंतालीस"), (48, "अदतालीस"), (49, "उनचास"),
    (50, "पचास"), (51, "इक्यावन"), (52, "बावन"), (53, "तिरपन"),
    (54, "चौवन"), (55, "पचपन"), (56, "छप्पन"), (57, "सत्तावन"),
    (58, "अट्ठावन"), (59, "उनसठ"), (60, "साठ"), (61, "इकसठ"),
    (62, "बासठ"), (63, "तिरसठ"), (64, "चौंसठ"), (65, "पैंसठ"),
    (66, "छियासठ"), (67, "सदसठ"), (68, "अदसठ"), (69, "उनहत्तर"),
    (70, "सत्तर"), (71, "इकहत्तर"), (72, "बहत्तर"), (73, "तिहत्तर"),
    (74, "चौहत्तर"), (75, "पचहत्तर"), (76, "छिहत्तर"),
    (77, "सत्तहत्तर सत्ततर"), (78, "अट्ठहत्तर"), (79, "उन्यासी"),
    (80, "अस्सी"), (81, "इक्यासी"), (82, "बयासी"), (83, "तिरासी"),
    (84, "चौरासी"), (85, "पचासी"), (86, "छियासी"), (87, "सत्तासी"),
    (88, "अट्ठासी"), (89, "नवासी"), (90, "नब्बे"), (91, "इक्यानवे"),
    (92, "बानवे"), (93, "तिरानवे"), (94, "चौरानवे"), (95, "पचानवे"),
    (96, "छियानवे"), (97, "सत्तानवे"), (98, "अट्ठानवे"), (99, "निन्यानवे"),
]
_NUMBERS.update({word: value for value, words in _DEVANAGARI for word in words.split()})

# No "hundreds"/"thousands": vague plurals ("hundreds of people") are not amounts.
_SCALES = {
    "hundred": 100, "thousand": 1000,
    "lakh": 100000, "lakhs": 100000, "laakh": 100000,
    "lac": 100000, "lacs": 100000,
    "crore": 10000000, "crores": 10000000, "karod": 10000000, "karor": 10000000,
    "sau": 100, "sao": 100,
    "hazaar": 1000, "hazar": 1000, "hajar": 1000, "hajaar": 1000,
    "सौ": 100, "हजार": 1000, "लाख": 100000, "करोड": 10000000,
}

# Fractions: ("add", x) shifts the next number, or 1; ("abs", x) stands alone.
_FRACTIONS = {
    "saadhe": ("add", 0.5), "sadhe": ("add", 0.5), "saade": ("add", 0.5),
    "sava": ("add", 0.25), "sawa": ("add", 0.25), "sawaa": ("add", 0.25),
    "paune": ("add", -0.25), "pone": ("add", -0.25), "pauna": ("add", -0.25),
    "dedh": ("abs", 1.5), "derh": ("abs", 1.5),
    "dhai": ("abs", 2.5), "dhaai": ("abs", 2.5), "adhai": ("abs", 2.5),
    "aadha": ("abs", 0.5), "adha": ("abs", 0.5),
    "साढे": ("add", 0.5), "सवा": ("add", 0.25), "पौने": ("add", -0.25),
    "डेढ": ("abs", 1.5), "डेढ्": ("abs", 1.5), "ढाई": ("abs", 2.5),
}

_CURRENCY = frozenset({
    "rupee", "rupees", "rupay", "rupaye", "rupaiya", "rupaiye", "rs", "inr", "₹",
    "रुपये", "रुपए", "रुपया", "रु",
})
_PAISE_WORDS = frozenset({"paise", "paisa", "पैसे", "पैसा"})
_BLOCK_WORDS = frozenset({
    "dollar", "dollars", "pound", "pounds", "euro", "euros", "yen",
    "$", "£", "€", "¥",
})
_GLUE_WORDS = frozenset({"and"})

# Nukta letters to plain ones, chandrabindu to anusvara: हज़ार and हजार,
# पाँच and पांच, साढ़े and साढे are looked up as one spelling each.
_FOLD = str.maketrans({
    chr(0x0901): "ं",
    chr(0x0958): "क", chr(0x0959): "ख", chr(0x095A): "ग", chr(0x095B): "ज",
    chr(0x095C): "ड", chr(0x095D): "ढ", chr(0x095E): "फ", chr(0x095F): "य",
})
_NUKTA = chr(0x093C)


def _fold(word: str) -> str:
    return word.translate(_FOLD).replace(_NUKTA, "")


def _tokenize(text: str) -> list:
    """Words, numbers and currency symbols; punctuation is skipped."""
    tokens = []
    for match in _TOKEN.finditer(text.lower()):
        raw = match.group(0)
        if raw[0] in "0123456789":
            tokens.append((_NUM, float(raw.replace(",", "")), "digit"))
        elif raw[0] in _DEV_DIGITS:
            value = int("".join(str(_DEV_DIGITS.index(c)) for c in raw if c != ","))
            tokens.append((_NUM, float(value), "dev"))
        else:
            word = _fold(raw)
            if word in _NUMBERS:
                tokens.append((_NUM, _NUMBERS[word], "a" if word == "a" else "word"))
            elif word in _SCALES:
                tokens.append((_SCALE, _SCALES[word], ""))
            elif word in _FRACTIONS:
                tokens.append((_FRAC, _FRACTIONS[word], ""))
            elif word in _CURRENCY:
                tokens.append((_CURR, 0, ""))
            elif word in _PAISE_WORDS:
                tokens.append((_PAISE, 0, ""))
            elif word in _BLOCK_WORDS:
                tokens.append((_BLOCK, 0, ""))
            elif word in _GLUE_WORDS:
                tokens.append((_GLUE, 0, ""))
            else:
                tokens.append((_OTHER, 0, ""))
    return tokens


def _runs(tokens: list) -> list:
    """Maximal number-phrase runs with the token kind on each side. A fraction
    starts a new run once the run already has a number or a scale."""
    runs = []
    index, end = 0, len(tokens)
    while index < end:
        if tokens[index][0] not in _RUNNABLE:
            index += 1
            continue
        run = [tokens[index]]
        next_index = index + 1
        while next_index < end and tokens[next_index][0] in _RUNNABLE and not (
            tokens[next_index][0] == _FRAC and any(t[0] in (_NUM, _SCALE) for t in run)
        ):
            run.append(tokens[next_index])
            next_index += 1
        prev = tokens[index - 1][0] if index > 0 else _OTHER
        following = tokens[next_index][0] if next_index < end else _OTHER
        runs.append((run, prev, following))
        index = next_index
    return runs


def _resolve(tokens: list) -> list:
    """Glue dropped, fractions and "a" resolved to plain num/scale tokens."""
    toks = [t for t in tokens if t[0] != _GLUE]
    # "a" counts as one only before a magnitude word ("a hundred", not "a month").
    toks = [t for n, t in enumerate(toks) if t[2] != "a" or (n + 1 < len(toks) and toks[n + 1][0] == _SCALE)]
    resolved = []
    seen, index = False, 0
    while index < len(toks):
        kind, value, _ = toks[index]
        if kind == _FRAC and not seen:
            mode, amount = value
            if mode == "abs":
                resolved.append((_NUM, amount))
            elif index + 1 < len(toks) and toks[index + 1][0] == _NUM:
                resolved.append((_NUM, toks[index + 1][1] + amount))
                index += 1
            else:
                resolved.append((_NUM, 1 + amount))
            seen = True
        elif kind in (_NUM, _SCALE):
            resolved.append((kind, value))
            seen = True
        index += 1
    return resolved


def _value(tokens: list) -> float:
    total, current = 0.0, 0.0
    for kind, value in tokens:
        if kind == _NUM:
            current += value
        elif value == 100:
            current = (current or 1) * 100
        else:
            total += (current or 1) * value
            current = 0.0
    return total + current


def spoken_amounts(text: str) -> set[str]:
    """Rupee amounts written in words, as plain digit strings ("4500")."""
    found = set()
    for run, prev, following in _runs(_tokenize(text or "")):
        if following == _BLOCK:
            continue  # foreign currency, not rupees
        if following == _PAISE and not any(t[0] == _SCALE and t[1] >= 1000 for t in run):
            continue  # "pachaas paise" is paise; "chaar hazaar paise" is Hinglish for Rs 4,000
        nums = [t for t in run if t[0] == _NUM]
        if len(run) == 1 and nums and nums[0][2] == "dev":
            if nums[0][1] > 0:  # bare Devanagari digits, e.g. ४,५००
                found.add(str(int(nums[0][1])))
            continue
        if not any(t[0] in (_SCALE, _FRAC) or (t[0] == _NUM and t[2] in ("word", "dev")) for t in run):
            continue  # digits only: handled elsewhere ("Rs 4,500", "12 October")
        if not any(t[0] == _SCALE for t in run) and prev != _CURR and following != _CURR:
            continue  # needs a magnitude or a currency word right next to it
        amount = _value(_resolve(run))
        rounded = round(amount)
        final = rounded if abs(amount - rounded) < 1e-6 else math.floor(amount)
        if final > 0:
            found.add(str(final))
    return found
