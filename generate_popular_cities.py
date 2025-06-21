#!/usr/bin/env python3
"""
generate_popular_cities.py
---------------------------
Generates a CSV of the most popular/recognizable cities based on multiple criteria:
1. Tourist destinations
2. National capitals
3. Cultural/historical significance
4. Economic importance
5. Existing COMMON_CITIES list
6. Population (as a tie-breaker)

This creates a much better list than raw population for 20 Questions.
"""

import csv
import sys
from pathlib import Path
import geonamescache  # type: ignore
import pycountry
import re

# Import the existing curated list
from place_index import COMMON_CITIES

# Additional tourist/cultural destinations often missing from population lists
TOURIST_DESTINATIONS = {
    # European tourist cities
    "venice", "florence", "pisa", "nice", "cannes", "monte", "monaco", "geneva",
    "salzburg", "bruges", "ghent", "santorini", "mykonos", "dubrovnik", "porto",
    "seville", "granada", "toledo", "cambridge", "oxford", "edinburgh", "bath",
    
    # Asian tourist destinations
    "kyoto", "nara", "hiroshima", "bali", "phuket", "goa", "agra", "jaipur",
    "varanasi", "rishikesh", "kathmandu", "lhasa", "macau", "jeju", "busan",
    
    # Middle East & Africa
    "petra", "luxor", "aswan", "marrakech", "fez", "zanzibar", "cape", "victoria",
    
    # Americas
    "cusco", "machu", "cartagena", "salvador", "oaxaca", "cancun", "tulum",
    "quebec", "montreal", "banff", "whistler", "aspen", "napa", "sedona",
    
    # Oceania
    "cairns", "gold", "rotorua", "queenstown", "fiji", "tahiti"
}

# Major historical/cultural cities
CULTURAL_CITIES = {
    "sparta", "troy", "delphi", "olympia", "pompeii", "toledo", "cordoba",
    "damascus", "samarkand", "bukhara", "timbuktu", "lalibela", "axum",
    "angkor", "bagan", "luang", "hue", "hoi", "yogyakarta", "ubud"
}

# Major economic/business centers
BUSINESS_CENTERS = {
    "zurich", "geneva", "frankfurt", "milan", "rotterdam", "antwerp",
    "dubai", "doha", "kuwait", "riyadh", "mumbai", "bangalore", "pune",
    "shenzhen", "guangzhou", "osaka", "yokohama", "toronto", "vancouver",
    "sao", "monterrey", "guadalajara"
}

# UNESCO World Heritage Cities (selection)
UNESCO_CITIES = {
    "venice", "florence", "siena", "verona", "genoa", "naples", "palermo",
    "prague", "cesky", "krakow", "warsaw", "vilnius", "riga", "tallinn",
    "stockholm", "bruges", "ghent", "porto", "evora", "toledo", "salamanca",
    "segovia", "avila", "cordoba", "seville", "santiago", "lyon", "strasbourg",
    "edinburgh", "bath", "canterbury", "york", "dublin", "bern", "vienna",
    "salzburg", "graz", "budapest", "athens", "rhodes", "delphi", "meteora"
}

DEFAULT_WIKI_FILE = "citylistfromwiki"  # relative path in repo

def get_all_national_capitals():
    """Get all national capitals using pycountry."""
    capitals = set()
    
    # Manual list of major capitals (since pycountry doesn't have capital data)
    major_capitals = {
        "london", "paris", "berlin", "rome", "madrid", "amsterdam", "brussels",
        "vienna", "prague", "budapest", "warsaw", "stockholm", "oslo", "copenhagen",
        "helsinki", "dublin", "lisbon", "athens", "ankara", "moscow", "kiev",
        "minsk", "bucharest", "sofia", "belgrade", "zagreb", "ljubljana",
        "sarajevo", "skopje", "tirana", "podgorica", "pristina", "chisinau",
        "vilnius", "riga", "tallinn", "baku", "yerevan", "tbilisi",
        
        "washington", "ottawa", "mexico", "guatemala", "belize", "tegucigalpa",
        "managua", "san", "panama", "havana", "kingston", "nassau", "port",
        
        "brasilia", "buenos", "montevideo", "asuncion", "la", "sucre", "quito",
        "lima", "bogota", "caracas", "georgetown", "paramaribo", "cayenne",
        
        "cairo", "khartoum", "addis", "nairobi", "kampala", "kigali", "bujumbura",
        "dar", "dodoma", "antananarivo", "port", "victoria", "moroni", "mamoudzou",
        "libreville", "malabo", "yaounde", "bangui", "ndjamena", "niamey",
        "ouagadougou", "bamako", "nouakchott", "dakar", "banjul", "bissau",
        "conakry", "freetown", "monrovia", "yamoussoukro", "accra", "lome",
        "porto", "cotonou", "abuja", "tripoli", "tunis", "algiers", "rabat",
        
        "beijing", "tokyo", "seoul", "pyongyang", "ulaanbaatar", "taipei",
        "manila", "hanoi", "vientiane", "phnom", "bangkok", "kuala", "singapore",
        "bandar", "jakarta", "dili", "yangon", "dhaka", "thimphu", "kathmandu",
        "colombo", "male", "new", "islamabad", "kabul", "dushanbe", "ashgabat",
        "tashkent", "bishkek", "almaty", "astana", "tehran", "baghdad", "kuwait",
        "riyadh", "manama", "doha", "abu", "muscat", "sanaa", "damascus",
        "beirut", "amman", "jerusalem", "nicosia", "ankara"
    }
    
    return major_capitals

