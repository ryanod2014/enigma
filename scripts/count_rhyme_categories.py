#!/usr/bin/env python3
"""count_rhyme_categories.py
Compute how many first names rhyme (exact CMU) with at least one noun in five
WordNet lexname buckets: food, animal, plant, body, artifact.
Print absolute counts and percentages relative to total unique first names.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import pronouncing  # type: ignore
from nltk.corpus import wordnet as wn
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from first_name_index import FirstNameIndex

# --------------------------------------------------------------------------- #
CATEGORIES = {
    "food": "noun.food",
    "animal": "noun.animal",
    "plant": "noun.plant",
    "body": "noun.body",
    "artifact": "noun.artifact",
    "tool": "tool",
    "toy": "toy",
    "weapon": "weapon",
    "jewelry": "jewel",
    "instrument": "instrument",
    "electronics": "electronic",
    "furniture": "furniture",
    "vehicle_small": "bike",
    "container": "cup",
    "art_tool": "pen",
    "sport": "ball",
}

# Build noun rhyme sets per category
noun_sets: dict[str, set[str]] = {k: set() for k in CATEGORIES}
for syn in wn.all_synsets("n"):
    lex = syn.lexname()
    defn = syn.definition().lower()
    for cat, key in CATEGORIES.items():
        if lex == key or key in defn:
            noun_sets[cat].update(l.name().lower().replace("_", "") for l in syn.lemmas())

# Collect unique first names
idx = FirstNameIndex()
datasets = {
    'names': {n for lst in idx.index.values() for n,_ in lst},
    'nouns': {w for lst in __import__('wordnet_vowel_index').WordIndex().index.values() for w in lst},
    'places': {n for lst in __import__('place_index').PlaceIndex().index.values() for n,_ in lst},
}

for label, name_set in datasets.items():
    counts = Counter()
    for name in name_set:
        rhymes = set(pronouncing.rhymes(name))
        for cat, nset in noun_sets.items():
            if rhymes & nset:
                counts[cat] += 1
                break

    total = len(name_set)
    print(f"\n== {label.upper()}  (total {total}) ==")
    for cat in CATEGORIES:
        c = counts[cat]
        print(f"{cat.capitalize():>8}: {c:6d} ({c/total*100:5.1f}%)") 