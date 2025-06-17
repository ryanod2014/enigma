#!/usr/bin/env python3
"""generate_country_keys.py
Generate a CSV summarising the (letters, category, V1, V2) key for each country in a fixed list.

Usage:
    python scripts/generate_country_keys.py > country_keys.csv
"""
import csv
import re
import sys
from typing import Dict, List, Tuple

VOWELS = "AEIOUY"

# Must stay in sync with `wordnet_vowel_index.CATEGORY_MAP`
CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},  # J & U intentionally overlap
    3: {"B", "D", "P", "R", "J", "U"},       # J & U intentionally overlap
}

STAR_SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


def _normalize(name: str) -> str:
    """Remove non-letters and return uppercase string."""
    return re.sub(r"[^A-Za-z]", "", name).upper()


def _first_category(letter: str) -> int:
    """Return the first (lowest) bucket number containing *letter*."""
    for cat in (1, 2, 3):
        if letter in CATEGORY_MAP[cat]:
            return cat
    raise ValueError(f"Letter {letter!r} missing from CATEGORY_MAP")


def _vowel_positions(word: str) -> List[int]:
    """Return 1-based indices of vowels in *word*."""
    return [idx + 1 for idx, ch in enumerate(word) if ch in VOWELS]


def main() -> None:
    groups: Dict[Tuple[int, int, int], List[str]] = {}

    for sign in STAR_SIGNS:
        clean = _normalize(sign)
        if not clean:
            continue  # skip if name had no letters somehow

        first_cat = _first_category(clean[0])
        last_cat = _first_category(clean[-1])
        vpos = _vowel_positions(clean)
        v1 = vpos[0] if vpos else 0

        key = (first_cat, v1, last_cat)
        groups.setdefault(key, []).append(sign)

    writer = csv.writer(sys.stdout)
    writer.writerow(["V1", "last_category", "star_signs"])
    for (first_cat, v1, last_cat), names in sorted(groups.items()):
        writer.writerow([v1, last_cat, "|".join(names)])


if __name__ == "__main__":
    main() 