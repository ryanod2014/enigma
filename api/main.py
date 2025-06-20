from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path
import csv

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from fastapi.concurrency import run_in_threadpool
import concurrent.futures

from wordnet_vowel_index import (
    WordIndex,
    CATEGORY_MAP,
    HOLDABLE_SET,
    classify_subject,
)  # type: ignore
from place_index import PlaceIndex  # new index for countries/cities
from first_name_index import FirstNameIndex

# This function MUST be at the top level to be pickled for ProcessPoolExecutor
def build_all_indexes_sync() -> tuple[WordIndex, PlaceIndex, FirstNameIndex]:
    """Blocking, CPU-intensive function to build all indexes."""
    # This now runs in a separate process, so it creates its own instances
    print("[index] Starting background index build process...")
    built_index = WordIndex()
    built_places = PlaceIndex()
    built_names = FirstNameIndex()
    print("[index] Background index build process finished.")
    return built_index, built_places, built_names

app = FastAPI(title="20-Questions Word Helper API")

# ------------------------------------------------------------------ #
#   Defer heavy index builds to post-startup so health check passes  #
# ------------------------------------------------------------------ #

index: WordIndex | None = None
places_index: PlaceIndex | None = None
names_index: FirstNameIndex | None = None

# Guard flag so endpoints know when indexes are ready
_INDEX_READY: bool = False


async def _startup_build_indexes():
    """Run index build in a separate process to not block the event loop."""
    global index, places_index, names_index, _INDEX_READY
    
    loop = asyncio.get_running_loop()
    
    # Use ProcessPoolExecutor to run in a separate process and avoid GIL
    try:
        with concurrent.futures.ProcessPoolExecutor() as pool:
            # run_in_executor runs the target function in the process pool
            built_index, built_places, built_names = await loop.run_in_executor(
                pool, build_all_indexes_sync
            )
        
        # Assign the results back to the global variables
        index = built_index
        places_index = built_places
        names_index = built_names
        
        _INDEX_READY = True
        print("[index] All indexes assigned and ready.")
    except Exception as e:
        import logging
        logging.exception("Fatal error during index build", exc_info=e)


# Kick off background build right after startup
@app.on_event("startup")
async def startup_event():
    # Run the build in the background, don't await it here
    asyncio.create_task(_startup_build_indexes())

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
    freq: float = 1.0  # constant placeholder (kept for UI compatibility)
    lex: Optional[str] = None  # our 7-bucket category
    manmade: bool = False
    common: bool = True  # not used but front-end expects
    holdable: Optional[bool] = None
    origin: Optional[str] = None
    size: Optional[str] = None
    label: Optional[str] = None


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
    is_nickname: bool | None = None
    holdable: Optional[bool] = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    """Lightweight health-check endpoint required by Replit."""
    return PlainTextResponse("OK", status_code=200)


