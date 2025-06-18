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
import json
from functools import lru_cache as _lru
from pathlib import Path
from typing import Dict, List, Tuple

# --------------------------------------------------------------------------- #
# Legacy WordNet imports are optional now. We only fall back to them if our
# local JSONL dataset is missing. This keeps runtime lightweight and removes
# the hard dependency on NLTK when running in production.
# --------------------------------------------------------------------------- #

try:
    import nltk  # type: ignore
    from nltk.corpus import wordnet as wn  # type: ignore
    from nltk.stem import WordNetLemmatizer  # type: ignore

    try:
        from wordfreq import zipf_frequency  # type: ignore
    except ImportError:
        zipf_frequency = None  # type: ignore
except ImportError:  # NLTK not installed – totally fine for JSONL mode
    nltk = None  # type: ignore
    wn = None  # type: ignore
    WordNetLemmatizer = None  # type: ignore
    zipf_frequency = None  # type: ignore

import csv

# Make sure WordNet corpora are present -------------------------------------- #
try:
    wn.synsets("dog")
except LookupError:  # first run
    print("[setup] downloading WordNet…", file=sys.stderr)
    nltk.download("wordnet")

VOWELS = "AEIOUY"

# WordNet lemmatizer (only if WordNet available)
LEMMATIZER = WordNetLemmatizer() if WordNetLemmatizer else None

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

_PHYSICAL_ROOT = wn.synset('physical_entity.n.01') if wn else None

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


# holdable set loaded once
HOLDABLE_FILE = Path(__file__).resolve().parent / "data" / "holdable_flags.tsv"
HOLDABLE_SET: set[str] = set()
if HOLDABLE_FILE.is_file():
    with HOLDABLE_FILE.open() as hf:
        for line in hf:
            word, flag = line.strip().split("\t")
            if flag == "1":
                HOLDABLE_SET.add(word.lower())

# rhyme set loaded once
RHYME_FILE = Path(__file__).resolve().parent / "data" / "rhyme_flags.tsv"

# --------------------------------------------------------------------------- #
#   Simplified subject classification for 20-Questions nouns
# --------------------------------------------------------------------------- #

# Minimal keyword sets – enough to bucket >90 % of the 9k subjects.  Feel free to
# extend in future; mis-hits will fall back to "unknown" which still shows up.

ANIMALS = {
    'aardvark','alligator','ant','anteater','antelope','ape','armadillo','badger',
    'bat','bear','beaver','bee','beetle','bison','boar','buffalo','bull','butterfly',
    'camel','canary','caribou','cat','caterpillar','cheetah','chicken','chimpanzee',
    'chipmunk','cobra','cougar','cow','coyote','crab','crow','deer','dinosaur',
    'dog','dolphin','donkey','dove','dragonfly','duck','eagle','eel','elephant',
    'elk','falcon','ferret','finch','firefly','fish','flamingo','fly','fox','frog',
    'gazelle','giraffe','goat','goose','gorilla','grasshopper','grouse','hamster',
    'hawk','hedgehog','hippo','horse','hummingbird','iguana','jackal','jaguar',
    'jay','jellyfish','kangaroo','koala','ladybug','lamb','lemur','leopard',
    'lion','lizard','lobster','lynx','mole','monkey','moose','mosquito','moth',
    'mouse','mule','newt','octopus','opossum','orangutan','osprey','ostrich','otter',
    'owl','ox','panda','panther','parrot','peacock','pelican','penguin','pig','pigeon',
    'porcupine','puma','quail','rabbit','raccoon','rat','raven','reindeer','rhino',
    'robin','rooster','salamander','salmon','seal','shark','sheep','skunk','sloth',
    'snail','snake','sparrow','spider','squid','squirrel','starfish','stork','swan',
    'tiger','toad','trout','turkey','turtle','vulture','walrus','wasp','weasel',
    'whale','wolf','wombat','woodpecker','worm','yak','zebra'
}

FOOD_PLANT = {
    'apple','banana','bread','broccoli','burger','butter','cake','candy','carrot',
    'celery','cheese','cherry','chocolate','coconut','coffee','cookie','corn',
    'cucumber','donut','egg','fish','garlic','grape','honey','ice','jam','juice',
    'kale','lemon','lettuce','lime','lobster','mango','meat','milk','mushroom',
    'noodle','nut','oat','oil','onion','orange','pasta','peach','pear','pepper',
    'pickle','pie','pizza','pork','potato','pumpkin','rice','salad','salt',
    'sandwich','sausage','soup','spinach','steak','sugar','tea','tomato','turkey',
    'water','watermelon','wine','yogurt','zucchini',
    # plants / trees
    'tree','oak','pine','maple','birch','cedar','spruce','willow','cactus','flower',
    'rose','tulip','daisy','orchid','fern','ivy','bamboo','moss','algae'
}

