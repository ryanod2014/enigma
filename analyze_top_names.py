#!/usr/bin/env python3
"""
Analyze the top 20% most popular first names to check unique keys.
"""

import csv
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple

VOWELS = "AEIOUY"

def vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1‑based positions of vowels in *word* (case‑insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)

def analyze_top_names():
    """Analyze the top 20% most popular names from first_names.tsv file."""
    
    names_path = Path("data/first_names.tsv")
    if not names_path.exists():
        print(f"ERROR: {names_path} not found!")
        return
    
    print("=== TOP 20% MOST POPULAR NAMES ANALYSIS ===\n")
    
    # First pass: collect all names with their popularity rankings
    all_names = []
    
    print("Reading first_names.tsv file...")
    
    with names_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row_num, row in enumerate(reader, 1):
            if not row or row[0].startswith("#"):
                continue
                
            # Parse row: name, gender, origin, rank_us, rank_world
            if len(row) < 5:
                continue
                
            name = row[0].lower()
            gender = row[1].lower()
            origin = row[2].upper()
            rank_us = int(row[3]) if row[3] else 9999999  # High number for unranked
            rank_world = int(row[4]) if row[4] else 9999999
            
            # Basic sanity checks
            if not name or " " in name:
                continue
                
            # Check vowel positions
            vpos = vowel_positions(name)
            if not vpos:
                continue  # must contain at least one vowel
            
            all_names.append({
                'name': name,
                'gender': gender,
                'origin': origin,
                'rank_us': rank_us,
                'rank_world': rank_world,
                'vowel_pos': vpos
            })
    
    # Sort by popularity (lower rank = more popular)
    # Prioritize US ranking, then world ranking
    def popularity_key(name_data):
        us_rank = name_data['rank_us']
        world_rank = name_data['rank_world']
        
        # If both are unranked, put at end
        if us_rank == 9999999 and world_rank == 9999999:
            return (9999999, 9999999)
        
        # If US rank exists, use it primarily
        if us_rank != 9999999:
            return (us_rank, world_rank)
        
        # Otherwise use world rank
        return (9999999, world_rank)
    
    all_names.sort(key=popularity_key)
    
    # Take top 20%
    total_names = len(all_names)
    top_20_percent_count = int(total_names * 0.2)
    top_names = all_names[:top_20_percent_count]
    
    print(f"Total valid names: {total_names:,}")
    print(f"Top 20% count: {top_20_percent_count:,}")
    
    # Now analyze just the top 20%
    unique_keys = set()
    length_stats = Counter()
    first_letter_stats = Counter()
    v1_stats = Counter()
    v2_stats = Counter()
    gender_stats = Counter()
    
    # FL bucket mapping
    CATEGORY_MAP = {
        1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
        2: {"C", "G", "O", "J", "Q", "S", "U"},
        3: {"B", "D", "P", "R", "J", "U"},
    }
    
    print(f"\nAnalyzing top {top_20_percent_count:,} most popular names...")
    
    for name_data in top_names:
        name = name_data['name']
        vpos = name_data['vowel_pos']
        
        first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)
        
        # Generate key
        key = (len(name), name[0], first_v, second_v)
        unique_keys.add(key)
        
        # Update statistics
        length_stats[len(name)] += 1
        first_letter_stats[name[0]] += 1
        v1_stats[first_v] += 1
        v2_stats[second_v] += 1
        
        gender = name_data['gender']
        if gender in {"m", "f"}:
            gender_stats[gender] += 1
        else:
            gender_stats["u"] += 1
    
    # Print results
    print(f"\n=== TOP 20% RESULTS ===")
    print(f"TOTAL UNIQUE KEYS FOR TOP 20%: {len(unique_keys):,}")
    
    print(f"\n=== LENGTH DISTRIBUTION (TOP 20%) ===")
    for length in sorted(length_stats.keys()):
        print(f"  {length} letters: {length_stats[length]:,} names")
    
    print(f"\n=== FIRST LETTER (FL) BUCKETS (TOP 20%) ===")
    for bucket in sorted(CATEGORY_MAP.keys()):
        letters = sorted(CATEGORY_MAP[bucket])
        count = sum(first_letter_stats[letter.lower()] for letter in letters)
        print(f"  Bucket {bucket} ({', '.join(letters)}): {count:,} names")
    
    print(f"\n=== FIRST VOWEL POSITION (V1) - TOP 20% ===")
    for pos in sorted(v1_stats.keys()):
        print(f"  Position {pos}: {v1_stats[pos]:,} names")
    
    print(f"\n=== SECOND VOWEL POSITION (V2) - TOP 20% ===")
    for pos in sorted(v2_stats.keys()):
        if pos == 0:
            print(f"  No second vowel (0): {v2_stats[pos]:,} names")
        else:
            print(f"  Position {pos}: {v2_stats[pos]:,} names")
    
    print(f"\n=== GENDER DISTRIBUTION (TOP 20%) ===")
    for gender in sorted(gender_stats.keys()):
        gender_name = {"m": "Male", "f": "Female", "u": "Unisex/Unknown"}[gender]
        print(f"  {gender_name}: {gender_stats[gender]:,} names")
    
    print(f"\n=== SAMPLE TOP 20 MOST POPULAR NAMES ===")
    for i, name_data in enumerate(top_names[:20]):
        name = name_data['name']
        us_rank = name_data['rank_us'] if name_data['rank_us'] != 9999999 else "N/A"
        world_rank = name_data['rank_world'] if name_data['rank_world'] != 9999999 else "N/A"
        gender = name_data['gender'].upper()
        print(f"  {i+1:2d}. {name:<12} (US: {us_rank:<4}, World: {world_rank:<4}, {gender})")
    
    print(f"\n=== SAMPLE UNIQUE KEYS (TOP 20%) ===")
    sample_keys = sorted(list(unique_keys))[:10]
    for key in sample_keys:
        length, letter, v1, v2 = key
        print(f"  ({length}, '{letter}', {v1}, {v2})")
    
    if len(unique_keys) > 10:
        print(f"  ... and {len(unique_keys) - 10:,} more keys")
    
    # Comparison with all names
    print(f"\n=== COMPARISON ===")
    all_keys_count = 1619  # From previous analysis
    efficiency = len(unique_keys) / all_keys_count * 100
    print(f"  All names unique keys: {all_keys_count:,}")
    print(f"  Top 20% unique keys: {len(unique_keys):,}")
    print(f"  Coverage efficiency: {efficiency:.1f}% of keys cover 20% of names")

if __name__ == "__main__":
    analyze_top_names() 