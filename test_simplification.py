#!/usr/bin/env python3
"""
Test script to evaluate the simplification heuristic on multi-word entries.
Shows original -> simplified mappings for manual review.
"""

import json
import random
from pathlib import Path
from simplify_keywords import should_simplify

def extract_multiword_samples(input_file: Path, sample_size: int = 150) -> list:
    """Extract multi-word entries from the original data file."""
    multiword_entries = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            try:
                entry = json.loads(line)
                
                # Only process entries with 'source' field (actual word entries)
                if 'source' not in entry:
                    continue
                
                subject = entry['subject']
                
                # Check if it's multi-word (contains space)
                if ' ' in subject and len(subject.split()) >= 2:
                    multiword_entries.append({
                        'original': subject,
                        'category': entry.get('category', 'unknown'),
                        'usage_count': entry.get('usage_count', 0)
                    })
                    
            except json.JSONDecodeError:
                continue
    
    # Shuffle and take sample
    random.shuffle(multiword_entries)
    return multiword_entries[:sample_size]

def test_simplification(samples: list) -> dict:
    """Test the simplification algorithm on samples."""
    results = {
        'good': [],
        'questionable': [],
        'bad': [],
        'no_change': []
    }
    
    for sample in samples:
        original = sample['original']
        should_sim, simplified = should_simplify(original)
        
        sample['simplified'] = simplified
        sample['changed'] = should_sim and simplified != original
        
        # Categorize for manual review
        if not sample['changed']:
            results['no_change'].append(sample)
        else:
            # For now, put all changes in questionable for manual review
            results['questionable'].append(sample)
    
    return results

def analyze_results(results: dict):
    """Display results for manual analysis."""
    total = sum(len(category) for category in results.values())
    
    print(f"\n{'='*80}")
    print(f"SIMPLIFICATION TEST RESULTS ({total} samples)")
    print(f"{'='*80}")
    
    # Show samples that were simplified
    print(f"\n🔄 SIMPLIFIED ENTRIES ({len(results['questionable'])} entries):")
    print(f"{'Original':<35} | {'Simplified':<20} | Category | Usage")
    print("-" * 80)
    
    for i, sample in enumerate(results['questionable'], 1):
        orig = sample['original'][:32] + "..." if len(sample['original']) > 32 else sample['original']
        simp = sample['simplified'][:17] + "..." if len(sample['simplified']) > 17 else sample['simplified']
        cat = sample['category'][:8]
        usage = sample['usage_count']
        
        print(f"{orig:<35} | {simp:<20} | {cat:<8} | {usage}")
        
        # Break into chunks for readability
        if i % 25 == 0 and i < len(results['questionable']):
            print(f"\n--- Showing {i} of {len(results['questionable'])} ---")
    
    # Show samples that weren't changed
    print(f"\n⏸️  NO CHANGE ({len(results['no_change'])} entries):")
    print("(These were already single words or compounds that should be preserved)")
    
    no_change_sample = results['no_change'][:10]  # Show first 10
    for sample in no_change_sample:
        print(f"  • {sample['original']}")
    
    if len(results['no_change']) > 10:
        print(f"  ... and {len(results['no_change']) - 10} more")

def categorize_manually():
    """Guide for manual categorization."""
    print(f"\n{'='*80}")
    print("MANUAL REVIEW GUIDE:")
    print("Look for these patterns in the simplified entries above:")
    print("='*80")
    print("✅ GOOD simplifications:")
    print("  • 'phone charger' → 'charger' ✓")
    print("  • 'wireless speaker' → 'speaker' ✓")
    print("  • 'office chair' → 'chair' ✓")
    print("  • 'vacuum cleaner' → 'vacuum' ✓")
    print()
    print("❓ QUESTIONABLE simplifications:")
    print("  • 'ice cream' → 'cream' (should it stay 'ice cream'?)")
    print("  • 'hot dog' → 'dog' (should stay 'hot dog')")
    print("  • 'space station' → 'station' (could go either way)")
    print()
    print("❌ BAD simplifications:")
    print("  • 'fire truck' → 'truck' (should be 'firetruck')")
    print("  • 'apple pie' → 'pie' (might want to keep 'apple pie')")
    print("  • 'peanut butter' → 'butter' (should stay 'peanut butter')")
    print()
    print("Count the good vs questionable vs bad as you review!")

def main():
    input_file = Path("data/combined_twentyquestions.jsonl")
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return
    
    print("🔍 Extracting multi-word entries for testing...")
    samples = extract_multiword_samples(input_file, sample_size=150)
    
    print(f"📊 Testing simplification on {len(samples)} multi-word entries...")
    results = test_simplification(samples)
    
    # Display results
    analyze_results(results)
    categorize_manually()
    
    # Summary stats
    simplified_count = len(results['questionable'])
    no_change_count = len(results['no_change'])
    total = simplified_count + no_change_count
    
    print(f"\n📈 SUMMARY:")
    print(f"Total entries tested: {total}")
    print(f"Entries simplified: {simplified_count} ({simplified_count/total*100:.1f}%)")
    print(f"Entries unchanged: {no_change_count} ({no_change_count/total*100:.1f}%)")
    
    print(f"\n💡 Now manually review the simplified entries above and count:")
    print(f"   • ✅ Good simplifications (correct and useful)")
    print(f"   • ❓ Questionable (could go either way)")  
    print(f"   • ❌ Bad simplifications (incorrect or loss of meaning)")

if __name__ == "__main__":
    main() 