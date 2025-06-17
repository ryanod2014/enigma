#!/usr/bin/env python3
"""
build_holdable_flags.py
-------------------------
Generate a TSV file marking which nouns from the WordIndex are "holdable"
(i.e., can plausibly be held in one's hands).

This uses a set of heuristics based on WordNet hypernyms (parent categories)
and definition keyword matching to exclude items that are too large, abstract,
or are locations.
"""
from __future__ import annotations

import csv
import random
import re
import sys
from pathlib import Path

# Add project root to path to allow importing our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nltk.corpus import wordnet as wn
from wordnet_vowel_index import WordIndex

# --- Configuration ---
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_FILE = DATA_DIR / "holdable_flags.tsv"
SAMPLE_SIZE = 20  # Number of random samples to print for review

# --- Heuristics for "Too Large" ---

# 1. Exclude nouns whose hypernym (parent) tree contains these concepts.
#    These are broad categories for things that are generally not holdable.
EXCLUDE_HYPERNYMS = {
    # Obvious locations and structures
    "vehicle.n.01", "building.n.01", "structure.n.01", "geological_formation.n.01",
    "body_of_water.n.01", "land.n.01", "thoroughfare.n.01", "facility.n.01",
    "celestial_body.n.01",
    # Large objects
    "furniture.n.01", "machine.n.01", "installation.n.01",
    # Living things (we want objects, not creatures/plants)
    "living_thing.n.01", "animal.n.01", "plant.n.01", "tree.n.01",
}

# 2. Exclude nouns if their definition contains these keywords.
#    This catches items missed by hypernyms. Case-insensitive regex.
EXCLUDE_DEFINITION_KEYWORDS = re.compile(
    r"\b("
    # Sizes and properties
    r"large|huge|massive|heavy|long|tall|big|"
    # Types of things
    r"machine|engine|appliance|"
    r"building|structure|room|area|region|site|zone|place|location|"
    r"vehicle|motorcycle|bicycle|car|truck|bus|ship|boat|aircraft|airplane|rocket|"
    r"furniture|table|chair|desk|bed|sofa|couch|cabinet|wardrobe|"
    r"mountain|river|ocean|lake|sea|continent|country|state|city|town|village|"
    r"castle|tower|bridge|road|highway|street|station|stadium|factory|mine|farm|"
    r"hotel|campus|railway|airport"
    r")\b",
    re.IGNORECASE,
)

# 3. Manual allow-list for items that might be wrongly excluded.
#    e.g., a "cat" is an animal, but can be held. "Toy car" is a vehicle.
MANUAL_ALLOW_LIST = {
    "cat", "dog", "hamster", "mouse", "rat", "kitten", "puppy",
    "laptop", "phone", "radio", "camera", "drone",
    "ball", "bat", "puck", "frisbee",
    "guitar", "violin", "flute", "drum",
    "pen", "pencil", "brush", "chisel",
    "cup", "jar", "box", "bottle", "plate", "bowl",
    "book", "card", "coin", "key",
    "toy", "doll", "action_figure",
    "tampon", "hemostat", "saltshaker", "sack", "brad", "ginger",
    "hacksaw", "nailbrush", "lance", "backsword",
}

# --- Main Script ---

def get_all_hypernyms(syn: wn.Synset) -> set[str]:
    """Recursively get all parent synset names for a given synset."""
    hypernyms = set()
    for h in syn.hypernyms() + syn.instance_hypernyms():
        hypernyms.add(h.name())
        hypernyms.update(get_all_hypernyms(h))
    return hypernyms


def is_holdable(word: str) -> bool:
    """Apply heuristics to determine if a word refers to a holdable object."""
    if word in MANUAL_ALLOW_LIST:
        return True

    syns = wn.synsets(word, pos=wn.NOUN)
    if not syns:
        return False  # Not a recognized noun

    # Check the first, most common sense of the word
    s = syns[0]

    # Rule 1: Check hypernyms
    all_parents = get_all_hypernyms(s)
    if any(parent in all_parents for parent in EXCLUDE_HYPERNYMS):
        return False

    # Rule 2: Check definition keywords
    definition = s.definition()
    if EXCLUDE_DEFINITION_KEYWORDS.search(definition):
        return False

    return True


def main():
    print("[holdable] Building WordIndex to get full noun list...")
    idx = WordIndex()
    all_physical_nouns = {w for lst in idx.index.values() for w in lst}
    print(f"[holdable] Processing {len(all_physical_nouns):,} physical nouns...")

    holdable_nouns = set()
    too_large_nouns = set()

    for noun in all_physical_nouns:
        if is_holdable(noun):
            holdable_nouns.add(noun)
        else:
            too_large_nouns.add(noun)

    # --- Write flags to file ---
    DATA_DIR.mkdir(exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        for word in sorted(holdable_nouns):
            writer.writerow([word, "1"])
    print(f"[holdable] Wrote {len(holdable_nouns):,} holdable flags to {OUT_FILE}")

    # --- Print summary and samples ---
    total = len(all_physical_nouns)
    hold_pct = len(holdable_nouns) / total * 100
    large_pct = len(too_large_nouns) / total * 100

    print("\n--- Holdability Analysis ---")
    print(f"Total physical nouns: {total}")
    print(f"  - Holdable:   {len(holdable_nouns):>5} ({hold_pct:.1f}%)")
    print(f"  - Too Large:  {len(too_large_nouns):>5} ({large_pct:.1f}%)")

    print(f"\n--- Random Samples (Holdable) ---")
    sample_hold = random.sample(list(holdable_nouns), min(SAMPLE_SIZE, len(holdable_nouns)))
    print(", ".join(sorted(sample_hold)))

    print(f"\n--- Random Samples (Too Large) ---")
    sample_large = random.sample(list(too_large_nouns), min(SAMPLE_SIZE, len(too_large_nouns)))
    print(", ".join(sorted(sample_large)))


if __name__ == "__main__":
    main() 