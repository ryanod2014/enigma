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
- **NLTK WordNet**: Linguistic database for word analysis
- **WordFreq**: Word frequency analysis using Zipf scores
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
  "must_letters": "LR"
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

The system uses a curated database of ~1,500 physical objects sourced from WordNet. Words are filtered to include only:

- **Physical entities**: Objects you can touch/see
- **Nouns with primary noun usage**: Excludes words primarily used as adjectives
- **Common objects**: Minimum usage frequency requirements
- **Allowed categories**: Artifacts, animals, plants, body parts, substances, vehicles

- **Places index**: …
- **First-name index**: built from U.S. SSA baby-names corpus (100k names). Optional nickname filter via built-in `nicknames.tsv`. Generate once:
  ```bash
  # automatic download
  python scripts/build_first_names.py
  # or using a locally downloaded names.zip
  python scripts/build_first_names.py --local path/to/names.zip
  ```
  Produces `data/first_names.tsv` used at runtime.

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

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

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