"""first_name_index.py
Builds an in-memory index of common first names keyed by:
    • word length (spaces ignored)
    • first letter
    • first & second vowel positions (1-based, 0 if word has only one vowel)

Extra filters supported:
    • gender  : "m" | "f" | "u" (unisex/unknown)
    • origin  : ISO-3166 country code (optional)
    • common  : True → top 200 US/world; False → uncommon only

NOTE: For now we ship a minimal built-in dataset (_DATA). Swap in a larger
`data/first_names.tsv` later without touching the API.
"""
from __future__ import annotations

import csv
import re
from functools import lru_cache as _lru
from pathlib import Path
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
VOWELS = "AEIOUY"

CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}

RANDOM_LETTER_RE = re.compile(r"^(\d+)([A-Za-z])$")

# --------------------------------------------------------------------------- #
# Fallback tiny dataset; each row: name, gender, origin, rank_us, rank_world
_DATA = [
    ("john", "m", "US", 1, 20),
    ("mary", "f", "US", 1, 50),
    ("li", "m", "CN", 0, 1),
    ("maria", "f", "ES", 5, 10),
    ("alex", "u", "US", 75, 130),
]

# --------------------------------------------------------------------------- #

def _vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1-based positions of vowels in *word* (case-insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)


def _char_at(word: str, pos: int) -> str:
    """Return char at 1-based *pos* ignoring spaces; '' if out of range."""
    clean = word.replace(" ", "")
    return clean[pos - 1] if 1 <= pos <= len(clean) else ""


class FirstNameIndex:
    """Fast lookup index for first names."""

    def __init__(self, data_path: str | Path | None = None):
        # Key → list[(name, meta)] where key=(len, first_letter, v1, v2)
        self.index: Dict[Tuple[int, str, int, int], List[Tuple[str, Dict]]] = {}
        self._build(data_path)

    # ------------------------------------------------------------------ #
    def _load_rows(self, data_path: str | Path | None):
        """Yield tuples (name, gender, origin, rank_us, rank_world)."""
        # Default to bundled TSV if present
        if data_path is None:
            default_path = Path(__file__).resolve().parent / "data" / "first_names.tsv"
            if default_path.is_file():
                data_path = default_path

        if data_path:
            p = Path(data_path)
            if not p.is_file():
                raise FileNotFoundError(p)
            with p.open(newline="", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                for row in reader:
                    if not row or row[0].startswith("#"):
                        continue
                    name, gender, origin, rank_us, rank_world = row[:5]
                    yield name.lower(), gender.lower(), origin.upper(), int(rank_us), int(rank_world)
            return
        # Fallback built-in
        for rec in _DATA:
            yield rec

    def _build(self, data_path: str | Path | None):
        for name, gender, origin, rank_us, rank_world in self._load_rows(data_path):
            if " " in name:
                continue  # ignore multi-word for now
            vpos = _vowel_positions(name)
            if not vpos:
                continue
            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)

            meta = {
                "gender": gender if gender in {"m", "f"} else "u",
                "origin": origin if len(origin) == 2 else None,
                "rank_us": rank_us,
                "count": rank_world,
                "common": rank_us and rank_us <= 200 or rank_world and rank_world <= 200,
            }
            key = (len(name), name[0], first_v, second_v)
            self.index.setdefault(key, []).append((name, meta))

        # Deduplicate names preserving order --------------------------------
        for k, lst in self.index.items():
            seen = set()
            dedup: List[Tuple[str, Dict]] = []
            for n, m in lst:
                if n not in seen:
                    dedup.append((n, m))
                    seen.add(n)
            self.index[k] = dedup

    # ------------------------------------------------------------------ #
    @_lru(maxsize=2048)
    def _lookup(self, length: int, first_letter: str, v1: int, v2: int) -> List[Tuple[str, Dict]]:
        return self.index.get((length, first_letter.lower(), v1, v2), [])

    # Public helpers ---------------------------------------------------- #
    def query(
        self,
        length: int,
        first_letter: str,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        gender: str | None = None,
        origin: str | None = None,
        common: bool | None = None,
    ) -> List[str]:
        """Exact-letter query; returns matching first names."""
        results = self._lookup(length, first_letter, first_vowel_pos, second_vowel_pos)
        return self._filter(results, gender, origin, common)

    def query_category(
        self,
        length: int,
        category: int,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        random_constraint: str | None = None,
        more_vowels: bool | None = None,
        gender: str | None = None,
        origin: str | None = None,
        common: bool | None = None,
    ) -> List[str]:
        if category not in CATEGORY_MAP:
            raise ValueError("category must be 1, 2, or 3")

        # Gather from all letters in bucket
        candidates: List[Tuple[str, Dict]] = []
        for letter in CATEGORY_MAP[category]:
            candidates.extend(
                self._lookup(length, letter.lower(), first_vowel_pos, second_vowel_pos)
            )

        # Deduplicate preserving order
        seen: set[str] = set()
        dedup = [(n, m) for n, m in candidates if not (n in seen or seen.add(n))]

        # Apply optional random letter constraint
        if random_constraint:
            m = RANDOM_LETTER_RE.match(random_constraint.upper())
            if not m:
                raise ValueError("random_constraint must look like '5S'")
            pos, letter = int(m.group(1)), m.group(2).lower()
            dedup = [(n, meta) for n, meta in dedup if _char_at(n, pos) == letter]

        # Vowel-count filter
        if more_vowels is not None:
            if more_vowels:
                dedup = [(n, m) for n, m in dedup if len(_vowel_positions(n)) > 2]
            else:
                dedup = [(n, m) for n, m in dedup if len(_vowel_positions(n)) <= 2]

        # Remaining meta-based filters
        return self._filter(dedup, gender, origin, common)

    # ------------------------------------------------------------------ #
    def _filter(
        self,
        items: List[Tuple[str, Dict]],
        gender: str | None,
        origin: str | None,
        common: bool | None,
    ) -> List[str]:
        out: List[str] = []
        for name, meta in items:
            if gender and meta["gender"] != gender:
                continue
            if origin and meta["origin"] != origin.upper():
                continue
            if common is True and not meta["common"]:
                continue
            if common is False and meta["common"]:
                continue
            out.append(name)
        return out 