#!/usr/bin/env python3
"""
wordnet_vowel_index.py
----------------------
Builds an in‑memory index of **all English nouns** in WordNet keyed by:
    • word length
    • first letter
    • first‑vowel position (1‑based)
    • second‑vowel position (1‑based, or 0 for "single‑vowel word")

After the one‑time build, look‑ups are O(1) dict hits and return immediately.

Usage (CLI):
    python3 wordnet_vowel_index.py 6 s 2 5
    # → prints all 6‑letter nouns starting with "s" whose vowels are at 2 & 5

As a library:
    from wordnet_vowel_index import WordIndex
    idx = WordIndex()                     # builds once, ~1 s
    words = idx.query(5, "b", 2, 0)      # (legacy) exact-letter lookup

    # New categorical query – 7-letter words whose first letter is in category 2
    # (C, G, O, J, Q, S, U), vowels at positions 2 & 4, and letter "S" at pos 5
    advanced = idx.query_category(7, 2, 2, 4, random_constraint="5S")
"""

from __future__ import annotations

import re
import sys
from functools import lru_cache as _lru
from pathlib import Path
from typing import Dict, List, Tuple

import nltk
from nltk.corpus import wordnet as wn
from nltk.stem import WordNetLemmatizer
# Optional word frequency (Zipf); import lazily if available
try:
    from wordfreq import zipf_frequency  # type: ignore
except ImportError:  # network issues or pkg not installed
    zipf_frequency = None  # type: ignore

# Make sure WordNet corpora are present -------------------------------------- #
try:
    wn.synsets("dog")
except LookupError:  # first run
    print("[setup] downloading WordNet…", file=sys.stderr)
    nltk.download("wordnet")

VOWELS = "AEIOUY"

# WordNet lemmatizer for detecting pluralia tantum
LEMMATIZER = WordNetLemmatizer()

# Physical object categories in WordNet
PHYSICAL_LEXNAMES = {
    "noun.artifact",    # man-made objects
    "noun.object",      # natural objects
    "noun.animal",      # animals
    "noun.plant",       # plants
    "noun.body",        # body parts
    "noun.food",        # foods and drinks
    "noun.substance",   # materials
    "noun.vehicle",     # vehicles
}

# Lexnames that should be excluded even though they are nouns
NON_PHYSICAL_LEXNAMES = {
    "noun.location",  # places, regions
    "noun.quantity",  # amounts, measures
    "noun.time",      # morning, weekend
    "noun.event",     # wedding, festival
    "noun.person",    # people / roles – treat as non-physical for this app
}

# Always-allowed plural-only objects
ALLOWED_PLURALS = {
    # household / clothing
    "stairs", "pants", "shorts", "jeans", "trousers", "pajamas", "clothes", "underwear",
    # tools / equipment
    "scissors", "pliers", "tongs", "binoculars", "goggles", "headphones", "earbuds",
    # eyewear
    "glasses", "spectacles",
}

# Words must meet this Zipf frequency (if wordfreq present)
COMMON_ZIPF_THRESHOLD = 3.5

# Fallback: WordNet lemma.count() occurrences
COMMON_COUNT_THRESHOLD = 0  # include even very rare words; we will filter in API

_PHYSICAL_ROOT = wn.synset('physical_entity.n.01')

@_lru(maxsize=2048)
def is_physical(syn) -> bool:
    """Return True if *syn* is (descendant of) physical_entity.n.01."""
    if syn.lexname() in PHYSICAL_LEXNAMES:
        # Additional check: filter out conceptual/spatial/abstract terms
        definition = syn.definition().lower()
        conceptual_keywords = [
            'part of', 'section of', 'area of', 'region of', 'portion of',
            'direction', 'location', 'place where', 'state of', 'condition of',
            'process of', 'act of', 'instance of', 'example of', 'type of',
            'category of', 'class of', 'group of', 'collection of',
            'amount', 'sum', 'total', 'quantity', 'number', 'value',
            'transport', 'service', 'anesthetic', 'berth'
        ]
        if any(keyword in definition for keyword in conceptual_keywords):
            return False
        return True
    if syn.lexname() in NON_PHYSICAL_LEXNAMES:
        return False
    return any(h == _PHYSICAL_ROOT for h in syn.closure(lambda s: s.hypernyms()))

# Letter category buckets for first-letter type queries ------------------- #
CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},  # J & U intentionally overlap
    3: {"B", "D", "P", "R", "J", "U"},          # J & U intentionally overlap
}

RANDOM_LETTER_RE = re.compile(r"^(\d+)([A-Za-z])$")


def vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1‑based positions of vowels in *word* (case‑insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)


# Helper: get character at 1-based *pos* (ignores spaces). Returns '' if out of range.
def _char_at(word: str, pos: int) -> str:
    clean = word.replace(" ", "")
    if 1 <= pos <= len(clean):
        return clean[pos - 1]
    return ""


