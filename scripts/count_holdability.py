#!/usr/bin/env python3
"""count_holdability.py
Roughly estimate how many WordIndex physical nouns are "holdable" vs clearly too large.
Criteria:
  • Exclude if lexname in noun.location
  • Exclude if definition contains size keywords (building, vehicle, mountain, river, ocean, hotel, house, city, country, planet, tree, road, bridge)
Print counts and percentage.
"""
from __future__ import annotations
import re, sys
from nltk.corpus import wordnet as wn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wordnet_vowel_index import WordIndex

def is_large(word:str)->bool:
    syns=wn.synsets(word, pos='n')
    if not syns:
        return False
    syn=syns[0]
    if syn.lexname()=='noun.location':
        return True
    big_kw=re.compile(r"\b(building|vehicle|mountain|river|ocean|sea|lake|hotel|house|city|country|planet|tree|road|bridge|street|train|ship|aircraft|car|truck|boat|tower|castle|factory)\b")
    if big_kw.search(syn.definition().lower()):
        return True
    return False

idx=WordIndex()
nouns={w for lst in idx.index.values() for w in lst}
holdable=0
large=0
for w in nouns:
    if is_large(w):
        large+=1
    else:
        holdable+=1

total=len(nouns)
print(f"Total nouns: {total}")
print(f"Holdable: {holdable} ({holdable/total*100:.1f}%)")
print(f"Too large: {large} ({large/total*100:.1f}%)") 