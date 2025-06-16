# place_index.py
"""place_index.py
Builds an in-memory index of countries and (optionally) major cities keyed by:
    • word length (spaces ignored)
    • first letter
    • first & second vowel positions (1-based, 0 if word has only one vowel)
The public API mirrors `wordnet_vowel_index.WordIndex` so the frontend can
switch indexes with zero refactor.

Extra filter support:
    • place_type: "country" | "city" (optional)
    • region / continent code: AF, AS, EU, NA, OC, SA (optional)
    • common: True → populous cities (≥1 M) / all countries; False → uncommon only

Dependencies: pycountry, geonamescache

NOTE: The build is executed once at import time (<200 ms) and requires no
network because `geonamescache` ships the datasets.
"""
from __future__ import annotations

import re
from functools import lru_cache as _lru
from typing import Dict, List, Tuple

import pycountry
import geonamescache  # type: ignore

# --------------------------------------------------------------------------- #
VOWELS = "AEIOUY"

CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}

# continent codes coming from geonames / ISO.
CONTINENTS = {"AF", "AS", "EU", "NA", "OC", "SA"}

# Well-known countries that people would think of first in 20 questions
COMMON_COUNTRIES = {
    # Major powers & large countries
    "usa", "china", "russia", "india", "brazil", "canada", "australia", 
    "japan", "germany", "france", "italy", "spain", "mexico", "argentina",
    "egypt", "turkey", "iran", "poland", "ukraine", "nigeria", "ethiopia",
    "kenya", "ghana", "morocco", "algeria", "libya", "sudan", "chad",
    
    # Well-known European countries  
    "england", "scotland", "wales", "ireland", "norway", "sweden", "denmark",
    "finland", "belgium", "netherlands", "switzerland", "austria", "portugal",
    "greece", "hungary", "romania", "croatia", "serbia", "bulgaria",
    
    # Famous/notable smaller countries
    "israel", "jordan", "lebanon", "kuwait", "qatar", "thailand", "vietnam", 
    "malaysia", "singapore", "philippines", "indonesia", "pakistan", "bangladesh",
    "myanmar", "cambodia", "laos", "nepal", "tibet", "mongolia", "kazakhstan",
    "peru", "chile", "venezuela", "colombia", "ecuador", "bolivia", "paraguay",
    "uruguay", "cuba", "jamaica", "haiti", "panama", "nicaragua", "guatemala",
    "honduras", "libya", "tunisia", "zimbabwe", "botswana", "zambia", "tanzania",
    "uganda", "rwanda", "madagascar", "mali", "niger", "somalia", "yemen",
    "afghanistan", "uzbekistan", "georgia", "armenia", "azerbaijan", "cyprus"
}

# Well-known major cities (global recognition + major population centers)
COMMON_CITIES = {
    # Megacities & global capitals
    "tokyo", "beijing", "delhi", "shanghai", "mumbai", "dhaka", "karachi", 
    "istanbul", "moscow", "london", "paris", "madrid", "barcelona", "rome",
    "berlin", "vienna", "amsterdam", "stockholm", "oslo", "copenhagen",
    "warsaw", "prague", "budapest", "athens", "dublin", "lisbon", "zurich",
    
    # Major US cities
    "newyork", "losangeles", "chicago", "houston", "phoenix", "philadelphia",
    "antonio", "diego", "dallas", "jose", "austin", "worth", "columbus",
    "charlotte", "francisco", "indianapolis", "seattle", "denver", "washington",
    "boston", "nashville", "baltimore", "portland", "vegas", "detroit", "memphis",
    
    # Other major world cities
    "cairo", "lagos", "kinshasa", "luanda", "johannesburg", "casablanca",
    "addis", "nairobi", "dar", "kampala", "khartoum", "algiers", "tunis",
    "tehran", "baghdad", "riyadh", "kuwait", "doha", "dubai", "muscat",
    "kabul", "islamabad", "lahore", "kolkata", "chennai", "bangalore", "hyderabad",
    "bangkok", "jakarta", "manila", "kuala", "singapore", "hanoi", "saigon",
    "yangon", "phnom", "seoul", "busan", "taipei", "hong", "macau",
    "sydney", "melbourne", "perth", "brisbane", "adelaide", "auckland", "wellington",
    "toronto", "vancouver", "montreal", "calgary", "ottawa", "quebec",
    "mexico", "guadalajara", "monterrey", "bogota", "medellin", "caracas",
    "lima", "quito", "santiago", "valparaiso", "buenos", "montevideo", "asuncion",
    "brasilia", "paulo", "janeiro", "salvador", "fortaleza", "recife", "manaus"
}