CLOTHING = {
    'hat','cap','helmet','shirt','tshirt','t-shirt','sweater','hoodie','jacket',
    'coat','vest','pants','trousers','shorts','jeans','leggings','skirt','dress',
    'miniskirt','bikini','bra','underwear',
    'socks','sock','shoe','shoes','boot','boots','sandal','glove','gloves','scarf',
    'belt','tie','watch','ring','necklace','bracelet','earring','earrings','goggles',
    'glasses','spectacles','umbrella','backpack','bag','purse','wallet'
}

FURNITURE = {
    'bed','sofa','couch','chair','armchair','table','desk','dresser','cabinet',
    'shelf','bookshelf','stool','bench','sofabed','closet','wardrobe','door',
    'window','lamp','light','fan','mirror','rug','carpet','toilet','sink','shower',
    'bathtub','fridge','freezer','stove','oven','microwave','dishwasher',
    'vacuum','washer','dryer'
}

OBJECT_TOOL = {
    'hammer','nail','screw','screwdriver','wrench','pliers','scissors','knife',
    'fork','spoon','spatula','pan','pot','bowl','cup','mug','plate','bottle',
    'jar','box','bag','bucket','can','rope','string','tape','glue','paper',
    'pencil','pen','marker','crayon','brush','comb','key','lock','phone','camera',
    'clock','watch','radio','tablet','laptop','computer','mouse','keyboard','drum',
    'guitar','violin','trumpet','ball','bat','racket','frisbee','kite','toy',
    'dice','card','coin','tool','fireworks','metalwork'
}

VEHICLE_MACHINE = {
    'car','truck','bus','bike','bicycle','motorcycle','scooter','train','plane',
    'motorbike','firetruck','spaceship','helicopter','boat','ship','submarine',
    'tank','rocket','spaceship','robot','computer','engine','motor','machine'
}

NATURAL_MATERIAL = {
    'rock','stone','pebble','granite','marble','sand','dirt','soil','mud','clay',
    'dust','ash','coal','charcoal','diamond','gold','silver','copper','iron','steel',
    'bronze','brass','aluminum','lead','mercury','water','ice','steam','snow',
    'rain','cloud','fog','wind','air','fire','lava','magma','smoke','gas','oil',
    'salt','sugar','oxygen','hydrogen','helium','planet','star','moon','comet',
    'asteroid','mountain','hill','valley','river','lake','ocean','sea','beach'
}

PERSON_SUFFIXES = ('er','or','ist','ian')  # crude heuristic


def classify_subject(word: str) -> tuple[str, bool]:
    """Return (bucket, manmade).  If bucket == 'person' caller may choose to skip."""
    w = word.lower()

    if w in ANIMALS:
        return 'animal', False
    if w in FOOD_PLANT:
        return 'food-plant', False
    if w in CLOTHING:
        return 'clothing', True
    if w in FURNITURE:
        return 'furniture', True
    if w in VEHICLE_MACHINE:
        return 'vehicle-machine', True
    if w in OBJECT_TOOL:
        return 'object-tool', True
    if w in NATURAL_MATERIAL:
        return 'natural-material', False

    # crude person detection
    if len(w) > 4 and w.endswith(PERSON_SUFFIXES):
        return 'person', False

    return 'unknown', False

