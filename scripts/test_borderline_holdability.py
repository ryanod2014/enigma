#!/usr/bin/env python3
"""
test_borderline_holdability.py
------------------------------
To validate the holdability filter, this script identifies "borderline" nouns
and tests how the current filter classifies them.

"Borderline" nouns are defined as those that were classified as "Too Large" by
a stricter version of our filter but are now considered "Holdable" by the
current, more permissive version.

This helps ensure we are not accidentally excluding items that a person could
plausibly hold.
"""
from __future__ import annotations

import random
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nltk.corpus import wordnet as wn
from wordnet_vowel_index import WordIndex

SAMPLE_SIZE = 500

# --- Filter Definitions ---

# This is the CURRENT, more permissive filter logic from build_holdable_flags.py
# We use it to check the final classification of our borderline items.
PERMISSIVE_EXCLUDE_HYPERNYMS = {
    "vehicle.n.01", "building.n.01", "structure.n.01", "geological_formation.n.01",
    "body_of_water.n.01", "land.n.01", "thoroughfare.n.01", "facility.n.01",
    "celestial_body.n.01", "furniture.n.01", "machine.n.01", "installation.n.01",
    "living_thing.n.01", "animal.n.01", "plant.n.01", "tree.n.01",
}
PERMISSIVE_EXCLUDE_KEYWORDS = re.compile(r"\b(machine|engine|appliance|building|...)\b") # Simplified for brevity
PERMISSIVE_ALLOW_LIST = {
    "cat", "dog", "tampon", "hacksaw", "nailbrush", "lance", "backsword",
    # ... and all the others from the previous script
}

# This is the OLD, stricter filter logic. We use it to find what *used to be* excluded.
STRICT_EXCLUDE_HYPERNYMS = PERMISSIVE_EXCLUDE_HYPERNYMS | {"instrumentality.n.03"}
STRICT_EXCLUDE_KEYWORDS = re.compile(
    r"\b(machine|engine|appliance|equipment|instrumentality|device|building|...)\b" # Simplified for brevity
)


def get_all_hypernyms(syn: wn.Synset) -> set[str]:
    hypernyms = set()
    for h in syn.hypernyms() + syn.instance_hypernyms():
        hypernyms.add(h.name())
        hypernyms.update(get_all_hypernyms(h))
    return hypernyms

def is_holdable(word: str, hypernym_exclusions: set, keyword_exclusions: re.Pattern, allow_list: set) -> bool:
    if word in allow_list:
        return True
    syns = wn.synsets(word, pos=wn.NOUN)
    if not syns:
        return False
    s = syns[0]
    if any(parent in get_all_hypernyms(s) for parent in hypernym_exclusions):
        return False
    if keyword_exclusions.search(s.definition()):
        return False
    return True

# --- Main Script ---

def main():
    print("[test] Building WordIndex to get full noun list...")
    idx = WordIndex()
    all_physical_nouns = {w for lst in idx.index.values() for w in lst}
    print(f"[test] Processing {len(all_physical_nouns):,} physical nouns...")

    # Load the full permissive allow list
    from scripts.build_holdable_flags import MANUAL_ALLOW_LIST as final_allow_list
    from scripts.build_holdable_flags import EXCLUDE_DEFINITION_KEYWORDS as final_keywords
    from scripts.build_holdable_flags import EXCLUDE_HYPERNYMS as final_hypernyms

    # Find what the strict filter would have excluded
    strict_large_nouns = set()
    for noun in all_physical_nouns:
        # Define the strict keyword list for this test
        strict_keywords = re.compile(r"\b(device|instrumentality|equipment)\b", re.IGNORECASE)
        if not is_holdable(noun, STRICT_EXCLUDE_HYPERNYMS, strict_keywords, set()):
            strict_large_nouns.add(noun)

    # Find what the current permissive filter considers holdable
    currently_holdable_nouns = set()
    for noun in all_physical_nouns:
        if is_holdable(noun, final_hypernyms, final_keywords, final_allow_list):
            currently_holdable_nouns.add(noun)

    # The borderline cases are those that WERE large but are NOW holdable
    borderline_nouns = strict_large_nouns.intersection(currently_holdable_nouns)

    print(f"\nFound {len(borderline_nouns)} borderline nouns.")
    print("These are items that the stricter filter excluded but the current, more permissive filter includes.")

    # --- Test and Display a Sample ---
    sample_size = min(len(borderline_nouns), SAMPLE_SIZE)
    if sample_size == 0:
        print("\nNo borderline cases found to test.")
        return

    print(f"\n--- Testing a random sample of {sample_size} borderline nouns ---")
    test_sample = random.sample(list(borderline_nouns), sample_size)

    final_classifications = {
        "Holdable": [],
        "Too Large": [],
    }

    for noun in test_sample:
        if is_holdable(noun, final_hypernyms, final_keywords, final_allow_list):
            final_classifications["Holdable"].append(noun)
        else:
            final_classifications["Too Large"].append(noun)

    print(f"\n--- All {len(final_classifications['Holdable'])} sampled borderline nouns are now classified as HOLDABLE ---")
    print("(This is expected, as we are sampling from the set of newly-included items.)")
    print("\nPlease review this list to ensure these items should indeed be considered holdable:")
    print(", ".join(sorted(final_classifications["Holdable"])))

    if final_classifications["Too Large"]:
        print("\n--- WARNING: Some borderline nouns were unexpectedly classified as TOO LARGE ---")
        print("This may indicate an issue in the filter logic.")
        print(", ".join(sorted(final_classifications["Too Large"])))


if __name__ == "__main__":
    main() 