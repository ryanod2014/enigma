#!/usr/bin/env python3
"""Export city codes (length, F1, V1, LL) for the top 100 cities.
Outputs CSV with columns: code, city, country, region"""
import csv
from pathlib import Path
from typing import List, Dict

VOWELS = "AEIOUY"
CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}


def category(ch: str) -> int:
    ch = ch.upper()
    for cat, letters in CATEGORY_MAP.items():
        if ch in letters:
            return cat
    return 1


def first_vowel_pos(word: str) -> int:
    for i, ch in enumerate(word.upper(), 1):
        if ch in VOWELS:
            return i
    return 0


def load_top_cities(path: Path, limit: int = 100) -> List[Dict]:
    data = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            data.append(row)
    return data


def main():
    src = Path("wiki_top_cities_final.csv")
    if not src.exists():
        print("Error: wiki_top_cities_final.csv not found")
        return

    rows = load_top_cities(src, 100)

    # Build buckets and calculate popularity score (higher rank = bigger score)
    buckets: Dict[str, List[Dict]] = {}
    scores: Dict[str, int] = {}
    for idx, row in enumerate(rows, 1):
        city = row.get("city") or row.get("City") or row.get("name")
        country = row.get("country") or row.get("Country") or ""
        region = row.get("region") or row.get("Region") or ""

        clean = city.replace(" ", "").replace("-", "")
        length = len(clean)
        F1 = category(city[0])
        V1 = first_vowel_pos(city)
        LL = category(city[-1])
        code = f"({length},{F1},{V1},{LL})"

        buckets.setdefault(code, []).append({
            "city": city,
            "country": country,
            "region": region,
            "code": code
        })
        # Popularity weight: inverse rank (top city gets 100, etc.)
        weight = 101 - idx  # idx 1 => 100, idx 100 => 1
        scores[code] = scores.get(code, 0) + weight

    # Sort codes by combined popularity score DESC, then code string
    sorted_codes = sorted(buckets.keys(), key=lambda c: (-scores[c], c))

    print("code,city,country,region")
    for code in sorted_codes:
        for rec in buckets[code]:
            print(f"{code},{rec['city']},{rec['country']},{rec['region']}")

if __name__ == "__main__":
    main() 