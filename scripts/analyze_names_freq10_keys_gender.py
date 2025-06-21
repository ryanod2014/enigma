#!/usr/bin/env python3
"""
analyze_names_freq10_keys_gender.py
-----------------------------------
Compute collision stats for the key combination (length + F1 + V1 + V2)
across names with frequency >= 10, broken down by gender (m/f/u).

Outputs for each gender:
  • total names
  • unique codes
  • average names per code
  • max names per code
"""
import csv
from collections import defaultdict
from pathlib import Path
from typing import List, Dict

VOWELS = "AEIOUY"
CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}


def first_cat(ch: str) -> int:
    ch = ch.upper()
    for cat, letters in CATEGORY_MAP.items():
        if ch in letters:
            return cat
    return 1


def vowel_pos(word: str) -> List[int]:
    return [i + 1 for i, c in enumerate(word.upper()) if c in VOWELS]


def load_records(path: Path) -> List[Dict]:
    records: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or row[0].startswith("#") or len(row) < 5:
                continue
            name, gender, origin, rank_us, count = row[:5]
            name = name.strip().lower()
            gender = gender.strip().lower() or "u"
            count_val = int(count) if count.isdigit() else 0
            freq = count_val / 10_000.0 if count_val else 0.1
            if freq < 10:
                continue
            if " " in name or all(ch not in VOWELS for ch in name.upper()):
                continue
            vpos = vowel_pos(name)
            v1 = vpos[0] if vpos else 0
            v2 = vpos[1] if len(vpos) > 1 else 0
            rec = {
                "name": name,
                "gender": gender if gender in {"m", "f", "u"} else "u",
                "length": len(name),
                "F1": first_cat(name[0]),
                "V1": v1,
                "V2": v2,
            }
            records.append(rec)
    return records


def compute_stats(records: List[Dict]):
    buckets = defaultdict(list)
    for rec in records:
        key = (rec["length"], rec["F1"], rec["V1"], rec["V2"])
        buckets[key].append(rec["name"])
    sizes = [len(lst) for lst in buckets.values()]
    if not sizes:
        return 0, 0, 0
    avg = sum(sizes) / len(buckets)
    max_size = max(sizes)
    return len(buckets), avg, max_size


def main():
    data_path = Path("data/first_names.tsv")
    if not data_path.exists():
        raise FileNotFoundError(data_path)
    records = load_records(data_path)
    by_gender = {"m": [], "f": [], "u": []}
    for rec in records:
        by_gender[rec["gender"].lower()].append(rec)

    print("Stats for key combo: length + F1 + V1 + V2 (freq>=10 names)\n")
    for g in ["m", "f", "u"]:
        total = len(by_gender[g])
        codes, avg, mx = compute_stats(by_gender[g])
        print(f"Gender {g.upper()} → names: {total}, unique codes: {codes}, avg/code: {avg:.2f}, max/code: {mx}")

if __name__ == "__main__":
    main() 