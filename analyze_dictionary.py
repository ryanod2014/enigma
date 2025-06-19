#!/usr/bin/env python3
"""
Analyze the 20-questions word dictionary to check total unique keys and statistics.
This script will also help debug the classification issue.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

VOWELS = "AEIOUY"

def vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1‑based positions of vowels in *word* (case‑insensitive)."""
    return tuple(i + 1 for i, ch in enumerate(word.upper()) if ch in VOWELS)

def debug_classify_subject(word: str) -> tuple[str, bool]:
    """Debug version of classify_subject to identify the issue."""
    try:
        # Import the function from the main module
        from wordnet_vowel_index import classify_subject
        result = classify_subject(word)
        if result is None:
            print(f"WARNING: classify_subject returned None for word: '{word}'")
            return 'unknown', False
        return result
    except Exception as e:
        print(f"ERROR classifying word '{word}': {e}")
        return 'unknown', False

def analyze_dictionary():
    """Analyze the combined_twentyquestions.jsonl file."""
    
    jsonl_path = Path("data/combined_twentyquestions.jsonl")
    if not jsonl_path.exists():
        print(f"ERROR: {jsonl_path} not found!")
        return
    
    print("=== 20 QUESTIONS DICTIONARY ANALYSIS ===\n")
    
    # Statistics counters
    total_entries = 0
    unique_subjects = set()
    subject_counts = {}
    valid_words = set()
    
    # Key analysis
    unique_keys = set()
    
    # Category breakdowns
    length_stats = Counter()
    first_letter_stats = Counter()
    v1_stats = Counter() 
    v2_stats = Counter()
    category_stats = Counter()
    
    # FL bucket mapping (from wordnet_vowel_index.py)
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
    
    print("Reading JSONL file...")
    
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, 1):
            try:
                obj = json.loads(line)
                total_entries += 1
            except json.JSONDecodeError:
                continue
            
            subj_raw = str(obj.get("subject", "")).strip().lower()
            
            # Basic sanity checks
            if not subj_raw:
                continue
            if " " in subj_raw:  # ignore multi-word
                continue
            if not re.fullmatch(r"[a-z]+", subj_raw):
                continue
                
            unique_subjects.add(subj_raw)
            subject_counts[subj_raw] = subject_counts.get(subj_raw, 0) + 1
            
            # Check vowel positions
            vpos = vowel_positions(subj_raw)
            if not vpos:
                continue  # must contain at least one vowel
                
            first_v, second_v = vpos[0], (vpos[1] if len(vpos) > 1 else 0)
            
            # Debug classification
            try:
                bucket, man_flag = debug_classify_subject(subj_raw)
                if bucket == 'person':
                    continue  # skip persons
            except Exception as e:
                print(f"ERROR on line {line_num} with word '{subj_raw}': {e}")
                continue
                
            # This word passes all filters
            valid_words.add(subj_raw)
            
            # Generate key
            key = (len(subj_raw), subj_raw[0], first_v, second_v)
            unique_keys.add(key)
            
            # Update statistics
            length_stats[len(subj_raw)] += 1
            first_letter_stats[subj_raw[0]] += 1
            v1_stats[first_v] += 1
            v2_stats[second_v] += 1
            
            fl_bucket = get_fl_bucket(subj_raw[0])
            category_stats[fl_bucket] += 1
    
    # Print results
    print(f"\n=== RESULTS ===")
    print(f"Total JSONL entries: {total_entries:,}")
    print(f"Unique raw subjects: {len(unique_subjects):,}")
    print(f"Valid filtered words: {len(valid_words):,}")
    print(f"TOTAL UNIQUE KEYS: {len(unique_keys):,}")
    
    print(f"\n=== LENGTH DISTRIBUTION ===")
    for length in sorted(length_stats.keys()):
        print(f"  {length} letters: {length_stats[length]:,} words")
    
    print(f"\n=== FIRST LETTER (FL) BUCKETS ===")
    for bucket in sorted(CATEGORY_MAP.keys()):
        letters = sorted(CATEGORY_MAP[bucket])
        count = sum(first_letter_stats[letter.lower()] for letter in letters)
        print(f"  Bucket {bucket} ({', '.join(letters)}): {count:,} words")
    
    print(f"\n=== FIRST VOWEL POSITION (V1) ===")
    for pos in sorted(v1_stats.keys()):
        print(f"  Position {pos}: {v1_stats[pos]:,} words")
    
    print(f"\n=== SECOND VOWEL POSITION (V2) ===")
    for pos in sorted(v2_stats.keys()):
        if pos == 0:
            print(f"  No second vowel (0): {v2_stats[pos]:,} words")
        else:
            print(f"  Position {pos}: {v2_stats[pos]:,} words")
    
    print(f"\n=== MOST COMMON WORDS ===")
    most_common = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    for word, count in most_common:
        if word in valid_words:
            print(f"  {word}: {count} occurrences")
    
    print(f"\n=== SAMPLE UNIQUE KEYS ===")
    sample_keys = sorted(list(unique_keys))[:10]
    for key in sample_keys:
        length, letter, v1, v2 = key
        print(f"  ({length}, '{letter}', {v1}, {v2})")
    
    if len(unique_keys) > 10:
        print(f"  ... and {len(unique_keys) - 10:,} more keys")

if __name__ == "__main__":
    analyze_dictionary() 