class WordIndex:
    """Build once, then lightning‑fast `query()` calls."""

    def __init__(self):
        self.index: Dict[Tuple[int, str, int, int], List[Dict[str, any]]] = {}
        self._build()

    def _build(self) -> None:
        """Build the in-memory index.

        Preference order:
        1. If `data/combined_twentyquestions.jsonl` is present → use it (fast).
        2. Fallback to the original WordNet crawl (slow, requires NLTK).
        """

        jsonl_path = Path(__file__).resolve().parent / "data" / "combined_twentyquestions.jsonl"
        if jsonl_path.is_file():
            self._build_from_jsonl(jsonl_path)
            return  # ✅ done – no need for WordNet

        if not wn:
            raise RuntimeError("NLTK/WordNet not available and JSONL dataset missing – cannot build index.")

        # ------------------------------------------------------------------ #
        # Legacy WordNet path (kept for CLI compatibility only)
        # ------------------------------------------------------------------ #
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

                # Add holdable flag
                is_holdable_flag = w in HOLDABLE_SET

                key = (len(w.replace(" ", "")), w[0], first_v, second_v)
                self.index.setdefault(key, []).append(
                    {"word": w, "holdable": is_holdable_flag}
                )

        # deduplicate while preserving order
        for k, lst in self.index.items():
            seen = set()
            deduped = []
            for item in lst:
                if item["word"] not in seen:
                    deduped.append(item)
                    seen.add(item["word"])
            self.index[k] = deduped

        # After main build loop, fill in any missing metadata so UI size/manmade filters work
        self._fill_missing_metadata()

        print(f"[index] done – {len(self.index):,} unique (len,letter,v1,v2) keys", file=sys.stderr)

    # ------------------------------------------------------------------ #
    @_lru(maxsize=8_192)
    def query(
        self,
        length: int,
        first_letter: str = "",
        first_vowel_pos: int = 0,
        second_vowel_pos: int = 0,
        category: int = 0,
        holdable: bool | None = None,
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
        holdable: bool | None = None,
    ) -> List[Dict[str, any]]:
        """Advanced query using *first-letter category* instead of exact letter.

        Args:
            length: total characters (spaces ignored)
            category: 1 / 2 / 3 (see CATEGORY_MAP)
            first_vowel_pos: 1-based index of first vowel
            second_vowel_pos: 1-based index of second vowel, or 0 if none
            random_constraint: optional string like "5S" meaning *s* is 5th letter
            more_vowels: if True → word has >2 vowels; if False → ≤2 vowels; if None ignore
            holdable: if True → only holdable words; if False → only non-holdable words; if None ignore
        """
        if category not in CATEGORY_MAP:
            raise ValueError(f"Unknown category {category}. Must be 1, 2, or 3.")

        # gather candidates from all letters in the category
        candidates: List[Dict[str, any]] = []
        for letter in CATEGORY_MAP[category]:
            key = (length, letter.lower(), first_vowel_pos, second_vowel_pos)
            candidates.extend(self.index.get(key, []))

        # deduplicate (preserve order)
        seen_words: set[str] = set()
        deduped = []
        for item in candidates:
            if item["word"] not in seen_words:
                deduped.append(item)
                seen_words.add(item["word"])

        # Apply holdable filter
        if holdable is True:
            deduped = [item for item in deduped if item["holdable"]]
        elif holdable is False:
            deduped = [item for item in deduped if not item["holdable"]]

        # Apply optional filters ------------------------------------------------
        if random_constraint:
            m = RANDOM_LETTER_RE.match(random_constraint.upper())
            if not m:
                raise ValueError(
                    "random_constraint must look like '5S' (position followed by letter)"
                )
            pos, letter = int(m.group(1)), m.group(2).lower()
            deduped = [item for item in deduped if _char_at(item["word"], pos) == letter]

        if more_vowels is not None:
            if more_vowels:
                deduped = [item for item in deduped if len(vowel_positions(item["word"])) > 2]
            else:
                deduped = [item for item in deduped if len(vowel_positions(item["word"])) <= 2]

        return deduped

    # ------------------------------------------------------------------ #
    def _build_from_jsonl(self, jsonl_path: Path) -> None:
        """Populate *self.index* from the local 20-Questions JSONL file."""
        print(f"[index] building from {jsonl_path.name}…", file=sys.stderr)

        subject_counts: dict[str, int] = {}

        with jsonl_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip malformed lines

                subj_raw = str(obj.get("subject", "")).strip().lower()

                # Basic sanity checks ------------------------------------------------
                if not subj_raw:
                    continue
                if " " in subj_raw:  # ignore multi-word for now (keeps length logic)
                    continue
                if not re.fullmatch(r"[a-z]+", subj_raw):
                    continue

                # Count occurrences (frequency in dataset)
                subject_counts[subj_raw] = subject_counts.get(subj_raw, 0) + 1

        # Now process unique subjects with their counts
        for subj_raw, count in subject_counts.items():
            vpos = vowel_positions(subj_raw)
            if not vpos:
                continue  # must contain at least one vowel

            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)

            bucket, man_flag = classify_subject(subj_raw)

            if bucket == 'person':
                continue  # skip persons/characters entirely

            # Common = appears 3+ times in dataset (somewhat arbitrary threshold)
            is_common = count >= 3

            key = (len(subj_raw), subj_raw[0], first_v, second_v)
            self.index.setdefault(key, []).append({
                "word": subj_raw,
                "holdable": subj_raw in HOLDABLE_SET,
                "cat": bucket,
                "manmade": man_flag,
                "common": is_common,
                "freq_count": count,
            })

        # Deduplicate while preserving order (probably unnecessary but safe)
        for k, lst in self.index.items():
            seen_words: set[str] = set()
            deduped: List[Dict[str, any]] = []
            for item in lst:
                if item["word"] not in seen_words:
                    deduped.append(item)
                    seen_words.add(item["word"])
            self.index[k] = deduped

        print(f"[index] done – {len(self.index):,} keys from JSONL", file=sys.stderr)

    # ------------------------------------------------------------------ #
    def _fill_missing_metadata(self) -> None:
        """Add `cat` and `manmade` flags to items that missed them during the
        fallback WordNet path. Also ensure `holdable` is always present.
        """
        for lst in self.index.values():
            for item in lst:
                # Ensure holdable boolean exists (may already be present)
                if 'holdable' not in item:
                    item['holdable'] = item['word'] in HOLDABLE_SET

                # Skip if already labeled
                if 'manmade' in item and 'cat' in item:
                    continue

                bucket, man_flag = classify_subject(item['word'])
                item['manmade'] = man_flag
                item['cat'] = bucket


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