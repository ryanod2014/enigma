# Enigma - 20 Questions Word Helper

A sophisticated word search tool designed for the 20 Questions game, built with Python FastAPI backend and React frontend.

## Features

### Advanced Word Filtering
- **Letter Count**: Select words by length (1-10 letters)
- **Letter Categories**: Filter by first/last letter shapes using visual icons
- **Vowel Positions**: Specify exact vowel positions (V1, V2)
- **Additional Letters**: Include specific letters that must be present
- **Physical Objects Only**: Curated database of tangible, physical objects
- **Frequency Filtering**: Common vs uncommon words based on usage statistics
- **Places Search**: Toggle to guess *Countries* or *Cities* with continent & popularity filters
- **First-Names Search**: Guess *First Names* with gender / origin filters

### Smart Categorization
- **Man-made vs Natural**: Automatic classification using WordNet hypernym analysis
- **Word Categories**: Animal, Plant, Artifact, Body, Substance, Vehicle, etc.
- **Real-time Filtering**: All filters work instantly without new API calls

### Mobile-Optimized UI
- **Dark Theme**: Sleek black interface with gray accents
- **Touch-Friendly**: Large buttons optimized for mobile use
- **Visual Search**: Click any word to open Google Images
- **Responsive Design**: Perfect on phones, tablets, and desktop

## Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **Local JSONL dataset**: curated 20-Questions knowledge base (`data/combined_twentyquestions.jsonl`)
- **Uvicorn**: ASGI server for production deployment

### Frontend
- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Shadcn/ui**: Beautiful, accessible components
- **Vite**: Fast build tool and dev server

## Project Structure

```
20questions/
├── api/                    # FastAPI backend
│   └── main.py            # API endpoints
├── web/                   # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   └── App.tsx    # Main application
│   │   ├── components/ui/ # Shadcn components
│   │   └── index.css      # Global styles
│   ├── package.json       # Node dependencies
│   └── vite.config.ts     # Vite configuration
├── wordnet_vowel_index.py # Word indexing engine
├── requirements.txt       # Python dependencies
└── word_index_filtered.csv # Pre-processed word data
```

## Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup
1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Download NLTK data** (first run only):
   ```bash
   python -c "import nltk; nltk.download('wordnet')"
   ```

3. **Start the API server:**
   ```bash
   python -m uvicorn api.main:app --reload --port 8000
   ```

### Frontend Setup
1. **Navigate to web directory:**
   ```bash
   cd web
   ```

2. **Install Node dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   Visit `http://localhost:5173`

## Usage Guide

### Basic Search
1. **Select letter count** using the number buttons (1-10)
2. **Choose first letter category** using the icon buttons:
   - `|` (Line): A, E, I, F, H, K, L, M, N, T, V, W, X, Y, Z
   - `○` (Circle): C, G, O, J, Q, S, U  
   - `⊘` (Circle with slash): B, D, P, R, J, U
3. **Click Search** to get results

