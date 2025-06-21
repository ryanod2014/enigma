#!/usr/bin/env python3
"""
extract_city_codes.py
---------------------
Extracts codes for cities from a CSV file, reversing the process from main.py.

For each city, extracts:
- length: Length of city name (ignoring spaces)  
- category: First letter category (1, 2, or 3)
- v1: First vowel position (1-based)
- v2: Second vowel position (1-based, or 0 if only one vowel)

Usage:
    python extract_city_codes.py input.csv [output.csv]
    
Input CSV should have a column named 'city' or 'name' (case insensitive)
If no output file specified, prints to console
"""

import csv
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Same constants as used in main.py and place_index.py
VOWELS = "AEIOUY"

CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}

def vowel_positions(word: str) -> Tuple[int, ...]:
    """Return 1-based positions of vowels in word (case-insensitive)."""
    clean_word = word.replace(" ", "").replace("-", "")
    return tuple(i + 1 for i, ch in enumerate(clean_word.upper()) if ch in VOWELS)

def get_first_letter_category(word: str) -> int:
    """Return the category (1, 2, or 3) for the first letter of the word."""
    if not word:
        return 0
    
    first_letter = word[0].upper()
    for category, letters in CATEGORY_MAP.items():
        if first_letter in letters:
            return category
    return 0  # Unknown category

def extract_city_codes(city_name: str, **additional_data) -> Dict[str, Any]:
    """Extract all codes for a single city name."""
    # Clean the city name
    clean_name = city_name.strip().lower()
    
    # Calculate length (ignoring spaces and hyphens)
    length = len(clean_name.replace(" ", "").replace("-", ""))
    
    # Get first letter category
    category = get_first_letter_category(clean_name)
    
    # Get vowel positions
    vpos = vowel_positions(clean_name)
    v1 = vpos[0] if vpos else 0
    v2 = vpos[1] if len(vpos) > 1 else 0
    
    result = {
        'city': city_name,
        'clean_name': clean_name,
        'length': length,
        'category': category,
        'first_letter': clean_name[0].upper() if clean_name else '',
        'v1': v1,
        'v2': v2,
        'vowel_count': len(vpos),
        'all_vowel_positions': list(vpos)
    }
    
    # Add any additional data (like country, region, population, etc.)
    result.update(additional_data)
    
    return result

def find_city_column(headers: List[str]) -> str:
    """Find the column that contains city names."""
    headers_lower = [h.lower() for h in headers]
    
    # Common column names for cities
    city_columns = ['city', 'name', 'city_name', 'place', 'location', 'town']
    
    for col in city_columns:
        if col in headers_lower:
            return headers[headers_lower.index(col)]
    
    # If no standard column found, use first column
    if headers:
        print(f"Warning: No standard city column found. Using '{headers[0]}'")
        return headers[0]
    
    raise ValueError("No columns found in CSV")

