#!/usr/bin/env python3
"""Analyze encoding keys for a curated country list.
Parses country names from the embedded multi-line string (text provided by user).
Outputs stats (unique codes, avg names/code, max collision) for candidate key combos.
"""
import re
from collections import defaultdict
from typing import List, Dict, Tuple

VOWELS = "AEIOUY"
CATEGORY_MAP = {
    1: {"A", "E", "I", "F", "H", "K", "L", "M", "N", "T", "V", "W", "X", "Y", "Z"},
    2: {"C", "G", "O", "J", "Q", "S", "U"},
    3: {"B", "D", "P", "R", "J", "U"},
}

COUNTRY_TEXT = """
France (Paris, Riviera, culture, cuisine)
Spain (Beaches, cities like Barcelona & Madrid, culture)
United States (Diverse landscapes, major cities, national parks)
Italy (Rome, Venice, Florence, food, history, art)
Turkey (Istanbul, Cappadocia, coastal resorts, history)
Mexico (Beaches, Mayan ruins, cuisine, culture)
United Kingdom (London, historical sites, countryside)
Germany (Cities, castles, Oktoberfest, Black Forest)
Thailand (Beaches, temples, food, vibrant culture)
China (Great Wall, Forbidden City, diverse landscapes - pre-pandemic, numbers were very high, recovering)
Japan (Unique culture, cuisine, technology, cherry blossoms)
Greece (Ancient ruins, islands like Santorini & Mykonos)
Canada (Natural beauty, vibrant cities, friendly culture)
Portugal (Lisbon, Porto, Algarve coast, affordability)
Netherlands (Amsterdam, tulips, windmills, art)
Austria (Vienna, Alps, music, culture)
Switzerland (Mountains, lakes, chocolate, watches)
Australia (Beaches, outback, wildlife, cities like Sydney & Melbourne)
United Arab Emirates (Dubai, Abu Dhabi, luxury, modern architecture)
South Korea (K-pop, K-drama, food, technology, history)
Croatia (Dalmatian coast, historical cities, Plitvice Lakes)
Ireland (Lush landscapes, pubs, castles, friendly locals)
Vietnam (Ha Long Bay, Hoi An, food, vibrant culture)
India (Taj Mahal, diverse culture, spirituality, cuisine)
Malaysia (Kuala Lumpur, islands, rainforests, food)
Indonesia (Bali, temples, volcanoes, beaches)
Brazil (Rio de Janeiro, Amazon rainforest, Iguazu Falls)
Argentina (Patagonia, Buenos Aires, tango, wine)
Morocco (Marrakech, Sahara Desert, souks, culture)
Egypt (Pyramids, Nile cruises, ancient history)
South Africa (Safaris, Cape Town, diverse landscapes)
New Zealand (Stunning natural beauty, adventure sports)
Singapore (Modern city, food, gardens, efficiency)
Sweden (Stockholm, design, nature, Northern Lights)
Norway (Fjords, Northern Lights, hiking)
Denmark (Copenhagen, design, hygge, cycling)
Belgium (Brussels, Bruges, chocolate, beer)
Poland (Krakow, Warsaw, history, affordability)
Czech Republic (Prague, castles, beer culture)
Hungary (Budapest, thermal baths, history)
Peru (Machu Picchu, Inca history, Andes)
Colombia (Medellin, Bogota, coffee region, diverse landscapes)
Costa Rica (Ecotourism, rainforests, wildlife, beaches)
Dominican Republic (Beaches, resorts, Caribbean culture)
Cuba (Vintage cars, cigars, music, unique culture)
Iceland (Volcanoes, glaciers, hot springs, Northern Lights)
Finland (Helsinki, Lapland, Santa Claus, saunas)
Philippines (Beaches, islands, diving)
Chile (Atacama Desert, Patagonia, Easter Island)
Israel (Jerusalem, Tel Aviv, religious sites, history)
Sri Lanka (Tea plantations, beaches, ancient sites)
Kenya (Safaris, Maasai Mara)
Tanzania (Serengeti, Kilimanjaro, Zanzibar)
Maldives (Luxury overwater bungalows, pristine beaches)
Seychelles (Stunning beaches, luxury resorts)
Mauritius (Beaches, luxury, diverse culture)
Fiji (Friendly culture, beaches, diving)
Ecuador (Galapagos Islands, Andes, Amazon)
Bolivia (Salt flats, Andes, unique culture)
Uruguay (Beaches, colonial towns, laid-back vibe)
Panama (Canal, rainforests, beaches)
Guatemala (Mayan ruins, volcanoes, Lake Atitlan)
Belize (Barrier Reef, Mayan ruins, jungles)
Nicaragua (Volcanoes, colonial cities, surfing)
El Salvador (Surfing, volcanoes, coffee)
Honduras (Mayan ruins, diving, beaches)
Paraguay (Jesuit missions, nature)
Jordan (Petra, Wadi Rum, Dead Sea)
Lebanon (Beirut, ancient ruins, cuisine)
Oman (Deserts, mountains, traditional culture)
Saudi Arabia (Opening up for tourism, historical sites, Red Sea)
Qatar (Doha, modern architecture, World Cup host)
Bahrain (Formula 1, history, pearl diving)
Georgia (Caucasus mountains, wine, ancient monasteries)
Armenia (Ancient monasteries, history, mountains)
Azerbaijan (Baku, mud volcanoes, unique culture)
Kazakhstan (Vast steppes, modern cities, unique nature)
Uzbekistan (Silk Road cities like Samarkand, Bukhara)
Mongolia (Gobi Desert, nomadic culture, vast landscapes)
Nepal (Himalayas, trekking, spirituality)
Bhutan (Gross National Happiness, monasteries, unique culture)
Myanmar (Burma) (Temples of Bagan, unique culture - political situation impacts desirability)
Laos (Luang Prabang, relaxed pace, Mekong River)
Cambodia (Angkor Wat, history)
Taiwan (Taipei, night markets, nature)
Cyprus (Beaches, history, mythology)
Malta (Historical sites, Mediterranean charm, diving)
Slovenia (Lake Bled, mountains, caves, Ljubljana)
Slovakia (Mountains, castles, Bratislava)
Romania (Transylvania, castles, medieval towns)
Bulgaria (Black Sea coast, mountains, history)
Albania (Beaches, mountains, affordability, emerging destination)
Montenegro (Kotor Bay, mountains, beaches)
Bosnia and Herzegovina (Sarajevo, Mostar, history)
Serbia (Belgrade, history, vibrant nightlife)
North Macedonia (Lake Ohrid, history, mountains)
Lithuania (Vilnius, Baltic coast, history)
Latvia (Riga, Art Nouveau, Baltic coast)
Estonia (Tallinn, medieval old town, digital innovation)
Luxembourg (Castles, Ardennes, financial center)
"""