def calculate_city_score(city_name: str, city_data: dict, arrivals_map: dict[str, int]) -> float:
    """Calculate a popularity score for a city based on arrivals and heuristics."""
    score = 0.0
    name = city_name.lower()
    
    # Tourist arrivals (dominant factor if present)
    arr = arrivals_map.get(name)
    if arr:
        arr_m = arr / 1_000_000  # convert to millions
        score += arr_m * 4  # weight: 4 pts per 1M visitors (Paris ≈ 70)
    
    # Base population score (normalized to 0-10)
    pop = city_data.get('population', 0)
    pop_score = min(10, pop / 1_000_000)  # 10M+ population = max score
    score += pop_score * 0.1  # small weight now
    
    # Recognition factors ---------------------------------------------
    if name in COMMON_CITIES:
        score += 8  # curated as common
    if name in TOURIST_DESTINATIONS:
        score += 6
    if name in CULTURAL_CITIES:
        score += 5
    if name in UNESCO_CITIES:
        score += 4
    if name in BUSINESS_CENTERS:
        score += 3
    
    capitals = get_all_national_capitals()
    if name in capitals or any(cap in name for cap in capitals):
        score += 2  # national capital bump
    
    # Famous city quick bonuses
    famous_bonus = {
        "paris": 5, "london": 5, "rome": 5, "tokyo": 4, "new": 4,
        "los": 3, "venice": 3, "florence": 3, "prague": 3, "amsterdam": 3,
    }
    for fm, bonus in famous_bonus.items():
        if fm in name:
            score += bonus
            break
    
    return round(score, 2)

def generate_popular_cities(output_file: str = "popular_cities.csv", max_cities: int = 500):
    """Generate a list of popular cities based on multiple criteria."""
    
    print("Loading cities from geonamescache...")
    gc = geonamescache.GeonamesCache()
    arrivals_map = load_wiki_arrivals()
    
    # Collect all cities with scores
    cities_with_scores = []
    
    for city in gc.get_cities().values():
        pop = int(city.get("population", 0))
        name_raw = city["name"]
        
        # Skip multi-word cities for consistency with main app
        if " " in name_raw:
            continue
            
        name = name_raw.lower()
        
        # Calculate popularity score
        score = calculate_city_score(name, city, arrivals_map)
        
        cities_with_scores.append({
            'name': name_raw,
            'population': pop,
            'country': city.get('countrycode', ''),
            'region': city.get('continentcode', ''),
            'population_millions': round(pop / 1_000_000.0, 3),
            'popularity_score': score
        })
    
    # Sort by popularity score (descending), then by population (descending)
    cities_sorted = sorted(cities_with_scores, 
                          key=lambda x: (x['popularity_score'], x['population']), 
                          reverse=True)
    
    # Take top N cities
    top_cities = cities_sorted[:max_cities]
    
    print(f"\nTop 20 cities by popularity score:")
    for i, city in enumerate(top_cities[:20], 1):
        print(f"{i:2d}. {city['name']:<20} (Score: {city['popularity_score']:5.1f}, "
              f"Pop: {city['population_millions']:5.1f}M) - {city['country']}")
    
    # Write to CSV
    output_path = Path(output_file)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['city', 'popularity_score', 'population', 'population_millions', 'country', 'region']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for city_data in top_cities:
            writer.writerow({
                'city': city_data['name'],
                'popularity_score': city_data['popularity_score'],
                'population': city_data['population'],
                'population_millions': city_data['population_millions'],
                'country': city_data['country'],
                'region': city_data['region']
            })
    
    print(f"\nTop {max_cities} popular cities written to: {output_file}")
    print(f"Score range: {top_cities[0]['popularity_score']:.1f} - {top_cities[-1]['popularity_score']:.1f}")
    
    # Show breakdown by score ranges
    score_ranges = {"20+": 0, "15-19": 0, "10-14": 0, "5-9": 0, "0-4": 0}
    for city in top_cities:
        score = city['popularity_score']
        if score >= 20:
            score_ranges["20+"] += 1
        elif score >= 15:
            score_ranges["15-19"] += 1
        elif score >= 10:
            score_ranges["10-14"] += 1
        elif score >= 5:
            score_ranges["5-9"] += 1
        else:
            score_ranges["0-4"] += 1
    
    print(f"\nScore distribution: {score_ranges}")
    
    return output_file

def load_wiki_arrivals(file_path: str = DEFAULT_WIKI_FILE) -> dict[str, int]:
    """Return mapping city_lower → arrivals (int). Expects tab-separated list.
    We treat column 2 as City and column 4 as arrival count (may contain commas)."""
    arrivals_map: dict[str, int] = {}
    p = Path(file_path)
    if not p.is_file():
        print(f"[warn] Wiki arrivals file not found at {file_path}. Skipping.")
        return arrivals_map
    
    with p.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            city_raw = parts[2].strip()
            arrival_str = parts[4].replace(",", "").strip()
            if not city_raw or not arrival_str or not re.match(r"^\d+$", arrival_str):
                continue
            try:
                arrivals_map[city_raw.lower()] = int(arrival_str)
            except ValueError:
                continue
    return arrivals_map

def main():
    max_cities = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    output_file = sys.argv[2] if len(sys.argv) > 2 else "popular_cities.csv"
    
    try:
        csv_file = generate_popular_cities(output_file, max_cities)
        print(f"\nReady to run: python extract_city_codes.py {csv_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 