#!/usr/bin/env python3
"""
show_names_freq10.py
--------------------
Outputs all first names in data/first_names.tsv with freq >= 10
(where freq = count/10_000 according to main.py logic). No 'common' filter applied.
Saves CSV to stdout or to a file if --out filepath is provided.
"""
import csv
import argparse
from pathlib import Path

VOWELS = "AEIOUY"

def load_names(path: Path):
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 5:
                continue
            name, gender, origin, rank_us, count = row[:5]
            yield {
                "name": name.strip().lower(),
                "gender": gender.strip().lower() if gender else "u",
                "origin": origin.strip().upper() if origin else "",
                "rank_us": int(rank_us) if rank_us.isdigit() else 0,
                "count": int(count) if count.isdigit() else 0,
            }


def main():
    parser = argparse.ArgumentParser(description="Export names with freq>=10 as CSV")
    parser.add_argument("--out", help="Output CSV file path", default=None)
    args = parser.parse_args()

    data_path = Path("data/first_names.tsv")
    if not data_path.exists():
        raise FileNotFoundError(data_path)

    rows = []
    for rec in load_names(data_path):
        # Skip multi-word or no-vowel names
        if " " in rec["name"] or not any(ch in VOWELS for ch in rec["name"].upper()):
            continue
        freq = rec["count"] / 10_000.0 if rec["count"] else 0.1
        if freq >= 10:
            rec["freq"] = round(freq, 1)
            rows.append(rec)

    # Sort by freq descending
    rows.sort(key=lambda r: r["freq"], reverse=True)

    header = ["rank", "name", "gender", "origin", "rank_us", "count", "freq"]
    output_lines = [" ".join(header)]  # placeholder; we'll build CSV string

    out_csv_lines = [",".join(header)]
    for idx, r in enumerate(rows, 1):
        out_csv_lines.append(
            f"{idx},{r['name']},{r['gender']},{r['origin']},{r['rank_us']},{r['count']},{r['freq']}"
        )

    csv_text = "\n".join(out_csv_lines)

    if args.out:
        Path(args.out).write_text(csv_text, encoding="utf-8")
    else:
        print(csv_text)

if __name__ == "__main__":
    main() 