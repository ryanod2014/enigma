from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from wordnet_vowel_index import (
    WordIndex,
    CATEGORY_MAP,
    zipf_frequency,
    PHYSICAL_LEXNAMES,
    is_physical,
)  # type: ignore
from nltk.corpus import wordnet as wn

app = FastAPI(title="20-Questions Word Helper API")

# Build the index once at import time – ~1 s
index = WordIndex()


class QueryIn(BaseModel):
    length: int
    category: int
    v1: int
    v2: int = 0
    random: Optional[str] = None
    more_vowels: Optional[bool] = None
    common: Optional[bool] = None  # True = common only, False = uncommon only, None = both
    last_category: Optional[int] = None  # optional filter on last letter category
    must_letters: Optional[str] = None  # letters that must be present somewhere in the word


class WordOut(BaseModel):
    word: str
    freq: float
    lex: Optional[str]
    manmade: bool


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/query")
def query(q: QueryIn):  # noqa: D401 – FastAPI creates docs automatically
    if q.category not in CATEGORY_MAP:
        raise HTTPException(status_code=400, detail="category must be 1, 2, or 3")

    words = index.query_category(
        q.length,
        q.category,
        q.v1,
        q.v2,
        random_constraint=q.random,
        more_vowels=q.more_vowels,
    )

    # Optional filter by last letter category
    if q.last_category in CATEGORY_MAP:
        allowed_last = CATEGORY_MAP[q.last_category]
        words = [w for w in words if w[-1].upper() in allowed_last]

    # Optional filter: word must contain all specified letters
    if q.must_letters:
        needed = set(q.must_letters.upper())
        words = [w for w in words if needed.issubset(set(w.upper()))]

    # Build response list with frequency + lexname
    resp: List[WordOut] = []

    # Precompute man-made root synsets
    MAN_MADE_ROOTS = {wn.synset('artifact.n.01'), wn.synset('vehicle.n.01')}

    for w in words:
        # Determine frequency (zipf or count)
        if callable(zipf_frequency):
            freq_metric = float(zipf_frequency(w, "en"))
            is_common = freq_metric >= 4.0  # zipf 4+ common words
        else:
            counts = [lem.count() for syn in wn.synsets(w) for lem in syn.lemmas() if lem.name() == w]
            freq_metric = float(max(counts, default=0))
            is_common = freq_metric >= 1  # >=1 occurrences common

        # Apply optional common/uncommon filter
        if q.common is True and not is_common:
            continue
        if q.common is False and is_common:
            continue

        # Determine the first *physical* synset for the word
        lex = None
        manmade_flag = False
        for syn in wn.synsets(w, pos=wn.NOUN):
            # Re-use the robust `is_physical` helper used when building the index
            if is_physical(syn):
                lex = syn.lexname()
                # Determine man-made vs natural by walking hypernym tree
                manmade_flag = any(p in MAN_MADE_ROOTS for p in syn.closure(lambda x: x.hypernyms()))
                break
        if lex is None:
            # No clearly physical sense found → skip the word
            continue

        resp.append(WordOut(word=w, freq=freq_metric, lex=lex, manmade=manmade_flag))

    # Sort by frequency descending, then alpha
    resp.sort(key=lambda r: (-r.freq, r.word))

    # Aggregate counts by lexname for filter tabs
    by_lexname: Dict[str, int] = {}
    for r in resp:
        key = r.lex or "unknown"
        by_lexname[key] = by_lexname.get(key, 0) + 1

    return {"results": [r.dict() for r in resp], "by_lexname": by_lexname} 