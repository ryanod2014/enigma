#!/usr/bin/env python3
"""
Analyze the first names dictionary to check total unique keys and statistics.
"""

import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple

VOWELS = "AEIOUY"

def vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1‑based positions of vowels in *word* (case‑insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)

def analyze_names():
    """Analyze the first_names.tsv file."""
    
    names_path = Path("data/first_names.tsv")
    if not names_path.exists():
        print(f"ERROR: {names_path} not found!")
        return
    
    print("=== FIRST NAMES DICTIONARY ANALYSIS ===\n")
    
    # Statistics counters
    total_entries = 0
    unique_names = set()
    valid_names = set()
    
    # Key analysis
    unique_keys = set()
    
    # Category breakdowns
    length_stats = Counter()
    first_letter_stats = Counter()
    v1_stats = Counter() 
    v2_stats = Counter()
    gender_stats = Counter()
    origin_stats = Counter()
    common_stats = Counter()
    
    # FL bucket mapping (from first_name_index.py)
    CATEGORY_MAP = {
        1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
        2: {"C", "G", "O", "J", "Q", "S", "U"},
        3: {"B", "D", "P", "R", "J", "U"},
    }
    
    def get_fl_bucket(letter: str) -> int:
        """Get the FL bucket (category) for a letter."""
        letter = letter.upper()
        for bucket, letters in CATEGORY_MAP.items():
            if letter in letters:
                return bucket
        return 0  # unknown
    
    print("Reading first_names.tsv file...")
    
    with names_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row_num, row in enumerate(reader, 1):
            if not row or row[0].startswith("#"):
                continue
                
            total_entries += 1
            
            # Parse row: name, gender, origin, rank_us, rank_world
            if len(row) < 5:
                continue
                
            name = row[0].lower()
            gender = row[1].lower()
            origin = row[2].upper()
            rank_us = int(row[3]) if row[3] else 0
            rank_world = int(row[4]) if row[4] else 0
            
            # Basic sanity checks
            if not name:
                continue
            if " " in name:  # ignore multi-word names
                continue
                
            unique_names.add(name)
            
            # Check vowel positions
            vpos = vowel_positions(name)
            if not vpos:
                continue  # must contain at least one vowel
                
            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)
            
            # This name passes all filters
            valid_names.add(name)
            
            # Generate key
            key = (len(name), name[0], first_v, second_v)
            unique_keys.add(key)
            
            # Update statistics
            length_stats[len(name)] += 1
            first_letter_stats[name[0]] += 1
            v1_stats[first_v] += 1
            v2_stats[second_v] += 1
            
            # Gender stats
            if gender in {"m", "f"}:
                gender_stats[gender] += 1
            else:
                gender_stats["u"] += 1  # unisex/unknown
            
            # Origin stats
            if len(origin) == 2:
                origin_stats[origin] += 1
            else:
                origin_stats["UNKNOWN"] += 1
            
            # Common stats (top 200 US or world)
            is_common = (rank_us and rank_us <= 200) or (rank_world and rank_world <= 200)
            common_stats[is_common] += 1
            
            fl_bucket = get_fl_bucket(name[0])
    
    # Print results
    print(f"\n=== RESULTS ===")
    print(f"Total TSV entries: {total_entries:,}")
    print(f"Unique raw names: {len(unique_names):,}")
    print(f"Valid filtered names: {len(valid_names):,}")
    print(f"TOTAL UNIQUE KEYS: {len(unique_keys):,}")
    
    print(f"\n=== LENGTH DISTRIBUTION ===")
    for length in sorted(length_stats.keys()):
        print(f"  {length} letters: {length_stats[length]:,} names")
    
    print(f"\n=== FIRST LETTER (FL) BUCKETS ===")
    for bucket in sorted(CATEGORY_MAP.keys()):
        letters = sorted(CATEGORY_MAP[bucket])
        count = sum(first_letter_stats[letter.lower()] for letter in letters)
        print(f"  Bucket {bucket} ({', '.join(letters)}): {count:,} names")
    
    print(f"\n=== FIRST VOWEL POSITION (V1) ===")
    for pos in sorted(v1_stats.keys()):
        print(f"  Position {pos}: {v1_stats[pos]:,} names")
    
    print(f"\n=== SECOND VOWEL POSITION (V2) ===")
    for pos in sorted(v2_stats.keys()):
        if pos == 0:
            print(f"  No second vowel (0): {v2_stats[pos]:,} names")
        else:
            print(f"  Position {pos}: {v2_stats[pos]:,} names")
    
    print(f"\n=== GENDER DISTRIBUTION ===")
    for gender in sorted(gender_stats.keys()):
        gender_name = {"m": "Male", "f": "Female", "u": "Unisex/Unknown"}[gender]
        print(f"  {gender_name}: {gender_stats[gender]:,} names")
    
    print(f"\n=== TOP ORIGINS ===")
    top_origins = sorted(origin_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    for origin, count in top_origins:
        print(f"  {origin}: {count:,} names")
    
    print(f"\n=== COMMON vs UNCOMMON ===")
    print(f"  Common (top 200): {common_stats[True]:,} names")
    print(f"  Uncommon: {common_stats[False]:,} names")
    
    print(f"\n=== SAMPLE UNIQUE KEYS ===")
    sample_keys = sorted(list(unique_keys))[:10]
    for key in sample_keys:
        length, letter, v1, v2 = key
        print(f"  ({length}, '{letter}', {v1}, {v2})")
    
    if len(unique_keys) > 10:
        print(f"  ... and {len(unique_keys) - 10:,} more keys")

    # Also analyze nicknames if available
    print(f"\n=== NICKNAME ANALYSIS ===")
    nicknames_path = Path("data/nicknames_full.tsv")
    if nicknames_path.exists():
        nickname_count = 0
        formal_names_with_nicks = set()
        with nicknames_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.strip().split("\t")
                formal = parts[0].strip().lower()
                nicknames = parts[1].split(",") if len(parts) > 1 else []
                formal_names_with_nicks.add(formal)
                nickname_count += len([n for n in nicknames if n.strip()])
        
        print(f"  Formal names with nicknames: {len(formal_names_with_nicks):,}")
        print(f"  Total nickname variations: {nickname_count:,}")
    else:
        print("  No nicknames_full.tsv found")

if __name__ == "__main__":
    analyze_names() 