def process_csv(input_file: str, output_file: str = None):
    """Process the CSV file and extract codes for all cities."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    results = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        # Try to detect if file has headers
        sample = f.read(1024)
        f.seek(0)
        
        # Try to detect delimiter and headers
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            has_header = sniffer.has_header(sample)
        except csv.Error:
            # Default to comma if detection fails
            delimiter = ','
            has_header = True
        
        f.seek(0)
        reader = csv.reader(f, delimiter=delimiter)
        
        if has_header:
            headers = next(reader)
            city_column = find_city_column(headers)
            city_col_index = headers.index(city_column)
        else:
            city_col_index = 0  # Use first column if no headers
            headers = [f"column_{i}" for i in range(20)]  # Generic headers
            print("Warning: No headers detected. Using first column as city names.")
        
        for row_num, row in enumerate(reader, start=2 if has_header else 1):
            if not row or city_col_index >= len(row):
                continue
                
            city_name = row[city_col_index].strip()
            if not city_name:
                continue
            
            try:
                # Collect additional data from all other columns
                additional_data = {}
                for i, value in enumerate(row):
                    if i != city_col_index and i < len(headers):
                        col_name = headers[i]
                        additional_data[col_name] = value.strip() if value else ''
                
                codes = extract_city_codes(city_name, **additional_data)
                codes['row_number'] = row_num
                results.append(codes)
            except Exception as e:
                print(f"Error processing '{city_name}' on row {row_num}: {e}")
    
    # Output results
    if output_file:
        output_path = Path(output_file)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if results:
                # Get all fieldnames from the first result (they should all be the same)
                all_fields = list(results[0].keys())
                
                # Reorder to put the main fields first, then additional data
                core_fields = ['city', 'clean_name', 'length', 'category', 'first_letter', 
                              'v1', 'v2', 'vowel_count', 'all_vowel_positions']
                
                fieldnames = []
                # Add core fields first
                for field in core_fields:
                    if field in all_fields:
                        fieldnames.append(field)
                
                # Add additional fields (like country, region, population, etc.)
                for field in all_fields:
                    if field not in core_fields and field != 'row_number':
                        fieldnames.append(field)
                
                # Add row_number at the end
                if 'row_number' in all_fields:
                    fieldnames.append('row_number')
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
        print(f"Results written to: {output_file}")        
    else:
        # Print to console - show key columns including country/region if available
        has_country = 'country' in results[0] if results else False
        has_region = 'region' in results[0] if results else False
        
        if has_country and has_region:
            header = f"{'City':<20} {'Country':<7} {'Region':<6} {'Length':<6} {'Cat':<3} {'FL':<2} {'V1':<2} {'V2':<2} {'Vowels':<7}"
            print(header)
            print("-" * len(header))
            for result in results:
                country = result.get('country', '')[:6]  # Truncate long country codes
                region = result.get('region', '')[:5]    # Truncate long region codes
                print(f"{result['city']:<20} {country:<7} {region:<6} {result['length']:<6} {result['category']:<3} "
                      f"{result['first_letter']:<2} {result['v1']:<2} {result['v2']:<2} {result['vowel_count']:<7}")
        elif has_country:
            header = f"{'City':<20} {'Country':<7} {'Length':<6} {'Cat':<3} {'FL':<2} {'V1':<2} {'V2':<2} {'Vowels':<7}"
            print(header)
            print("-" * len(header))
            for result in results:
                country = result.get('country', '')[:6]
                print(f"{result['city']:<20} {country:<7} {result['length']:<6} {result['category']:<3} "
                      f"{result['first_letter']:<2} {result['v1']:<2} {result['v2']:<2} {result['vowel_count']:<7}")
        else:
            # Original format if no additional columns
            print(f"{'City':<20} {'Length':<6} {'Cat':<3} {'FL':<2} {'V1':<2} {'V2':<2} {'Vowels':<7} {'Positions':<10}")
            print("-" * 70)
            for result in results:
                print(f"{result['city']:<20} {result['length']:<6} {result['category']:<3} "
                      f"{result['first_letter']:<2} {result['v1']:<2} {result['v2']:<2} "
                      f"{result['vowel_count']:<7} {str(result['all_vowel_positions']):<10}")
    
    print(f"\nProcessed {len(results)} cities successfully.")
    
    # Summary statistics
    category_counts = {}
    length_counts = {}
    
    for result in results:
        cat = result['category']
        length = result['length']
        
        category_counts[cat] = category_counts.get(cat, 0) + 1
        length_counts[length] = length_counts.get(length, 0) + 1
    
    print(f"\nSummary:")
    print(f"Category distribution: {dict(sorted(category_counts.items()))}")
    print(f"Length distribution: {dict(sorted(length_counts.items()))}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_city_codes.py input.csv [output.csv]")
        print("\nExample:")
        print("  python extract_city_codes.py cities.csv")
        print("  python extract_city_codes.py cities.csv city_codes.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        process_csv(input_file, output_file)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 