from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path
import csv

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wordnet_vowel_index import (
    WordIndex,
    CATEGORY_MAP,
    zipf_frequency,
    PHYSICAL_LEXNAMES,
    is_physical,
    HOLDABLE_SET,
)  # type: ignore
from nltk.corpus import wordnet as wn
from place_index import PlaceIndex  # new index for countries/cities
from first_name_index import FirstNameIndex

app = FastAPI(title="20-Questions Word Helper API")

# Build the index once at import time – ~1 s
index = WordIndex()
places_index = PlaceIndex()  # builds at import
names_index = FirstNameIndex()

# rhyme set for nouns filter
RHYME_FILE = Path(__file__).resolve().parent.parent / "data" / "rhyme_flags.tsv"
RHYME_SET: set[str] = set()
if RHYME_FILE.is_file():
    with RHYME_FILE.open() as rf:
        reader = csv.reader(rf, delimiter="\t")
        for row in reader:
            if row and row[1] == "1":
                RHYME_SET.add(row[0].lower())

# Helper to get char at 1-based position ignoring spaces
def _char_at(word: str, pos: int) -> str:
    clean = word.replace(" ", "")
    return clean[pos - 1].upper() if 1 <= pos <= len(clean) else ""


class QueryIn(BaseModel):
    length: int
    category: int
    v1: int
    v2: int = 0
    v1_cat: Optional[int] = None  # category for letter at V1 position
    v2_cat: Optional[int] = None  # category for letter at V2 position
    random: Optional[str] = None
    more_vowels: Optional[bool] = None
    common: Optional[bool] = None  # True = common only, False = uncommon only, None = both
    last_category: Optional[int] = None  # optional filter on last letter category
    must_letters: Optional[str] = None  # letters that must be present somewhere in the word
    rhyme: Optional[bool] = None
    ms: Optional[bool] = None  # restrict to first letter M/T/S/F
    holdable: Optional[bool] = None


class WordOut(BaseModel):
    word: str
    freq: float
    lex: Optional[str]
    manmade: bool
    common: bool  # True if frequent (Zipf ≥4.0 or count≥1)
    holdable: Optional[bool] = None


# --------------------------- Places models ----------------------------- #

class PlaceQueryIn(BaseModel):
    length: int
    category: int
    v1: int
    v2: int = 0
    v1_cat: Optional[int] = None
    v2_cat: Optional[int] = None
    last_category: Optional[int] = None  # optional filter on last letter category
    place_type: Optional[str] = None  # 'city' | 'country'
    region: Optional[str] = None      # continent code e.g. 'EU'
    common: Optional[bool] = None     # True = common only (1M+ pop), False = uncommon only
    random: Optional[str] = None
    more_vowels: Optional[bool] = None
    must_letters: Optional[str] = None
    rhyme: Optional[bool] = None
    ms: Optional[bool] = None
    holdable: Optional[bool] = None


class PlaceOut(BaseModel):
    word: str
    freq: float  # use population in millions for cities, else 1.0
    lex: str     # 'city' or 'country' for UI category grouping
    manmade: bool = False  # always False to keep existing UI logic
    common: bool | None = None  # populous cities or well-known country flag
    region: str | None = None
    holdable: Optional[bool] = None


# --------------------------- Names models ----------------------------- #

class NameQueryIn(BaseModel):
    length: int
    category: int
    v1: int
    v2: int = 0
    v1_cat: Optional[int] = None
    v2_cat: Optional[int] = None
    gender: Optional[str] = None  # 'm' | 'f' | 'u'
    origin: Optional[str] = None  # ISO country
    common: Optional[bool] = None  # True common only
    random: Optional[str] = None
    more_vowels: Optional[bool] = None
    last_category: Optional[int] = None
    nickname: Optional[str] = None  # 'nickname'|'multiple'|'none'
    must_letters: Optional[str] = None  # letters that must appear
    rhyme: Optional[bool] = None
    ms: Optional[bool] = None
    holdable: Optional[bool] = None


class NameOut(BaseModel):
    word: str
    freq: float
    lex: str  # use gender as lex category
    manmade: bool = False  # placeholder to reuse UI logic
    origin: str | None = None
    common: bool | None = None
    has_nickname: bool | None = None
    nick_count: int | None = None
    holdable: Optional[bool] = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/query")