@app.post("/query")
def query(q: QueryIn):  # noqa: D401 – FastAPI creates docs automatically
    if not _INDEX_READY:
        raise HTTPException(status_code=503, detail="Indexes are building, please try again in a few moments.")
    if index is None:
        raise HTTPException(status_code=500, detail="Word index is not available.")

    if q.category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="category must be 1, 2, or 3")

    # `query_category` now returns a **list[Dict]** (word metadata), not just strings
    word_items = index.query_category(
        length=q.length,
        category=q.category,
        first_vowel_pos=q.v1,
        second_vowel_pos=q.v2,
        random_constraint=q.random,
        more_vowels=q.more_vowels,
        holdable=q.holdable,
    )

    # Start with the raw word list
    words = [item["word"] for item in word_items]

    # Optional filter by last letter category
    if q.last_category in CATEGORY_MAP:
        allowed_last = CATEGORY_MAP[q.last_category]
        filtered_items = [item for item in word_items if item["word"][-1].upper() in allowed_last]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items

    # First-letter MTSF filter
    if q.ms is True:
        filtered_items = [item for item in word_items if item["word"][0] in {'m','t','s','f','w'}]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items
    if q.ms is False:
        filtered_items = [item for item in word_items if item["word"][0] not in {'m','t','s','f','w'}]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items

    # Rhyme filter
    if q.rhyme is True:
        filtered_items = [item for item in word_items if item["word"] in RHYME_SET]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items
    if q.rhyme is False:
        filtered_items = [item for item in word_items if item["word"] not in RHYME_SET]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items

    # Optional filter: word must contain all specified letters
    if q.must_letters:
        needed = set(q.must_letters.upper())
        filtered_items = [item for item in word_items if needed.issubset(set(item["word"].upper()))]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items

    # V1 / V2 category filters
    if q.v1_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v1_cat]
        filtered_items = [item for item in word_items if _char_at(item["word"], q.v1) in allowed_set]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items
    if q.v2 > 0 and q.v2_cat in CATEGORY_MAP:
        allowed_set = CATEGORY_MAP[q.v2_cat]
        filtered_items = [item for item in word_items if _char_at(item["word"], q.v2) in allowed_set]
        words = [item["word"] for item in filtered_items]
        word_items = filtered_items

    resp: List[WordOut] = []

    for item in word_items:
        w = item["word"]

        resp.append(
            WordOut(
                word=w,
                freq=item.get("freq_count", 1),
                lex=item.get("cat", "unknown"),
                manmade=item.get("manmade", False),
                common=item.get("common", False),
                holdable=item.get("holdable"),
                origin=item.get("origin"),
                size=item.get("size"),
                label=item.get("label"),
            )
        )

    # Optional common filter
    if q.common is True:
        resp = [r for r in resp if r.common]
    elif q.common is False:
        resp = [r for r in resp if not r.common]

    resp.sort(key=lambda r: (-r.freq, r.word))

    # Build counts by bucket (lex)
    bucket_counts: Dict[str, int] = {}
    for r in resp:
        if r.lex:
            bucket_counts[r.lex] = bucket_counts.get(r.lex, 0) + 1

    # Calculate letter position entropy for filtering efficiency
    letter_positions = {}
    for i in range(1, 11):  # positions 1-10
        letter_counts = {}
        valid_words = 0
        for r in resp:
            if len(r.word) >= i:
                letter = r.word[i-1].upper()
                letter_counts[letter] = letter_counts.get(letter, 0) + 1
                valid_words += 1
        
        if valid_words > 0:
            # Calculate entropy - lower entropy = more informative position
            import math
            entropy = 0
            for count in letter_counts.values():
                p = count / valid_words
                if p > 0:
                    entropy -= p * math.log2(p)
            
            letter_positions[i] = {
                "entropy": round(entropy, 2),
                "distribution": letter_counts,
                "total_words": valid_words
            }
    
    # Sort positions by entropy (most informative first)
    sorted_positions = sorted(letter_positions.items(), key=lambda x: x[1]["entropy"])
    efficiency_ranking = [pos for pos, data in sorted_positions]

    return {
        "results": [r.dict() for r in resp], 
        "by_lexname": bucket_counts,
        "letter_efficiency": efficiency_ranking,
        "letter_analysis": letter_positions
    }


# ----------------------------------------------------------------------- #
#   Places endpoint
# ----------------------------------------------------------------------- #


@app.post("/query_place")
def query_place(q: PlaceQueryIn):
    if not _INDEX_READY:
        raise HTTPException(status_code=503, detail="Indexes are building, please try again in a few moments.")
    if places_index is None:
        raise HTTPException(status_code=500, detail="Places index is not available.")

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
    if not _INDEX_READY:
        raise HTTPException(status_code=503, detail="Indexes are building, please try again in a few moments.")
    if names_index is None:
        raise HTTPException(status_code=500, detail="Names index is not available.")

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
        # Fast constant-time meta retrieval using new helper
        meta = names_index.get_meta(n)
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
                is_nickname=meta.get("is_nickname"),
                holdable=meta.get("holdable"),
            )
        )

    # Prune ultra-obscure names (freq < 0.4)
    resp = [r for r in resp if r.freq >= 0.4]

    resp.sort(key=lambda r: (-r.freq, r.word))

    by_gender: Dict[str, int] = {}
    for r in resp:
        by_gender[r.lex] = by_gender.get(r.lex, 0) + 1

    return {"results": [r.dict() for r in resp], "by_lexname": by_gender}

# Mount static assets under /assets for CSS/JS files
dist_path = Path(__file__).resolve().parent.parent / "web" / "dist"
app.mount("/assets", StaticFiles(directory=dist_path / "assets"), name="assets")

# SPA fallback route for deep links (must be last)
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """Catch-all route to serve React app for client-side routing"""
    return FileResponse(dist_path / "index.html", media_type="text/html") 