#!/usr/bin/env python3
"""
build_wikidata_meta.py
Step 4: Wire common_objects.json into the metadata builder
"""

import json
import sys
from pathlib import Path
from typing import Dict, Set, Any

# Load accept/reject Q-IDs
def load_qids(file_path: Path) -> Set[str]:
    """Load Q-IDs from TSV file (first column)."""
    qids = set()
    if file_path.exists():
        with open(file_path) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    qid = line.split('\t')[0].strip()
                    if qid.startswith('Q'):
                        qids.add(qid)
    return qids

def main():
    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    common_objects_file = base_dir / "data" / "common_objects.json"
    accept_file = base_dir / "data" / "accept.tsv"
    reject_file = base_dir / "data" / "reject.tsv"
    output_file = base_dir / "data" / "wikidata_meta.json"
    
    # Load accept/reject Q-ID rosters
    accept_qids = load_qids(accept_file)
    reject_qids = load_qids(reject_file)
    
    print(f"Loaded {len(accept_qids)} accept Q-IDs, {len(reject_qids)} reject Q-IDs")
    
    # Load common objects cache
    if not common_objects_file.exists():
        print(f"ERROR: {common_objects_file} not found. Run Steps 2-3 first.")
        sys.exit(1)
    
    with open(common_objects_file) as f:
        common_objects = json.load(f)
    
    print(f"Processing {len(common_objects)} common objects...")
    
    # Build metadata for each word
    meta_data = {}
    
    for word, entry in common_objects.items():
        qid = entry.get("qid")
        links = entry.get("links", 0)
        description = entry.get("desc", "")
        root = entry.get("root", "object")
        
        # Step 4: Classification logic
        # - if its Q-ID ∈ reject_roster → status=reject  
        # - else if its Q-ID ∈ accept_roster OR its root in ("tool","food"…) → status=accept & category = root  
        # - else default reject (safety)
        
        if qid and qid in reject_qids:
            status = "reject"
            category = "unknown"
        elif qid and qid in accept_qids:
            status = "accept"
            category = root
        elif root in ["tool", "machine", "optical instrument", "musical instrument", "vehicle", 
                      "food", "clothing", "furniture", "toy", "animal", "plant"]:
            status = "accept"
            category = root
        else:
            # Default reject for safety
            status = "reject"
            category = "unknown"
        
        meta_data[word] = {
            "qid": qid,
            "status": status,
            "category": category,
            "popularity": links,
            "description": description
        }
    
    # Save metadata
    with open(output_file, 'w') as f:
        json.dump(meta_data, f, indent=2)
    
    # Stats
    accept_count = sum(1 for v in meta_data.values() if v["status"] == "accept")
    reject_count = len(meta_data) - accept_count
    
    print(f"Built metadata for {len(meta_data)} words:")
    print(f"  Accept: {accept_count}")
    print(f"  Reject: {reject_count}")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    main() 