def query(q: QueryIn):  # noqa: D401 – FastAPI creates docs automatically
    if q.category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="category must be 1, 2, or 3")

    # `query_category` now returns a **list[str]** (words), not dicts
    words_raw = index.query_category(
        length=q.length,
        category=q.category,
        first_vowel_pos=q.v1,
        second_vowel_pos=q.v2,
        random_constraint=q.random,
        more_vowels=q.more_vowels,
        holdable=q.holdable,
    )

    # Start with the raw word list
    words = list(words_raw)

    # Optional filter by last letter category
    if q.last_category in CATEGORY_MAP:
        allowed_last = CATEGORY_MAP[q.last_category]
        words = [w for w in words if w[-1].upper() in allowed_last]

    # First-letter MTSF filter
    if q.ms is True:
        words = [w for w in words if w[0] in {'m','t','s','f','w'}]
    if q.ms is False:
        words = [w for w in words if w[0] not in {'m','t','s','f','w'}]

    # Rhyme filter
    if q.rhyme is True:
        words = [w for w in words if w in RHYME_SET]
    if q.rhyme is False:
        words = [w for w in words if w not in RHYME_SET]

    # Optional filter: word must contain all specified letters
    if q.must_letters:
        needed = set(q.must_letters.upper())
        words = [w for w in words if needed.issubset(set(w.upper()))]

    # V1 / V2 category filters
    if q.v1_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v1_cat]
        words = [w for w in words if _char_at(w, q.v1) in allowed_set]
    if q.v2 > 0 and q.v2_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v2_cat]
        words = [w for w in words if _char_at(w, q.v2) in allowed_set]

    resp: List[WordOut] = []

    for w in words:
        if callable(zipf_frequency):
            freq_metric = float(zipf_frequency(w, "en"))
            is_common = freq_metric >= 4.0
        else:
            counts = [lem.count() for syn in wn.synsets(w) for lem in syn.lemmas() if lem.name() == w]
            freq_metric = float(max(counts, default=0))
            is_common = freq_metric >= 1

        if q.common is True and not is_common:
            continue
        if q.common is False and is_common:
            continue

        lex = None
        manmade_flag = False
        for syn in wn.synsets(w, pos=wn.NOUN):
            if is_physical(syn):
                lex = syn.lexname()
                manmade_flag = any(p in {wn.synset('artifact.n.01'), wn.synset('vehicle.n.01')} for p in syn.closure(lambda x: x.hypernyms()))
                break
        if lex is None:
            continue

        resp.append(
            WordOut(
                word=w,
                freq=freq_metric,
                lex=lex,
                manmade=manmade_flag,
                common=is_common,
                holdable=w in HOLDABLE_SET,
            )
        )

    resp.sort(key=lambda r: (-r.freq, r.word))

    by_lexname: Dict[str, int] = {}
    for r in resp:
        key = r.lex or "unknown"
        by_lexname[key] = by_lexname.get(key, 0) + 1

    return {"results": [r.dict() for r in resp], "by_lexname": by_lexname}


# ----------------------------------------------------------------------- #
#   Places endpoint
# ----------------------------------------------------------------------- #