# helper regex for random constraint like "5S"
RANDOM_LETTER_RE = re.compile(r"^(\d+)([A-Za-z])$")


def _vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1-based positions of vowels in *word* (case-insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)


def _char_at(word: str, pos: int) -> str:
    """Return char at 1-based *pos* ignoring spaces; '' if out of range."""
    clean = word.replace(" ", "")
    return clean[pos - 1] if 1 <= pos <= len(clean) else ""


class PlaceIndex:
    """Fast lookup index for countries & cities."""

    def __init__(self):
        # Key → list[(name, meta)] where key=(len, first_letter, v1, v2)
        self.index: Dict[Tuple[int, str, int, int], List[Tuple[str, Dict]]]= {}
        self._build()

    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        gc = geonamescache.GeonamesCache()

        # Countries ------------------------------------------------------
        for cdata in gc.get_countries().values():
            name_raw = cdata["name"]
            if " " in name_raw:
                # Skip multi-word for now; keeps length logic simple
                continue
            name = name_raw.lower()
            vpos = _vowel_positions(name)
            if not vpos:
                continue
            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)

            meta = {
                "type": "country",
                "region": cdata["continentcode"] if cdata["continentcode"] in CONTINENTS else None,
                "population": cdata.get("population", 0),
                "common": name in COMMON_COUNTRIES,  # Only well-known countries are common
            }
            key = (len(name), name[0], first_v, second_v)
            self.index.setdefault(key, []).append((name, meta))

        # Cities ---------------------------------------------------------
        # geonamescache already bundles top ~150k cities with population
        for city in gc.get_cities().values():
            pop = int(city.get("population", 0))
            if not pop:
                continue
            name_raw = city["name"]
            if " " in name_raw:
                continue  # ignore multi-word cities for consistency
            name = name_raw.lower()
            vpos = _vowel_positions(name)
            if not vpos:
                continue
            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)

            meta = {
                "type": "city",
                "region": city.get("continentcode"),
                "population": pop,
                "common": name in COMMON_CITIES,  # Only globally recognized cities are common
            }
            key = (len(name), name[0], first_v, second_v)
            self.index.setdefault(key, []).append((name, meta))

        # Deduplicate names preserving order --------------------------------
        for k, lst in self.index.items():
            seen = set()
            dedup: List[Tuple[str, Dict]] = []
            for name, meta in lst:
                if name not in seen:
                    dedup.append((name, meta))
                    seen.add(name)
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
        place_type: str | None = None,
        region: str | None = None,
        common: bool | None = None,
    ) -> List[str]:
        """Exact-letter query; returns matching place names."""
        results = self._lookup(length, first_letter, first_vowel_pos, second_vowel_pos)
        return self._filter(results, place_type, region, common)

    def query_category(
        self,
        length: int,
        category: int,
        first_vowel_pos: int,
        second_vowel_pos: int = 0,
        random_constraint: str | None = None,
        more_vowels: bool | None = None,
        place_type: str | None = None,
        region: str | None = None,
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
        return self._filter(dedup, place_type, region, common)

    # ------------------------------------------------------------------ #
    def _filter(
        self,
        items: List[Tuple[str, Dict]],
        place_type: str | None,
        region: str | None,
        common: bool | None,
    ) -> List[str]:
        out: List[str] = []
        for name, meta in items:
            if place_type and meta["type"] != place_type:
                continue
            if region and meta["region"] != region:
                continue
            if common is True and not meta["common"]:
                continue
            if common is False and meta["common"]:
                continue
            out.append(name)
        return out 