class WordIndex:
    """Build once, then lightning‑fast `query()` calls."""

    def __init__(self):
        self.index: Dict[Tuple[int, str, int, int], List[str]] = {}
        self._build()

    def _build(self) -> None:
        print("[index] building WordNet noun index…", file=sys.stderr)
        for syn in wn.all_synsets(pos=wn.NOUN):
            # Skip non-physical concepts
            if not is_physical(syn):
                continue
            for lemma in syn.lemmas():
                w = lemma.name().lower().replace("_", " ")  # keep spaces for multi‑word
                # Skip very rare / technical words
                if zipf_frequency is not None:
                    if zipf_frequency(w.replace(" ", ""), "en") < COMMON_ZIPF_THRESHOLD:
                        continue
                else:
                    if lemma.count() < COMMON_COUNT_THRESHOLD:
                        continue

                # Exclude multi-word expressions (contain spaces)
                if " " in w:
                    continue

                if not re.fullmatch(r"[a-z ]+", w):
                    continue  # skip punctuation, digits, mixed‑case proper names
                # Skip if the word's most frequent sense is not a noun
                synsets_all = wn.synsets(w)
                if not synsets_all or synsets_all[0].pos() != wn.NOUN:
                    continue

                vpos = vowel_positions(w)
                if not vpos:
                    continue  # words without vowels (rare) – ignore
                first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)

                # Skip proper nouns / names (capitalized lemmas)
                if any(lem.name()[0].isupper() for lem in wn.lemmas(w)):
                    continue

                # Skip regular plural forms that have a singular counterpart; keep plural-only nouns
                if w.endswith("s"):
                    singular = LEMMATIZER.lemmatize(w.replace(" ", "_"), wn.NOUN).replace("_", " ")
                    plural_only = singular == w
                    if not plural_only and w not in ALLOWED_PLURALS:
                        continue

                primary_synsets = wn.synsets(w, pos=wn.NOUN)
                if not primary_synsets or not is_physical(primary_synsets[0]):
                    continue

                # For animals, require some usage count to avoid obscure taxa
                if primary_synsets[0].lexname() == "noun.animal":
                    if all(lem.count() < 2 for lem in primary_synsets[0].lemmas() if lem.name() == w.replace(" ", "_")):
                        continue

                key = (len(w.replace(" ", "")), w[0], first_v, second_v)
                self.index.setdefault(key, []).append(w)

        # deduplicate while preserving order
        for k, lst in self.index.items():
            seen = set()
            self.index[k] = [x for x in lst if not (x in seen or seen.add(x))]

        print(f"[index] done – {len(self.index):,} unique (len,letter,v1,v2) keys", file=sys.stderr)

    # ------------------------------------------------------------------ #
    @_lru(maxsize=8_192)
    def query(
        self,
        length: int,
        first_letter: str,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
    ) -> List[str]:
        """Return nouns matching the exact pattern (list may be empty)."""
        return self.index.get(
            (length, first_letter.lower(), first_vowel_pos, second_vowel_pos), []
        )

    # ------------------------------------------------------------------ #
    def query_category(
        self,
        length: int,
        category: int,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        random_constraint: str | None = None,
        more_vowels: bool | None = None,
    ) -> List[str]:
        """Advanced query using *first-letter category* instead of exact letter.

        Args:
            length: total characters (spaces ignored)
            category: 1 / 2 / 3 (see CATEGORY_MAP)
            first_vowel_pos: 1-based index of first vowel
            second_vowel_pos: 1-based index of second vowel, or 0 if none
            random_constraint: optional string like "5S" meaning *s* is 5th letter
            more_vowels: if True → word has >2 vowels; if False → ≤2 vowels; if None ignore
        """
        if category not in CATEGORY_MAP:
            raise ValueError(f"Unknown category {category}. Must be 1, 2, or 3.")

        # gather candidates from all letters in the category
        candidates: List[str] = []
        for letter in CATEGORY_MAP[category]:
            candidates.extend(
                self.query(length, letter.lower(), first_vowel_pos, second_vowel_pos)
            )

        # deduplicate (preserve order)
        seen: set[str] = set()
        deduped = [w for w in candidates if not (w in seen or seen.add(w))]

        # Apply optional filters ------------------------------------------------
        if random_constraint:
            m = RANDOM_LETTER_RE.match(random_constraint.upper())
            if not m:
                raise ValueError(
                    "random_constraint must look like '5S' (position followed by letter)"
                )
            pos, letter = int(m.group(1)), m.group(2).lower()
            deduped = [w for w in deduped if _char_at(w, pos) == letter]

        if more_vowels is not None:
            if more_vowels:
                deduped = [w for w in deduped if len(vowel_positions(w)) > 2]
            else:
                deduped = [w for w in deduped if len(vowel_positions(w)) <= 2]

        return deduped


# -------------------------------------------------------------------------- #
# CLI helper
# -------------------------------------------------------------------------- #

def _cli():
    if len(sys.argv) < 4:
        print(
            "Usage:\n"
            "  Exact-letter:   wordnet_vowel_index.py <len> <letter> <v1> [v2]\n"
            "  Category mode:  wordnet_vowel_index.py <len> <1|2|3> <v1> [v2] [random] [more]\n"
            "    random → e.g. 5S  (position+letter)\n"
            "    more   → y/n  (y = >2 vowels)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    length = int(sys.argv[1])
    second_vowel = 0

    idx = WordIndex()

    # Category mode if arg2 is digit 1-3
    if sys.argv[2].isdigit():
        category = int(sys.argv[2])
        first_vowel = int(sys.argv[3])
        if len(sys.argv) > 4 and sys.argv[4].isdigit():
            second_vowel = int(sys.argv[4])
            extra_args = sys.argv[5:]
        else:
            extra_args = sys.argv[4:]

        random_c = extra_args[0] if extra_args else None
        more_flag = extra_args[1].lower() if len(extra_args) > 1 else None
        more_vowels = True if more_flag == "y" else False if more_flag == "n" else None

        words = idx.query_category(
            length,
            category,
            first_vowel,
            second_vowel,
            random_constraint=random_c,
            more_vowels=more_vowels,
        )
    else:  # legacy exact-letter mode
        first_letter = sys.argv[2]
        first_vowel = int(sys.argv[3])
        second_vowel = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        words = idx.query(length, first_letter, first_vowel, second_vowel)

    print("\n".join(words) if words else "<no matches>")


if __name__ == "__main__":
    _cli() 