def extract_countries(text: str) -> List[str]:
    out=[]
    for line in text.strip().splitlines():
        line=line.strip()
        if not line:
            continue
        # take part before first "(" or end
        name=re.split(r"\s*\(", line, 1)[0].strip()
        out.append(name)
    # remove duplicates preserving order
    seen=set()
    uniq=[]
    for n in out:
        if n.lower() not in seen:
            uniq.append(n)
            seen.add(n.lower())
    return uniq


def category(ch: str) -> int:
    return 1 if ch.upper() in CATEGORY_MAP[1] else 2 if ch.upper() in CATEGORY_MAP[2] else 3


def first_vowel(word: str) -> int:
    for i,ch in enumerate(word.upper(),1):
        if ch in VOWELS:
            return i
    return 0


def second_vowel(word: str) -> int:
    cnt=0
    for i,ch in enumerate(word.upper(),1):
        if ch in VOWELS:
            cnt+=1
            if cnt==2:
                return i
    return 0


def build_records(names: List[str]):
    recs=[]
    for n in names:
        rec={
            'name': n,
            'length': len(n.replace(' ','').replace('-','')),
            'F1': category(n[0]),
            'V1': first_vowel(n),
            'V2': second_vowel(n),
            'LL': category(n[-1])
        }
        recs.append(rec)
    return recs


def stats(records: List[Dict], keys: Tuple[str,...]):
    buckets=defaultdict(list)
    for rec in records:
        buckets[tuple(rec[k] for k in keys)].append(rec['name'])
    sizes=[len(v) for v in buckets.values()]
    return len(buckets), sum(sizes)/len(buckets), max(sizes)


def main():
    countries=extract_countries(COUNTRY_TEXT)
    print(f"Total countries parsed: {len(countries)}")
    recs=build_records(countries)
    combos=[
        (('length','F1','V1','V2'),'length+F1+V1+V2'),
        (('length','V1','V2','LL'),'length+V1+V2+LL'),
        (('length','F1','V1','LL'),'length+F1+V1+LL'),
        (('F1','V1','V2','LL'),'F1+V1+V2+LL'),
        (('length','V1','V2'),'length+V1+V2')
    ]
    for keys,name in combos:
        codes,avg,mx=stats(recs,keys)
        print(f"{name}: codes={codes}, avg={avg:.2f}, max={mx}")

if __name__=='__main__':
    main() 