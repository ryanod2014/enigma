#!/usr/bin/env python3
"""
analyze_names_freq10_keys.py
----------------------------
Analyze key collision stats for first names that have frequency ≥ 10
(count / 10_000) in data/first_names.tsv.

Key combinations analyzed:
1. length + F1 + V1 + V2 + LL
2. length + F1 + V1 + V2
3. F1 + V1 + V2 + LL

Outputs average names per code and max names per code for each combo.
"""
import csv
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Tuple

VOWELS = "AEIOUY"

CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}


def first_letter_category(word: str) -> int:
    ch = word[0].upper()
    for cat, letters in CATEGORY_MAP.items():
        if ch in letters:
            return cat
    return 1


def last_letter_category(word: str) -> int:
    ch = word[-1].upper()
    for cat, letters in CATEGORY_MAP.items():
        if ch in letters:
            return cat
    return 1


def vowel_positions(word: str) -> List[int]:
    return [i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS]


def load_names(path: Path) -> List[str]:
    """Return list of names (str) with freq>=10."""
    names: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 5:
                continue
            name, _, _, _, count = row[:5]
            count_int = int(count) if count.isdigit() else 0
            freq = count_int / 10_000.0 if count_int else 0.1
            if freq >= 10:
                names.append(name.strip().lower())
    return names


def analyze(keys: List[str], records: List[Dict]) -> Tuple[float, int, int]:
    buckets = defaultdict(list)
    for rec in records:
        key = tuple(rec[k] for k in keys)
        buckets[key].append(rec["name"])
    sizes = [len(v) for v in buckets.values()]
    avg = sum(sizes) / len(buckets) if buckets else 0.0
    mx = max(sizes) if sizes else 0
    return avg, mx, len(buckets)


def main():
    data_path = Path("data/first_names.tsv")
    if not data_path.exists():
        raise FileNotFoundError(data_path)

    names = load_names(data_path)

    records: List[Dict] = []
    for n in names:
        vpos = vowel_positions(n)
        v1 = vpos[0] if vpos else 0
        v2 = vpos[1] if len(vpos) > 1 else 0
        rec = {
            "name": n,
            "length": len(n),
            "F1": first_letter_category(n),
            "V1": v1,
            "V2": v2,
            "LL": last_letter_category(n),
        }
        records.append(rec)

    combos = [
        ("length", "F1", "V1", "V2", "LL"),
        ("length", "F1", "V1", "V2"),
        ("F1", "V1", "V2", "LL"),
    ]

    print(f"Total names with freq>=10: {len(names)}")
    for combo in combos:
        avg, mx, num_codes = analyze(list(combo), records)
        print("\nKey combo: " + " + ".join(combo))
        print(f"  Unique codes: {num_codes}")
        print(f"  Avg names per code: {avg:.2f}")
        print(f"  Max names for any code: {mx}")

if __name__ == "__main__":
    main() 