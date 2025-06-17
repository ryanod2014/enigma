#!/usr/bin/env python3
"""build_first_names.py
Download the U.S. Social Security Administration baby-names corpus and
generate `data/first_names.tsv` used by `first_name_index.py`.

The TSV columns are:
    name\tgender\torigin\trank_us\ttotal_count

• A name appears for each **distinct spelling** across all years 1880-present.
• `gender` rules:
      if male_count == 0            → "f"
      elif female_count == 0        → "m"
      elif max_ratio >= 10:1        → "m" / "f" (majority gender)
      else                          → "u"  (unisex)
• `origin` column is always "US" (may be broadened later).
• `rank_us` is by total_count desc (1-based).

Usage:
    python scripts/build_first_names.py   # writes data/first_names.tsv
"""
from __future__ import annotations

import csv
import io
import os
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple
import argparse

import requests
from tqdm import tqdm

SSA_URL = "https://www.ssa.gov/oact/babynames/names.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_PATH = DATA_DIR / "first_names.tsv"


def download_zip(url: str) -> bytes:
    """Return bytes of remote ZIP (streaming download)."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; EnigmaBot/1.0)"}
    r = requests.get(url, stream=True, timeout=30, headers=headers)
    if r.status_code == 403:
        raise RuntimeError("SSA site blocked automated download (HTTP 403). Please download 'names.zip' from https://www.ssa.gov/oact/babynames/ and place it in the project root, then rerun this script with --local /path/to/names.zip")
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0))
    buf = io.BytesIO()
    pbar = tqdm(total=total, unit="B", unit_scale=True, desc="download")
    for chunk in r.iter_content(chunk_size=8192):
        buf.write(chunk)
        pbar.update(len(chunk))
    pbar.close()
    r.close()
    buf.seek(0)
    return buf.read()


def aggregate_counts(zip_bytes: bytes) -> Dict[str, Tuple[int, int]]:
    """Return name → (male_count, female_count)."""
    counts: Dict[str, Tuple[int, int]] = defaultdict(lambda: [0, 0])  # type: ignore
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for txt in zf.namelist():
            if not txt.startswith("yob") or not txt.endswith(".txt"):
                continue
            with zf.open(txt) as f:
                for line in f.read().decode().splitlines():
                    name, sex, cnt = line.strip().split(",")
                    cnt_i = int(cnt)
                    rec = counts[name.lower()]
                    if sex == "M":
                        rec[0] += cnt_i  # type: ignore[index]
                    else:
                        rec[1] += cnt_i  # type: ignore[index]
    # convert lists to tuples
    return {n: (m, f) for n, (m, f) in counts.items()}


def classify_gender(m: int, f: int) -> str:
    if m == 0:
        return "f"
    if f == 0:
        return "m"
    # majority threshold 10:1
    if m >= f * 10:
        return "m"
    if f >= m * 10:
        return "f"
    return "u"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build first_names.tsv from SSA dataset")
    parser.add_argument("--local", help="Path to pre-downloaded names.zip", default=None)
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    if args.local:
        print(f"[builder] reading local zip {args.local}…")
        zip_data = Path(args.local).read_bytes()
    else:
        print("[builder] downloading SSA names…")
        zip_data = download_zip(SSA_URL)

    print("[builder] parsing & aggregating…")
    counts = aggregate_counts(zip_data)

    print("[builder] ranking…")
    ranked = sorted(counts.items(), key=lambda kv: kv[1][0] + kv[1][1], reverse=True)

    print(f"[builder] writing {OUT_PATH}…")
    with OUT_PATH.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f, delimiter="\t")
        for rank, (name, (m_cnt, f_cnt)) in enumerate(ranked, 1):
            gender = classify_gender(m_cnt, f_cnt)
            total = m_cnt + f_cnt
            writer.writerow([name, gender, "US", rank, total])

    print("[builder] done –", len(ranked), "unique names written")


if __name__ == "__main__":
    main() 