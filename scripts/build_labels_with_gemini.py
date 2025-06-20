import os
import json
import csv
import time
import argparse
from pathlib import Path
from typing import List, Dict

import google.generativeai as genai

# --------------------------------------------------------------------------- #
#  Batch-label 20-Questions subjects with Gemini 2-flash
# --------------------------------------------------------------------------- #
#  • Reads the master subject list from data/combined_twentyquestions.jsonl
#  • Sends batches of 100 words to Gemini-flash 2.0 and asks for labels along
#    three dimensions: origin, size, primary category.
#  • Appends results to data/thing_labels.tsv so the run is resumable.
#
#  USAGE
#    python scripts/build_labels_with_gemini.py          # labels first 100
#    python scripts/build_labels_with_gemini.py --all    # labels everything
#    python scripts/build_labels_with_gemini.py --limit 500
#
#  Gemini pricing: ~0.0001 USD / 1K tokens → full run (<10K words) costs cents.
# --------------------------------------------------------------------------- #

# TODO – Set your temporary Gemini API key here, then delete after run ↓↓↓
API_KEY = "AIzaSyDukbzEET7BdVEyd2HcIUwgQnDrC5ftdyM"

assert API_KEY and API_KEY != "PASTE_YOUR_GEMINI_KEY_HERE", (
    "Set your Gemini API key in build_labels_with_gemini.py before running."
)

genai.configure(api_key=API_KEY)

MODEL_NAME = "models/gemini-2.0-flash"  # 2-flash alias
BATCH_SIZE = 100
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "thing_labels.tsv"
SUBJECTS_FILE = Path(__file__).resolve().parent.parent / "data" / "combined_twentyquestions.jsonl"

DIMENSION_SPEC = (
    "origin: man-made | natural | both\n"
    "size: fits-in-backpack | too-big-for-backpack | size-varies\n"
    "category: animal | person | food | plant | vehicle | tool | electronics |"
    " household | clothing | place | abstract | other\n"
)

SYSTEM_PROMPT = (
    "You are a meticulous taxonomist helping with the 20 Questions game. "
    "For every English noun provided you must assign three labels exactly as "
    "defined below. Respond strictly as JSON array. Do not add keys.\n\n" + DIMENSION_SPEC
)

USER_PROMPT_TEMPLATE = (
    "Label the following words. Return JSON array of objects with keys "
    "'word', 'origin', 'size', 'category'. ONE line JSON, no markdown.\n\n" +
    "Words: {words}"
)

def load_subject_list() -> List[str]:
    """Read unique subjects from the combined JSONL dataset (≈9.8K)."""
    subjects: List[str] = []
    seen = set()
    with SUBJECTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (obj.get("word") or obj.get("subject") or "").strip()
            if word and word not in seen:
                seen.add(word)
                subjects.append(word)
    return subjects


def load_done_set() -> set[str]:
    """Return set of words already present in OUTPUT_FILE (if any)."""
    done = set()
    if OUTPUT_FILE.is_file():
        with OUTPUT_FILE.open() as f:
            for row in csv.reader(f, delimiter="\t"):
                if row:
                    done.add(row[0])
    return done


def call_gemini(words: List[str]) -> List[Dict[str, str]]:
    prompt = SYSTEM_PROMPT + "\n\n" + USER_PROMPT_TEMPLATE.format(words=", ".join(words))
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    content = response.text.strip()
    
    # Strip markdown code blocks if present
    if content.startswith("```json") and content.endswith("```"):
        content = content[7:-3].strip()
    elif content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        # Basic recovery: wrap in [] if single object, else raise
        if content.startswith("{") and content.endswith("}"):
            data = [json.loads(content)]
        else:
            raise RuntimeError(f"Gemini returned non-JSON output: {content[:200]}…") from e
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array from Gemini")
    return data


def write_rows(rows: List[Dict[str, str]]) -> None:
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with OUTPUT_FILE.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        for r in rows:
            w.writerow([r.get("word", "").lower(), r.get("origin"), r.get("size"), r.get("category")])


def main():
    parser = argparse.ArgumentParser(description="Batch-label 20Q subjects with Gemini")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--limit", type=int, metavar="N", help="Label only the first N unlabeled words (default 100)")
    group.add_argument("--all", action="store_true", help="Label the full remaining set (~10K)")
    parser.add_argument("--pause", type=float, default=0.25, help="Seconds to sleep between Gemini calls (default 0.25)")
    args = parser.parse_args()

    subjects = load_subject_list()
    done = load_done_set()
    todo = [w for w in subjects if w not in done]

    if not args.all:
        limit = args.limit if args.limit is not None else 100
        todo = todo[:limit]

    print(f"[label] Starting – {len(todo)} words to label (done {len(done)})")
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        print(f"[label] Batch {i//BATCH_SIZE + 1} | {len(batch)} words…", end=" ")
        try:
            rows = call_gemini(batch)
        except Exception as e:
            print("❌ error", e)
            print("Stopping. Partial results saved.")
            break
        write_rows(rows)
        print("✓")
        time.sleep(args.pause)

    print("[label] Done.")


if __name__ == "__main__":
    main() 