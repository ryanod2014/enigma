#!/usr/bin/env python3
"""Export CSV of country collisions for key F1+V1+LL where collisions >5.
Columns: code,country,region sorted by code groups (same order as output)
"""
import re
from collections import defaultdict

VOWELS="AEIOUY"
CAT1={"A","E","I","F","H","K","L","M","N","T","V","W","X","Y","Z"}
CAT2={"C","G","O","J","Q","S","U"}
CAT3={"B","D","P","R","J","U"}

COUNTRY_TEXT="""<placeholder>"""
# We'll load original text from existing script to keep single source
import importlib.util, pathlib, sys
spec=importlib.util.spec_from_file_location('ck','scripts/analyze_country_keys.py')
ck=importlib.util.module_from_spec(spec); spec.loader.exec_module(ck)
COUNTRY_TEXT=ck.COUNTRY_TEXT

REGION_MAP={
    # Europe
    'Turkey':'Europe', 'Norway':'Europe','Hungary':'Europe','Malta':'Europe','North Macedonia':'Europe','Lithuania':'Europe','Latvia':'Europe','Germany':'Europe','Portugal':'Europe','Denmark':'Europe','Belgium':'Europe','Romania':'Europe','Bulgaria':'Europe','Bosnia and Herzegovina':'Europe','Italy':'Europe','Austria':'Europe','Serbia':'Europe','Albania':'Europe','Estonia':'Europe','Croatia':'Europe','Greece':'Europe','Sweden':'Europe','Slovenia':'Europe','Slovakia':'Europe','Netherlands':'Europe','Luxembourg':'Europe','Georgia':'Europe',
    # Asia / Middle East
    'Turkey':'Europe','Vietnam':'Asia','Malaysia':'Asia','Lebanon':'Middle East','Kazakhstan':'Asia','Mongolia':'Asia','Nepal':'Asia','Taiwan':'Asia','Japan':'Asia','South Korea':'Asia','Singapore':'Asia','Cambodia':'Asia','India':'Asia','Indonesia':'Asia','Israel':'Middle East','Armenia':'Asia','Azerbaijan':'Asia','Sri Lanka':'Asia','Maldives':'Asia','Laos':'Asia','China':'Asia',
    # Africa
    'Kenya':'Africa','Tanzania':'Africa','South Africa':'Africa','Egypt':'Africa','Morocco':'Africa','Mauritius':'Africa',
    # Americas
    'Fiji':'Oceania','Nicaragua':'North America','Canada':'North America','Colombia':'South America','Costa Rica':'North America','Cuba':'North America','Guatemala':'North America','Jordan':'Middle East','Saudi Arabia':'Middle East','Bolivia':'South America','Panama':'North America','Belize':'North America','Paraguay':'South America','Bahrain':'Middle East','Spain':'Europe','Mexico':'North America','Argentina':'South America','Chile':'South America','Honduras':'North America',
}

def categories(ch):
    """Return list of all category numbers this char belongs to (1..3)."""
    up=ch.upper()
    cats=[]
    if up in CAT1:
        cats.append(1)
    if up in CAT2:
        cats.append(2)
    if up in CAT3:
        cats.append(3)
    return cats or [1]

def v1(word):
    for i,ch in enumerate(word.upper(),1):
        if ch in VOWELS:
            return i
    return 0

def extract_countries(text:str):
    out=[]; seen=set()
    for line in text.strip().splitlines():
        name=re.split(r'\s*\(',line.strip(),1)[0].strip()
        if name.lower() not in seen:
            out.append(name); seen.add(name.lower())
    return out

countries=extract_countries(COUNTRY_TEXT)

buckets=defaultdict(list)
for n in countries:
    vpos=v1(n)
    for f_cat in categories(n[0]):
        for l_cat in categories(n[-1]):
            key=(f_cat, vpos, l_cat)
            buckets[key].append(n)

print('code,country,region')
for code in sorted(buckets, key=lambda k: (-len(buckets[k]), k)):
    for c in buckets[code]:
        region=REGION_MAP.get(c,'Unknown')
        print(f"{code},{c},{region}") 