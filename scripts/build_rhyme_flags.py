#!/usr/bin/env python3
"""build_rhyme_flags.py
Generate TSV mapping word → 1 if it rhymes (exact or close) with at least one English noun.
Exact rhymes use CMU Pronouncing Dict via `pronouncing`.
Close rhymes use Double-Metaphone match on ending syllable using `fuzzy`.
"""
from __future__ import annotations

import csv
import os
import sys
import unicodedata
from pathlib import Path
from typing import Set, Dict

# add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pronouncing  # type: ignore
import fuzzy  # type: ignore
from nltk.corpus import wordnet as wn

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_FILE = DATA_DIR / "rhyme_flags.tsv"


def last_dmetaphone(word: str) -> str:
    # normalize and convert to ascii-safe form
    word = unicodedata.normalize('NFD', word)
    word = ''.join(c for c in word if ord(c) < 128 and c.isalpha())
    dm = fuzzy.DMetaphone()
    codes = dm(word)
    # return first non-None code
    for c in codes:
        if c:
            return c.decode()
    return ""


def build_noun_sets() -> tuple[Set[str], Dict[str, Set[str]]]:
    # Use only hand-holdable objects
    nouns = set()
    HOLDABLE_LEXNAMES = {
        "noun.artifact",  # tools, utensils, clothing, etc
        "noun.food",      # fruits, vegetables, etc
        "noun.plant",     # flowers, small plants (excludes trees)
        "noun.body",      # body parts
    }
    EXCLUDE_WORDS = {
        # large artifacts
        "building", "house", "car", "truck", "ship", "boat", "plane", "aircraft", 
        "bridge", "road", "tower", "castle", "church", "stadium", "factory",
        # furniture (too big to hold)
        "table", "chair", "desk", "bed", "sofa", "couch", "cabinet", "wardrobe",
        # abstract/chemical
        "element", "compound", "molecule", "atom", "ion", "gas", "liquid",
    }
    
    for syn in wn.all_synsets("n"):
        if syn.lexname() not in HOLDABLE_LEXNAMES:
            continue
        for lemma in syn.lemmas():
            word = lemma.name().lower().replace("_", "")
            if len(word) < 3 or not word.isalpha():
                continue
            if word in EXCLUDE_WORDS:
                continue
            # Skip if definition suggests it's too big
            definition = syn.definition().lower()
            if any(big in definition for big in ["large", "building", "structure", "vehicle", "tree"]):
                continue
            nouns.add(word)
    dm_map: Dict[str, Set[str]] = {}
    dm = fuzzy.DMetaphone()
    for n in nouns:
        code = last_dmetaphone(n)
        if not code:
            continue
        dm_map.setdefault(code, set()).add(n)
    return nouns, dm_map


def main() -> None:
    print("[rhyme] building noun rhyme sets…")
    noun_set, dm_map = build_noun_sets()

    # Gather all candidate words from datasets ---------------------------
    from first_name_index import FirstNameIndex
    from place_index import PlaceIndex
    from wordnet_vowel_index import WordIndex

    names_idx = FirstNameIndex()
    places_idx = PlaceIndex()
    nouns_idx = WordIndex()

    candidates: Set[str] = set()
    for lst in names_idx.index.values():
        candidates.update(n for n, _ in lst)
    for lst in places_idx.index.values():
        candidates.update(n for n, _ in lst)
    for lst in nouns_idx.index.values():
        candidates.update(lst)

    print(f"[rhyme] total candidate words: {len(candidates):,}")

    flags: Dict[str, int] = {}

    for w in candidates:
        keep = False
        # exact rhyme check
        for r in pronouncing.rhymes(w):
            if r in noun_set and r != w:
                keep = True
                break
        if not keep:
            # close rhyme: matching double metaphone code of ending syllable
            code = last_dmetaphone(w)
            if code and len(dm_map.get(code, set()) - {w}):
                keep = True
        if keep:
            flags[w] = 1

    print(f"[rhyme] words with noun rhymes: {len(flags):,}")

    DATA_DIR.mkdir(exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        for word in sorted(flags.keys()):
            w.writerow([word, "1"])
    print("[rhyme] written", OUT_FILE)


if __name__ == "__main__":
    main() 