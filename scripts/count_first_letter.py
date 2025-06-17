#!/usr/bin/env python3
"""count_first_letter.py
Compute how much restricting first letter to {M, T, S, F} narrows the candidate set
for names, nouns, and places.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from first_name_index import FirstNameIndex
from place_index import PlaceIndex
from wordnet_vowel_index import WordIndex

LETTERS = {"m", "t", "s", "f"}

def count_reduction(pop: set[str]):
    total = len(pop)
    narrowed = sum(1 for w in pop if w[0] in LETTERS)
    return total, narrowed

names_set = {n for lst in FirstNameIndex().index.values() for n,_ in lst}
places_set = {n for lst in PlaceIndex().index.values() for n,_ in lst}
words_set = {w for lst in WordIndex().index.values() for w in lst}

data = {
    "names": names_set,
    "words": words_set,
    "places": places_set,
}

for label, pop in data.items():
    total, narrowed = count_reduction(pop)
    pct = narrowed/total*100
    print(f"{label.capitalize():6}: {narrowed} / {total}  ({pct:.1f}% remain) ⇒ {100-pct:.1f}% reduction") 