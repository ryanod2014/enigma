#!/usr/bin/env python3
"""
Script to simplify multi-word entries to their core keywords.
Example: "phone charger" -> "charger", but preserve "firetruck" as "firetruck"
"""

import json
import re
from typing import Dict, Set, List, Tuple
from pathlib import Path

# Compound words that should NOT be simplified (stay as single words)
PRESERVE_COMPOUNDS = {
    'firetruck', 'spaceship', 'earthquake', 'butterfly', 'snowball', 
    'basketball', 'football', 'bedroom', 'bathroom', 'toothbrush',
    'keychain', 'rainbow', 'doorbell', 'lighthouse', 'grandfather',
    'grandmother', 'sunflower', 'moonlight', 'starfish', 'jellyfish',
    'horseback', 'backyard', 'pathway', 'highway', 'sidewalk',
    'railroad', 'aircraft', 'spacecraft', 'waterfall', 'snowman',
    'sunshine', 'earthquake', 'flashlight', 'headlight', 'spotlight',
    'loudspeaker', 'loudspeakers', 'breakfast', 'lunchbox', 'dinnertime'
}

# Common adjective prefixes that should be removed
ADJECTIVE_PREFIXES = {
    'wireless', 'electric', 'digital', 'automatic', 'manual', 'outdoor',
    'indoor', 'portable', 'handheld', 'stainless', 'plastic', 'wooden',
    'metal', 'glass', 'fabric', 'leather', 'frozen', 'fresh', 'dried',
    'broken', 'emergency', 'safety', 'kitchen', 'office', 'bathroom',
    'bedroom', 'living', 'dining', 'garden', 'garage', 'basement',
    'upstairs', 'downstairs', 'outdoor', 'indoor', 'waterproof',
    'fireproof', 'shockproof', 'childproof', 'tamper', 'anti'
}

# Common brand/material prefixes that should be removed  
BRAND_PREFIXES = {
    'amazon', 'apple', 'google', 'samsung', 'sony', 'lg', 'panasonic',
    'nintendo', 'xbox', 'playstation', 'microsoft', 'intel', 'amd',
    'nvidia', 'canon', 'nikon', 'honda', 'toyota', 'ford', 'bmw'
}

# Specific multi-word patterns to simplify
SIMPLIFICATION_RULES = {
    # Pattern: (full_phrase, simplified_keyword)
    'phone charger': 'charger',
    'car charger': 'charger', 
    'laptop charger': 'charger',
    'vacuum cleaner': 'vacuum',
    'air filter': 'filter',
    'water filter': 'filter',
    'coffee filter': 'filter',
    'office chair': 'chair',
    'desk chair': 'chair',
    'kitchen table': 'table',
    'dining table': 'table',
    'coffee table': 'table',
    'beer glass': 'glass',
    'wine glass': 'glass',
    'water glass': 'glass',
    'toaster oven': 'toaster',
    'microwave oven': 'microwave',
    'desk lamp': 'lamp',
    'floor lamp': 'lamp',
    'table lamp': 'lamp',
    'ceiling lamp': 'lamp',
    'ice cream': 'cream',  # Unless it's a compound like "ice cream cone"
    'whipped cream': 'cream',
    'storage bin': 'bin',
    'trash bin': 'bin',
    'recycle bin': 'bin',
    'filing cabinet': 'cabinet',
    'medicine cabinet': 'cabinet',
    'kitchen cabinet': 'cabinet',
    'picture frame': 'frame',
    'photo frame': 'frame',
    'mixing bowl': 'bowl',
    'salad bowl': 'bowl',
    'soup bowl': 'bowl',
    'soccer ball': 'ball',
    'tennis ball': 'ball',
    'golf ball': 'ball',
    'rubber ball': 'ball',
    # Fix "manual" pattern issues
    'user manual': 'manual',
    'laboratory manual': 'manual',
    'instruction manual': 'manual',
    'service manual': 'manual',
    'owner manual': 'manual',
    'repair manual': 'manual'
}

