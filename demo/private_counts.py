"""Bounded literal quantity grammar for the synthetic private demos."""

from __future__ import annotations

import re

WORDS = {
    "cero": 0,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "dieciséis": 16,
    "veinte": 20,
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty": 20,
}
NUMBER = r"\d+(?:\.\d+)?"
WORD_PATTERN = "|".join(re.escape(word) for word in sorted(WORDS, key=len, reverse=True))
COUNT_TOKEN = rf"(?:{NUMBER}|{WORD_PATTERN})"
JOIN = r"(?:o|or|y|and|a|to|/|[-–])"
COUNT_SERIES = rf"(?>{COUNT_TOKEN}(?:\s*{JOIN}\s*{COUNT_TOKEN})*)"
TOKEN = re.compile(rf"\b(?:{COUNT_TOKEN})\b")
ADJACENT_COUNT = re.compile(rf"\b{COUNT_TOKEN}\s+$")
QUALIFIER = re.compile(
    r"(?:\bal\s+menos|\bhasta|\bentre|\bm[aá]s\s+de|\bmenos\s+de|"
    r"\baprox(?:imadamente)?\.?|\bunos?|\bunas?|\bquiz[aá]s|\btal\s+vez|"
    r"\bat\s+least|\bat\s+most|\bup\s+to|\bmore\s+than|\bless\s+than|"
    r"\bbetween|\babout|\baround|\broughly|\bmaybe|\bperhaps)\s+$"
)


def parse_series(series: str) -> list[int]:
    """Parse whole quantities; decimals cannot represent item counts."""
    values = []
    for match in TOKEN.finditer(series):
        token = match.group()
        if token[0].isdigit():
            if "." in token:
                raise ValueError("Cantidad fraccionaria sin respaldo")
            values.append(int(token))
        else:
            values.append(WORDS[token])
    return values


def has_qualifier(text: str, start: int) -> bool:
    """A nearby uncertainty or range qualifier prevents a fixed count."""
    return bool(QUALIFIER.search(text[max(0, start - 35) : start]))


def has_adjacent_count(text: str, start: int) -> bool:
    """A preceding unjoined number word cannot be silently discarded."""
    return bool(ADJACENT_COUNT.search(text[max(0, start - 35) : start]))
