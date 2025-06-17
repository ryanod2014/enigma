#!/usr/bin/env python3
"""evaluate_rhyme_filter.py
Print how many first names have at least one rhyming English noun
(based on CMU Pronouncing Dict via `pronouncing` + WordNet nouns).

Gives a quick sense of the selectivity of a "rhymes with a noun" filter.
"""
from __future__ import annotations

from collections import Counter
from typing import Set
import sys

try:
    import pronouncing  # type: ignore
except ImportError:
    sys.stderr.write("[error] Please pip-install 'pronouncing' to run this script.\n")
    sys.exit(1)

from nltk.corpus import wordnet as wn

from first_name_index import FirstNameIndex


# --------------------------------------------------------------------------- #

def build_noun_set() -> Set[str]:
    nouns = {l.name().lower().replace('_', '') for s in wn.all_synsets('n') for l in s.lemmas()}
    # remove very short strings – rhyming not meaningful
    return {w for w in nouns if len(w) >= 3 and w.isalpha()}


def main() -> None:
    idx = FirstNameIndex()
    names = {n for lst in idx.index.values() for n, _ in lst}

    noun_set = build_noun_set()

    total = len(names)
    rhyme_hits = 0

    for name in names:
        rhymes = set(pronouncing.rhymes(name))
        if rhymes & noun_set:
            rhyme_hits += 1

    print(f"Total unique names: {total}")
    print(f"Names that rhyme with at least one common noun: {rhyme_hits}")
    pct = rhyme_hits / total * 100
    print(f"Filter would reduce pool to {pct:.1f}% of original (×{total/rhyme_hits:.2f} narrower)")


if __name__ == "__main__":
    main() 