def is_compound_word(word: str) -> bool:
    """Check if a word is a legitimate compound that should be preserved."""
    return word.lower() in PRESERVE_COMPOUNDS

def should_simplify(phrase: str) -> Tuple[bool, str]:
    """
    Determine if a multi-word phrase should be simplified and return the simplified form.
    Returns: (should_simplify: bool, simplified_word: str)
    """
    phrase_lower = phrase.lower().strip()
    
    # Check explicit rules first
    if phrase_lower in SIMPLIFICATION_RULES:
        return True, SIMPLIFICATION_RULES[phrase_lower]
    
    # Split the phrase into words
    words = phrase_lower.split()
    
    if len(words) < 2:
        return False, phrase  # Single word, no simplification needed
    
    # Check if it's a compound word written as separate words
    compound_candidate = ''.join(words)
    if is_compound_word(compound_candidate):
        return True, compound_candidate  # Combine into compound word
    
    # Find the main noun (usually the last non-adjective word)
    main_word = None
    
    # Work backwards through words to find the main noun
    for word in reversed(words):
        if (word not in ADJECTIVE_PREFIXES and 
            word not in BRAND_PREFIXES and
            len(word) > 2):  # Avoid tiny words like "of", "in", etc.
            main_word = word
            break
    
    if main_word and main_word != phrase_lower:
        return True, main_word
    
    return False, phrase

def process_jsonl_file(input_file: Path, output_file: Path) -> Dict[str, int]:
    """
    Process a JSONL file and simplify multi-word entries.
    Returns statistics about the changes made.
    """
    stats = {
        'total_entries': 0,
        'simplified': 0,
        'preserved': 0,
        'skipped': 0
    }
    
    simplified_entries = []
    seen_subjects = set()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                stats['total_entries'] += 1
                
                # Only process entries with 'source' field (actual word entries, not questions)
                if 'source' not in entry:
                    continue
                
                original_subject = entry['subject']
                should_simplify_flag, simplified_subject = should_simplify(original_subject)
                
                if should_simplify_flag and simplified_subject != original_subject:
                    # Avoid duplicates
                    if simplified_subject not in seen_subjects:
                        entry['subject'] = simplified_subject
                        entry['original_subject'] = original_subject  # Keep track of original
                        simplified_entries.append(entry)
                        seen_subjects.add(simplified_subject)
                        stats['simplified'] += 1
                        print(f"✓ Simplified: '{original_subject}' -> '{simplified_subject}'")
                    else:
                        stats['skipped'] += 1
                        print(f"⚠ Skipped (duplicate): '{original_subject}' -> '{simplified_subject}'")
                else:
                    # Preserve original entry
                    if original_subject not in seen_subjects:
                        simplified_entries.append(entry)
                        seen_subjects.add(original_subject)
                        stats['preserved'] += 1
                    else:
                        stats['skipped'] += 1
                        
            except json.JSONDecodeError:
                continue
    
    # Write simplified entries to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in simplified_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    return stats

def main():
    input_file = Path("data/combined_twentyquestions.jsonl")
    output_file = Path("data/simplified_twentyquestions.jsonl")
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    print("🔄 Processing entries...")
    stats = process_jsonl_file(input_file, output_file)
    
    print("\n📊 Simplification Results:")
    print(f"Total entries processed: {stats['total_entries']}")
    print(f"Entries simplified: {stats['simplified']}")
    print(f"Entries preserved: {stats['preserved']}")
    print(f"Entries skipped (duplicates): {stats['skipped']}")
    print(f"\n✅ Output written to: {output_file}")
    
    # Show some examples of what was simplified
    print("\n🔍 Sample simplifications:")
    sample_rules = list(SIMPLIFICATION_RULES.items())[:10]
    for original, simplified in sample_rules:
        print(f"  '{original}' -> '{simplified}'")

if __name__ == "__main__":
    main() 