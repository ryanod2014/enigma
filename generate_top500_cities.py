#!/usr/bin/env python3
"""
generate_top500_cities.py
--------------------------
Generates a CSV of the top 500 most popular cities by population using the same
geonamescache data source as the main application.

This matches the ranking logic used in main.py where cities are ranked by 
population (freq_val = meta["population"] / 1_000_000.0).

Usage:
    python generate_top500_cities.py [output_file.csv]
    
If no output file specified, creates 'top500_cities.csv'
"""

import csv
import sys
from pathlib import Path
import geonamescache  # type: ignore

def generate_top500_cities(output_file: str = "top500_cities.csv"):
    """Generate CSV with top 500 cities by population."""
    
    print("Loading cities from geonamescache...")
    gc = geonamescache.GeonamesCache()
    
    # Get all cities with population data
    cities_with_pop = []
    
    for city in gc.get_cities().values():
        pop = int(city.get("population", 0))
        if not pop:
            continue
        
        name_raw = city["name"]
        # Skip multi-word cities to match the main application's logic
        if " " in name_raw:
            continue
            
        cities_with_pop.append({
            'name': name_raw,
            'population': pop,
            'country': city.get('countrycode', ''),
            'region': city.get('continentcode', ''),
            'population_millions': round(pop / 1_000_000.0, 3)
        })
    
    print(f"Found {len(cities_with_pop)} cities with population data")
    
    # Sort by population (descending) and take top 500
    cities_sorted = sorted(cities_with_pop, key=lambda x: x['population'], reverse=True)
    top500 = cities_sorted[:500]
    
    print(f"Top 10 cities by population:")
    for i, city in enumerate(top500[:10], 1):
        print(f"{i:2d}. {city['name']:<15} ({city['population_millions']:>5.1f}M) - {city['country']}")
    
    # Write to CSV
    output_path = Path(output_file)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['city', 'population', 'population_millions', 'country', 'region']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for city_data in top500:
            writer.writerow({
                'city': city_data['name'],
                'population': city_data['population'],
                'population_millions': city_data['population_millions'],
                'country': city_data['country'],
                'region': city_data['region']
            })
    
    print(f"\nTop 500 cities written to: {output_file}")
    print(f"Population range: {top500[0]['population_millions']:.1f}M - {top500[-1]['population_millions']:.1f}M")
    
    return output_file

def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "top500_cities.csv"
    
    try:
        csv_file = generate_top500_cities(output_file)
        print(f"\nReady to run: python extract_city_codes.py {csv_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 