@app.post("/query_place")
def query_place(q: PlaceQueryIn):
    if q.category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="category must be 1, 2, or 3")

    words = places_index.query_category(
        length=q.length,
        category=q.category,
        first_vowel_pos=q.v1,
        second_vowel_pos=q.v2,
        random_constraint=q.random,
        more_vowels=q.more_vowels,
        place_type=q.place_type,
        region=q.region,
        common=q.common,
        holdable=q.holdable,
    )

    # Optional filter by last letter category
    if q.last_category in CATEGORY_MAP:
        allowed_last = CATEGORY_MAP[q.last_category]
        words = [w for w in words if w[-1].upper() in allowed_last]

    # First-letter MTSF filter
    if q.ms is True:
        words = [w for w in words if w[0] in {'m','t','s','f','w'}]
    if q.ms is False:
        words = [w for w in words if w[0] not in {'m','t','s','f','w'}]

    # Optional filters
    if q.rhyme is True:
        words = [w for w in words if any(meta.get("rhyme") for lst in places_index.index.values() for n,meta in lst if n==w)]
    if q.rhyme is False:
        words = [w for w in words if all(not meta.get("rhyme") for lst in places_index.index.values() for n,meta in lst if n==w)]

    # Must contain specific letters
    if q.must_letters:
        needed = set(q.must_letters.upper())
        words = [w for w in words if needed.issubset(set(w.upper()))]

    # V1/V2 category filters
    if q.v1_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v1_cat]
        words = [w for w in words if _char_at(w, q.v1) in allowed_set]
    if q.v2 > 0 and q.v2_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v2_cat]
        words = [w for w in words if _char_at(w, q.v2) in allowed_set]

    # Build response list with pseudo frequency (population millions for cities)
    resp: List[PlaceOut] = []
    for w in words:
        # Retrieve meta via a secondary exact query to look up stored data
        meta = None
        # Attempt to fetch via internal lookup function on raw index (not public)
        for lst in places_index.index.values():
            for name, md in lst:
                if name == w:
                    meta = md
                    break
            if meta:
                break

        if not meta:
            continue  # should not happen

        if meta["type"] == "city":
            freq_val = meta["population"] / 1_000_000.0  # millions
            lex_val = "city"
        else:
            freq_val = 1.0  # default
            lex_val = "country"

        resp.append(
            PlaceOut(
                word=w,
                freq=freq_val,
                lex=lex_val,
                common=meta.get("common"),
                region=meta.get("region"),
                holdable=meta.get("holdable"),
            )
        )

    resp.sort(key=lambda r: (-r.freq, r.word))

    by_lexname: Dict[str, int] = {}
    for r in resp:
        key = r.lex
        by_lexname[key] = by_lexname.get(key, 0) + 1

    return {"results": [r.dict() for r in resp], "by_lexname": by_lexname}


# ----------------------------------------------------------------------- #
#   Names endpoint
# ----------------------------------------------------------------------- #

@app.post("/query_first_name")
def query_first_name(q: NameQueryIn):
    if q.category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="category must be 1, 2, or 3")

    names = names_index.query_category(
        length=q.length,
        category=q.category,
        first_vowel_pos=q.v1,
        second_vowel_pos=q.v2,
        random_constraint=q.random,
        more_vowels=q.more_vowels,
        gender=q.gender,
        origin=q.origin,
        common=q.common,
        nickname=q.nickname,
        rhyme=q.rhyme,
        holdable=q.holdable,
    )

    # last letter category filter
    if q.last_category in CATEGORY_MAP:
        allowed_last = CATEGORY_MAP[q.last_category]
        names = [n for n in names if n[-1].upper() in allowed_last]

    # optional must_letters filter
    if q.must_letters:
        needed = set(q.must_letters.upper())
        names = [n for n in names if needed.issubset(set(n.upper()))]

    # V1/V2 category filters
    if q.v1_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v1_cat]
        names = [n for n in names if _char_at(n, q.v1) in allowed_set]
    if q.v2 > 0 and q.v2_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v2_cat]
        names = [n for n in names if _char_at(n, q.v2) in allowed_set]

    resp: List[NameOut] = []

    # Build NameOut list
    for n in names:
        # fetch meta via exact lookup
        meta = None
        for lst in names_index.index.values():
            for name, md in lst:
                if name == n:
                    meta = md
                    break
            if meta:
                break
        if not meta:
            continue

        count = meta.get("count", 0)
        freq_val = (count / 10_000.0) if count else 0.1
        is_common = meta.get("rank_us", 0) and meta.get("rank_us", 0) <= 200
        resp.append(
            NameOut(
                word=n,
                freq=freq_val,
                lex=meta.get("gender", "u"),
                origin=meta.get("origin"),
                common=is_common,
                has_nickname=meta.get("has_nickname"),
                nick_count=meta.get("nick_count", 0),
                holdable=meta.get("holdable"),
            )
        )

    resp.sort(key=lambda r: (-r.freq, r.word))

    by_gender: Dict[str, int] = {}
    for r in resp:
        by_gender[r.lex] = by_gender.get(r.lex, 0) + 1

    return {"results": [r.dict() for r in resp], "by_lexname": by_gender} 