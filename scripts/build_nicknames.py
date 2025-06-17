#!/usr/bin/env python3
"""build_nicknames.py
Merge several public-domain nickname datasets into a TSV file used by
FirstNameIndex to mark names that have common abbreviations.

Output: data/nicknames_full.tsv – canonical<TAB>nick1,nick2,…

Currently pulls:
    • https://raw.githubusercontent.com/arineng/ardict/master/resources/nicknames.csv
      ( ~8 k rows, MIT licence )
You can add more sources by appending to SOURCES.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
import requests
from tqdm import tqdm
import argparse

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_FILE = DATA_DIR / "nicknames_full.tsv"

SOURCES = {
    "arineng": "https://raw.githubusercontent.com/arineng/ardict/master/resources/nicknames.csv",
}


def download_csv(url: str) -> list[tuple[str, list[str]]]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EnigmaBot/1.0)"}
    r = requests.get(url, timeout=30, headers=headers)
    r.raise_for_status()
    rows = []
    for line in io.StringIO(r.text):
        parts = [p.strip() for p in line.strip().split(",") if p.strip()]
        if not parts:
            continue
        canonical, *nicks = parts
        if canonical:
            rows.append((canonical.lower(), [n.lower() for n in nicks]))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build nicknames_full.tsv")
    parser.add_argument("--local", help="Path to local CSV file with canonical,nick1,nick2 …", default=None)
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    merged: dict[str, set[str]] = {}

    # local file first
    if args.local:
        print(f"[nick] loading local file {args.local}…")
        with open(args.local, 'r', encoding='utf-8') as f:
            for line in f:
                parts = [p.strip() for p in line.strip().split(",") if p.strip()]
                if not parts:
                    continue
                canonical, *nicks = parts
                if canonical:
                    merged.setdefault(canonical.lower(), set()).update(n.lower() for n in nicks)

    # Skip network downloads if we have local data
    if not args.local:
        for name, url in SOURCES.items():
            print(f"[nick] downloading {name}…")
            for canonical, nicks in download_csv(url):
                bucket = merged.setdefault(canonical, set())
                bucket.update(nicks)

    # Deduplicate nicknames and remove self-references
    print("[nick] writing TSV…")
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        for canonical, nick_set in sorted(merged.items()):
            if canonical in nick_set:
                nick_set.remove(canonical)
            if not nick_set:
                continue
            w.writerow([canonical, ",".join(sorted(nick_set))])

    print("[nick] done –", len(merged), "formal names written →", OUT_FILE)


if __name__ == "__main__":
    main() 