### Advanced Filtering
- **Last Letter (LL)**: Optional filter for word endings
- **Vowels (V1&V2+#L)**: Enter vowel positions like "123R"
  - First digit = 1st vowel position
  - Second digit = 2nd vowel position  
  - Letters = additional required letters
- **Compound Toggle**: Choose *All*, *Simple*, or *Compound* words.  
  *Compound* includes spaced ("fire truck"), hyphenated ("rain-coat"), or glued compounds ("toothbrush").
- **Other**: Letters that must appear somewhere in the word
- **2+ Button**: Words with more than 2 vowels

### Result Filtering
- **All/Common/Uncommon**: Filter by word frequency
- **All Types/Man-made/Natural**: Filter by object origin
- **Category Filters**: Animal, Plant, Artifact, etc.
- **Click any word**: Opens Google Images search

## API Endpoints

### `POST /query`
Search for words matching criteria.

**Request Body:**
```json
{
  "length": 5,
  "category": 1,
  "v1": 2,
  "v2": 4,
  "random": "3S",
  "more_vowels": true,
  "last_category": 2,
  "must_letters": "LR",
  "compound": true
}
```

**Response:**
```json
{
  "results": [
    {
      "word": "table",
      "freq": 4.2,
      "lex": "noun.artifact",
      "manmade": true
    }
  ],
  "by_lexname": {
    "noun.artifact": 15,
    "noun.animal": 3
  }
}
```

### `GET /health`
Health check endpoint.

### `POST /query_place`
Search for places (countries or cities).

**Request Body (example):**
```json
{
  "length": 6,
  "category": 2,
  "v1": 1,
  "v2": 0,
  "place_type": "country",   // or "city"
  "region": "EU",            // Continent code (EU, AS, NA, SA, AF, OC)
  "common": true              // Only populous cities (≥1 M) / all countries
}
```

**Response:**
```json
{
  "results": [
    {
      "word": "france",
      "freq": 1.0,
      "lex": "country",
      "manmade": false
    }
  ],
  "by_lexname": {
    "country": 45
  }
}
```

### `POST /query_first_name`
Search for first names.

**Request Body (example):**
```json
{
  "length": 4,
  "category": 1,
  "v1": 2,
  "v2": 0,
  "gender": "m",        // "m", "f", or "u" (unisex)
  "origin": "US",       // ISO country code (optional)
  "common": true          // Only common names (≤200 in US/world)
}
```

**Response:**
```json
{
  "results": [
    {
      "word": "john",
      "gender": "m",
      "origin": "US"
    }
  ],
  "by_gender": {
    "m": 123,
    "f": 110
  }
}
```

## Word Database

As of 2025-06 the noun list no longer relies on WordNet. Instead we ship **9,800+ subjects** extracted from the classic "20 Q" game datasets. These are stored in `data/combined_twentyquestions.jsonl` and loaded at startup (<100 ms) with zero external downloads.

Legacy WordNet code is still present for the CLI fallback but is **not required in production**.

## Development

### Backend Development
- Hot reload enabled with `--reload` flag
- WordNet index rebuilds automatically on code changes
- API documentation available at `http://localhost:8000/docs`

### Frontend Development
- Vite provides instant hot reload
- TypeScript ensures type safety
- Tailwind classes for rapid styling
- Shadcn components for consistent UI

### Adding New Features
1. **Backend**: Add endpoints in `api/main.py`
2. **Frontend**: Update `web/src/pages/App.tsx`
3. **Word Processing**: Modify `wordnet_vowel_index.py`

## Production Deployment

### Backend
```bash
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd web
npm run build
# Serve the dist/ directory with any static file server
```

### Replit (Always-Hot) Deployment
Follow these one-time steps to deploy to Replit so the API starts once and stays hot between requests.

1. **Add the `.replit` file** (already committed in repo):
   ```ini
   run = "uvicorn api.main:app --host 0.0.0.0 --port 8000"
   ```
2. **Import the repo**: In Replit → **Create** → **Import from GitHub** → select this repository.
3. **Install & test**: Replit auto-installs `requirements.txt`; press **Run** and check `/health` returns `{ "status": "ok" }`.
4. **Keep it awake**:
   • Choose **Deploy → Reserved VM** (no sleep) **or** Enable **Autoscale** + ping `/health` every 5 min.
5. **Redeploy on changes**: Push commits to GitHub, then click **Deploy → Build & Deploy**.

After the first boot the container stays resident, so every subsequent API call responds instantly.

## Datasets

### Wiki Top Cities Dataset

**`wiki_top_cities_final.csv`** - The definitive dataset of 140 most popular cities for 20 Questions, based on Wikipedia's international visitor arrivals data.

**Columns:**
- **city**: City name
- **country**: Country name  
- **region**: Geographic region (Asia, Europe, North America, etc.)
- **clean_name**: Normalized city name
- **length**: Character count (ignoring spaces/hyphens)
- **category**: First letter category (1=vowels, 2=consonants, 3=special)
- **first_letter**: First letter of city name
- **v1**: First vowel position (1-based)
- **v2**: Second vowel position (1-based, or 0 if only one vowel)
- **vowel_count**: Total vowel count
- **all_vowel_positions**: List of all vowel positions

**Code Distribution:**
- 140 cities compressed into 55 unique codes
- **Average: 2.55 cities per code** (much better than population-based ranking)
- 56.4% of codes are unique (1 city only)
- Maximum collision: 15 cities sharing the same code

**Region Distribution:**
- Asia: 51 cities (36.4%)
- Europe: 36 cities (25.7%)  
- North America: 20 cities (14.3%)
- Middle East: 13 cities (9.3%)
- Africa: 8 cities (5.7%)
- South America: 7 cities (5.0%)
- Oceania: 3 cities (2.1%)
- Other: 2 cities (1.4%)

## Utilities

### City Code Extractor

The `extract_city_codes.py` script extracts encoding parameters for any CSV list of cities.

**Usage:**
```bash
# Print results to console
python extract_city_codes.py cities.csv

# Save results to CSV file  
python extract_city_codes.py cities.csv output_codes.csv
```

**Input:** CSV with city names (auto-detects column)  
**Output:** All encoding parameters plus preserved columns (country, region, etc.)

**Example output:**
```
City                 Length Cat FL V1 V2 Vowels  Positions 
----------------------------------------------------------------------
Paris                5      2   P  2  4  2       [2, 4]    
London               6      2   L  2  5  2       [2, 5]    
Tokyo                5      2   T  2  4  3       [2, 4, 5] 
Berlin               6      2   B  2  5  2       [2, 5]    
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Key Combination Analysis Results

### Cities Dataset (140 cities)
- **Current system** (Length + F1 + V1 + V2): **2.55 avg** cities per code, 15 max collision
- **Best system** (Length + V1 + V2 + LL): **2.03 avg** cities per code, 13 max collision (20% improvement)
- 56.4% of codes are unique (single city only)
- Maximum collision: 15 cities sharing same code

### Names Dataset Analysis (CORRECTED)

#### Actual Names Used in Production (200 names)
After simulating the **exact filtering pipeline** used in main.py:
- 104,819 total names → 75,401 (top 200 US/world rank filter) → **200 final names** (freq >= 0.4 filter)
- **Current system**: **2.41 avg** names per code (0.9x cities - actually BETTER!)
- **Best system**: **1.89 avg** names per code (Length + F1 + V1 + V2 + LL)
- 44.8% of codes are unique (single name only)
- Maximum collision: 9 names sharing same code

#### Specific Combinations for Production Names:
- **Length + F1 + V1**: 4.88 avg, 18 max collision
- **F1 + V1 + V2**: 6.67 avg, 26 max collision  
- **F1 + V1 + V2 + LL**: 3.85 avg, 24 max collision
- **Length + F1 + V1 + LL**: 3.17 avg, 16 max collision

**Key Finding**: The aggressive filtering in main.py (freq >= 0.4) reduces names to just 200 high-quality entries, making the encoding system **more efficient than cities**! Previous analysis based on full datasets was misleading.

## Acknowledgments

- **NLTK Team**: For the comprehensive WordNet database
- **WordFreq**: For word frequency data
- **Shadcn**: For beautiful UI components
- **FastAPI Team**: For the excellent web framework 

### 2025-Jun-17: Bug fix – `/query` endpoint 500

* **Problem** `WordIndex.query_category()` switched to returning `List[str]`, but the `/query` FastAPI handler still expected a list of dicts. This caused a `TypeError` and a 500 response for every request.
* **Fix** Updated `api/main.py`:
  * Import `HOLDABLE_SET`.
  * Treat return value as `words_raw: List[str]`.
  * Re-fetch holdable flag via `w in HOLDABLE_SET`.
* Front-end now receives results again. 

### 2025-Jun-17: Common / Uncommon filter restored for nouns

* Added `common: bool` field to `WordOut` model in `api/main.py` and populated it with the existing `is_common` logic (Zipf ≥ 4.0).
* Front-end logic already expects `.common`; filter now works across words, names, and places consistently. 
* Added `common` field to `PlaceOut` so place results also include it (population-based / well-known flag). 

### 2025-Jun-17: V1 / V2 vowel-category filters

* Front-end: added V1 and V2 selector buttons (reuse same 3 icon buckets). Request sends `v1_cat` / `v2_cat`.
* API: models now include `v1_cat` and `v2_cat`. Each endpoint filters words/names/places by checking the letter at the specified vowel position against `CATEGORY_MAP`. 

### 2025-Jun-17: Country key generator utility

* Added `scripts/generate_country_keys.py` to create a CSV listing unique (letters, category, V1, V2) keys for a curated set of country names.  
  ```bash
  python scripts/generate_country_keys.py > country_keys.csv
  ``` 

## Labeling noun metadata with Gemini

We use Google's Gemini-flash 2.0 to auto-label every 20-Questions subject along three dimensions:

1. **Origin** – man-made / natural / both
2. **Size** – fits-in-backpack / too-big-for-backpack / size-varies
3. **Primary category** – animal, person, food, plant, vehicle, tool, electronics, household, clothing, place, abstract, other

A helper script `scripts/build_labels_with_gemini.py` streams the 9.8 k subjects in batches of 100, writes the results to `data/thing_labels.tsv`, and is resumable.

```bash
# first 100 (dry-run)
python scripts/build_labels_with_gemini.py

# full dataset (≈ 10 batches)
python scripts/build_labels_with_gemini.py --all
```

The script needs a **temporary API key** – paste it into the `API_KEY` constant and delete after running. The key never ships to production. 