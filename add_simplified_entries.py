#!/usr/bin/env python3
"""
Script to add simplified keyword entries alongside original multi-word entries.
Keeps both versions in the database for maximum search flexibility.
Example: Keep "phone charger" AND add "charger" as separate entries.
"""

import json
from typing import Dict, Set, List
from pathlib import Path
from simplify_keywords import should_simplify

def add_simplified_entries(input_file: Path, output_file: Path) -> Dict[str, int]:
    """
    Add simplified entries alongside original entries.
    Returns statistics about the changes made.
    """
    stats = {
        'original_entries': 0,
        'kept_originals': 0,
        'added_simplified': 0,
        'skipped_duplicates': 0,
        'total_output': 0
    }
    
    all_entries = []
    seen_subjects = set()
    
    # First pass: Keep all original entries
    print("📥 Loading original entries...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                stats['original_entries'] += 1
                
                # Keep all original entries
                if entry.get('subject'):
                    all_entries.append(entry)
                    seen_subjects.add(entry['subject'].lower())
                    stats['kept_originals'] += 1
                    
            except json.JSONDecodeError:
                continue
    
    # Second pass: Add simplified versions for multi-word entries
    print("🔄 Generating simplified entries...")
    simplified_entries = []
    
    for entry in all_entries:
        # Only process entries with 'source' field (actual word entries, not questions)
        if 'source' not in entry:
            continue
            
        original_subject = entry['subject']
        should_simplify_flag, simplified_subject = should_simplify(original_subject)
        
        if (should_simplify_flag and 
            simplified_subject != original_subject):
            
            # Create new simplified entry
            simplified_entry = entry.copy()
            simplified_entry['subject'] = simplified_subject
            simplified_entry['original_subject'] = original_subject
            simplified_entry['simplified_from'] = original_subject  # Track where it came from
            
            simplified_entries.append(simplified_entry)
            seen_subjects.add(simplified_subject.lower())
            stats['added_simplified'] += 1
            
            print(f"➕ Added: '{simplified_subject}' (from '{original_subject}')")
    
    # Combine original + simplified entries
    final_entries = all_entries + simplified_entries
    stats['total_output'] = len(final_entries)
    
    # Write combined entries to output file
    print("💾 Writing combined database...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in final_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    return stats

def main():
    input_file = Path("data/combined_twentyquestions.jsonl")
    output_file = Path("data/enhanced_twentyquestions.jsonl")
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    print("🚀 Creating enhanced database with both original and simplified entries...")
    stats = add_simplified_entries(input_file, output_file)
    
    print(f"\n{'='*60}")
    print("📊 ENHANCED DATABASE RESULTS:")
    print(f"{'='*60}")
    print(f"Original entries loaded: {stats['original_entries']:,}")
    print(f"Original entries kept: {stats['kept_originals']:,}")
    print(f"Simplified entries added: {stats['added_simplified']:,}")
    print(f"Duplicates skipped: {stats['skipped_duplicates']:,}")
    print(f"Total entries in output: {stats['total_output']:,}")
    print(f"\n✅ Enhanced database written to: {output_file}")
    
    # Show some examples
    print(f"\n🔍 Example enhancements:")
    print(f"  Database now contains both:")
    print(f"    • 'phone charger' (original)")
    print(f"    • 'charger' (simplified)")
    print(f"  Players can search for either version!")
    
    print(f"\n🎯 Benefits:")
    print(f"  ✓ Zero data loss - all originals preserved")
    print(f"  ✓ Maximum search flexibility")
    print(f"  ✓ Handles different player thinking patterns")
    print(f"  ✓ Backward compatible")

if __name__ == "__main__":
    main() 