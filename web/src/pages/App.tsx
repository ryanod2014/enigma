import { useState, useEffect, useMemo } from 'react';
import { Loader2, Search, Minus, Circle, CircleSlash, Book, MapPin, User } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Result {
  word: string;
  freq: number;
  lex: string | null;
  manmade: boolean;
  region?: string | null;
}

const categories = [
  { id: 1, icon: Minus }, // "|" icon
  { id: 2, icon: Circle }, // "○" icon  
  { id: 3, icon: CircleSlash }, // "⊘" icon (circle with line through it)
];

type CommonFilter = 'all' | 'common' | 'uncommon';

export default function App() {
  const [length, setLength] = useState<number>(4);
  const [category, setCategory] = useState<number>(1);
  const [lastCategory, setLastCategory] = useState<number | null>(null);
  const [v1Category, setV1Category] = useState<number | null>(null);
  const [v2Category, setV2Category] = useState<number | null>(null);
  const [vowelsAndRandom, setVowelsAndRandom] = useState<string>(''); // Combined input like "123R"
  const [mustLetters, setMustLetters] = useState<string>('');
  const [moreVowels, setMoreVowels] = useState<boolean | undefined>();
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false); // true after first query
  const [commonFilter, setCommonFilter] = useState<CommonFilter>('all');
  const [macroFilter, setMacroFilter] = useState<'all' | 'manmade' | 'natural'>('all');
  const [results, setResults] = useState<Result[]>([]);
  const [lexFilter, setLexFilter] = useState<string>('all');
  const [lexCounts, setLexCounts] = useState<Record<string, number>>({});
  const [mode, setMode] = useState<'words' | 'places' | 'names'>('words');
  const [regionFilter, setRegionFilter] = useState<string>(''); // continent code filter
  const [nicknameFilter, setNicknameFilter] = useState<'all'|'nickname'|'multiple'|'none'>('all');
  const [msFilter, setMsFilter] = useState<'all'|'yes'|'no'>('all');
  const [sizeFilter, setSizeFilter] = useState<'all' | 'small' | 'big'>('all');
  const [letterEfficiency, setLetterEfficiency] = useState<number[]>([]);
  const [positionFilters, setPositionFilters] = useState<Record<number, string>>({});

  const REGION_LABELS: Record<string,string> = {
    'EU': 'Europe',
    'AS': 'Asia',
    'NA': 'North America',
    'SA': 'South America',
    'AF': 'Africa',
    'OC': 'Oceania',
    'OTHER': 'Other',
  };

  // Re-run query automatically when server-side filters change
  useEffect(() => {
    if (mode === 'places') {
      submit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, msFilter]);

  // No lex set needed; API provides manmade flag

  // Parse vowelsAndRandom input like "123R" -> v1=1, v2=2, random="3R"
  function parseVowelsAndRandom(input: string) {
    if (!input) return { v1: 1, v2: 0, random: '' };
    
    const digits = input.match(/\d/g) || [];
    const letters = input.match(/[A-Z]/gi) || [];
    
    const v1 = digits[0] ? parseInt(digits[0]) : 1;
    const v2 = digits[1] ? parseInt(digits[1]) : 0;
    const random = digits.slice(2).join('') + letters.join('');
    
    return { v1, v2, random };
  }

  // Clean up lexical category names (e.g. "noun.artifact" -> "Artifact")
  function cleanLexName(lex: string): string {
    return lex.replace('noun.', '').charAt(0).toUpperCase() + lex.replace('noun.', '').slice(1);
  }

  // Helper to pretty-print gender code in Names mode
  const getLexLabel = (code: string) => {
    if (mode === 'names') {
      const map: Record<string, string> = { m: 'Male', f: 'Female', u: 'Unisex' };
      return map[code.toLowerCase()] || code;
    }
    return code;
  };

  const handleSizeFilter = (newFilter: 'small' | 'big') => {
    setSizeFilter(prev => prev === newFilter ? 'all' : newFilter);
  };

  async function submit() {
    try {
      setLoading(true);
      console.log('Submitting query...');
      
      const { v1, v2, random } = parseVowelsAndRandom(vowelsAndRandom);
      
      const body: any = { length, category, v1, v2 };
      if (random) body.random = random;
      if (moreVowels !== undefined) body.more_vowels = moreVowels;
      if (lastCategory !== null) body.last_category = lastCategory;
      if (v1Category !== null) body.v1_cat = v1Category;
      if (v2Category !== null) body.v2_cat = v2Category;
      if (mustLetters.trim()) body.must_letters = mustLetters.trim();
      // Add place filters if in places mode
      let endpoint = '/query';
      if (mode === 'places') {
        endpoint = '/query_place';
        // common filter handled client-side for places
      } else if (mode === 'names') {
        endpoint = '/query_first_name';
        // no nickname param; handled client-side
      }

      // rhyme filter removed
      if (msFilter === 'yes') body.ms = true;
      if (msFilter === 'no') body.ms = false;
      if (sizeFilter === 'small') { body.holdable = true; }
      else if (sizeFilter === 'big') { body.holdable = false; }

      console.log('Request body:', body);
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      console.log('Response data:', data);
      setResults(data.results);
      setLexCounts(data.by_lexname);
      setLetterEfficiency(data.letter_efficiency || []);
      setLexFilter('all');
      setSearched(true);
    } catch (error) {
      console.error('Error submitting query:', error);
    } finally {
      setLoading(false);
    }
  }

  // Compute common/uncommon counts after applying all active filters EXCEPT common filter itself
  const baseForCommon = (() => {
    // Start with raw results then apply every filter except common/uncommon flag
    // 1) nickname/ms/size filters (same logic as filteredByFrequency but skipping common)
    return results.filter(r => {
      let ok = true;
      if (mode === 'places') {
        // nickname filters not used in places
      } else {
        // nickname filter (names mode only)
        if (nicknameFilter === 'nickname') ok = ok && (r as any).has_nickname === true;
        if (nicknameFilter === 'multiple') ok = ok && ((r as any).nick_count || 0) >= 2;
        if (nicknameFilter === 'none') ok = ok && (r as any).has_nickname === false;
      }

      if (msFilter === 'yes') ok = ok && ['m','t','s','f','w'].includes(r.word[0].toLowerCase());
      if (msFilter === 'no') ok = ok && !['m','t','s','f','w'].includes(r.word[0].toLowerCase());

      if (sizeFilter === 'small') ok = ok && ((r as any).holdable !== false);
      if (sizeFilter === 'big') ok = ok && ((r as any).holdable !== true);

      // Region filter for places
      if(mode==='places' && regionFilter){
        const code = r.region ? r.region.toUpperCase() : 'OTHER';
        ok = ok && code === regionFilter;
      }

      // Macro filter for words
      if(mode==='words'){
        if(macroFilter==='manmade') ok = ok && r.manmade;
        if(macroFilter==='natural') ok = ok && !r.manmade;
      }

      // Position-based letter filters
      for (const [pos, letter] of Object.entries(positionFilters)) {
        const position = parseInt(pos);
        if (r.word.length >= position && r.word[position - 1].toUpperCase() !== letter) {
          ok = false;
          break;
        }
      }

      // Lex filters
      if (lexFilter !== 'all') {
        if (!r.lex || cleanLexName(r.lex) !== lexFilter) ok = false;
      }
      return ok;
    });
  })();

  const commonCounts = baseForCommon.reduce((acc, r)=>{
    const isCommon = (r as any).common === true;
    if(isCommon) acc.common +=1; else acc.uncommon +=1;
    return acc;
  }, {common:0, uncommon:0});

  // Filter results by frequency and lexical category
  const filteredByFrequency = results.filter(r => {
    let ok = true;
    if (mode === 'places') {
      if (commonFilter === 'common') ok = ok && (r as any).common === true;
      if (commonFilter === 'uncommon') ok = ok && (r as any).common === false;
      return ok;
    }

    if (commonFilter === 'common') ok = ok && (r as any).common === true;
    if (commonFilter === 'uncommon') ok = ok && (r as any).common === false;

    // nickname filter (names mode only)
    if (nicknameFilter === 'nickname') ok = ok && (r as any).has_nickname === true;
    if (nicknameFilter === 'multiple') ok = ok && ((r as any).nick_count || 0) >= 2;
    if (nicknameFilter === 'none') ok = ok && (r as any).has_nickname === false;

    if (msFilter === 'yes') ok = ok && ['m', 't', 's', 'f', 'w'].includes(r.word[0].toLowerCase());
    if (msFilter === 'no') ok = ok && !['m', 't', 's', 'f', 'w'].includes(r.word[0].toLowerCase());

    // Size filter (client-side)
    if (sizeFilter === 'small') ok = ok && ((r as any).holdable !== false);
    if (sizeFilter === 'big') ok = ok && ((r as any).holdable !== true);

    return ok;
  });

  // Apply region filter (places mode only)
  const filteredByRegion = filteredByFrequency.filter(r => {
    if(mode==='places' && regionFilter) {
       const itemRegion = r.region ? r.region.toUpperCase() : 'OTHER';
       return itemRegion === regionFilter;
    }
    return true;
  });

  // Compute region counts from filteredByFrequency (before region filter) so counts show totals
  const regionCounts = filteredByFrequency.reduce((acc, r) => {
     const code = r.region ? r.region.toUpperCase() : 'OTHER';
     acc[code] = (acc[code] || 0) + 1;
     return acc;
  }, {} as Record<string, number>);

  // Add "All" count 
  const totalCount = Object.values(regionCounts).reduce((sum, count) => sum + count, 0);
  const regionCountsWithAll = { '': totalCount, ...regionCounts };

  // Compute man-made / natural counts (from filteredByRegion before macro filter)
  const manCounts = filteredByRegion.reduce((acc, r) => {
    if (r.manmade) acc.man += 1; else acc.nat += 1;
    return acc;
  }, {man:0, nat:0});

  // Size counts (words mode only) before size filter is applied
  const sizeCounts = (() => {
    if (mode !== 'words') return { small: 0, big: 0 };
    // Build base list with all active filters EXCEPT size filter
    const base = results.filter(r => {
      let ok = true;
      // apply same filters as filteredByFrequency but skip size filter logic
      if (commonFilter === 'common') ok = ok && (r as any).common === true;
      if (commonFilter === 'uncommon') ok = ok && (r as any).common === false;

      if (nicknameFilter === 'nickname') ok = ok && (r as any).has_nickname === true;
      if (nicknameFilter === 'multiple') ok = ok && ((r as any).nick_count || 0) >= 2;
      if (nicknameFilter === 'none') ok = ok && (r as any).has_nickname === false;

      if (msFilter === 'yes') ok = ok && ['m','t','s','f','w'].includes(r.word[0].toLowerCase());
      if (msFilter === 'no') ok = ok && !['m','t','s','f','w'].includes(r.word[0].toLowerCase());

      return ok;
    }).filter(r => {
      // region filter (places not relevant here), but keep consistent with words mode
      return true;
    }).filter(r => {
      // Macro filter (manmade/natural)
      if (macroFilter === 'manmade') return r.manmade;
      if (macroFilter === 'natural') return !r.manmade;
      return true;
    }).filter(r => {
      // Region filter not applied for words mode
      return true;
    });

    let small = 0;
    let big = 0;
    for (const r of base) {
      const holdable = (r as any).holdable;
      if (holdable !== false) small += 1;
      if (holdable !== true) big += 1;
    }
    return { small, big };
  })();

  // Apply macro man-made / natural filter
  const filteredByMacro = filteredByRegion.filter(r => {
    if (mode==='words') {
      // Exclude adjectives, verbs, proper nouns and untouchable abstractions
      if (r.lex && (r.lex.startsWith('adj.') || r.lex.startsWith('verb.') || r.lex.startsWith('noun.person'))) {
        return false;
      }
      if ((r as any).holdable === false) {
        return false; // cannot touch/hold
      }
    }
    if (macroFilter === 'all') return true;
    const isMan = r.manmade;
    if (macroFilter === 'manmade') return isMan;
    if (macroFilter === 'natural') return !isMan;
    return true;
  });

  // Apply position-based letter filters early so all subsequent counts are affected
  const filteredByPosition = filteredByMacro.filter(r => {
    for (const [pos, letter] of Object.entries(positionFilters)) {
      const position = parseInt(pos);
      if (r.word.length >= position && r.word[position - 1].toUpperCase() !== letter) {
        return false;
      }
    }
    return true;
  });

  const displayed = filteredByPosition.filter(r => {
    if (lexFilter !== 'all') {
      if (!r.lex || cleanLexName(r.lex) !== lexFilter) return false;
    }
    return true;
  });

  // Update lexCounts based on position-filtered results with cleaned names
  const filteredLexCounts = filteredByPosition.reduce((acc, result) => {
    if (result.lex) {
      const cleanedName = cleanLexName(result.lex);
      acc[cleanedName] = (acc[cleanedName] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);



  // Reset position filters whenever new results arrive (new query)
  useEffect(() => {
    setPositionFilters({});
  }, [results]);

  // Clear previous results when switching modes to avoid showing stale filters
  useEffect(() => {
    setResults([]);
    setLexCounts({});
    setSearched(false);
  }, [mode]);

  // Calculate letter efficiency for currently displayed results
  const currentLetterEfficiency = useMemo(() => {
    // Use filteredByPosition so efficiency updates based on position filters already applied
    const sourceResults = filteredByPosition.length > 0 ? filteredByPosition : (filteredByMacro.length > 0 ? filteredByMacro : results);
    if (sourceResults.length <= 1) return [];
    
    const letterPositions: Record<number, { uniqueLetters: number; distribution: Record<string, number> }> = {};
    
    for (let i = 1; i <= 10; i++) {
      const letterCounts: Record<string, number> = {};
      let validWords = 0;
      
      for (const r of sourceResults) {
        if (r.word.length >= i) {
          const letter = r.word[i-1].toUpperCase();
          letterCounts[letter] = (letterCounts[letter] || 0) + 1;
          validWords++;
        }
      }
      
      if (validWords > 0) {
        const uniqueLetters = Object.keys(letterCounts).length;
        letterPositions[i] = { uniqueLetters, distribution: letterCounts };
      }
    }
    
    // Get positions with active filters
    const activeFilterPositions = Object.keys(positionFilters).map(Number);
    
    // Get top efficient positions (excluding ones with active filters to avoid duplicates)
    const topEfficient = Object.entries(letterPositions)
      .filter(([pos]) => !activeFilterPositions.includes(parseInt(pos)))
      .sort(([, a], [, b]) => b.uniqueLetters - a.uniqueLetters)
      .slice(0, 3 - activeFilterPositions.length)
      .map(([pos, data]) => [parseInt(pos), data] as [number, { uniqueLetters: number; distribution: Record<string, number> }]);
    
    // Combine active filter positions with top efficient ones
    const activePositions = activeFilterPositions
      .map(pos => {
        // If position has data, use it; otherwise create synthetic data for the active filter
        const data = letterPositions[pos] || {
          uniqueLetters: 1,
          distribution: { [positionFilters[pos]]: 0 }
        };
        return [pos, data] as [number, { uniqueLetters: number; distribution: Record<string, number> }];
      });
    
    return [...activePositions, ...topEfficient];
  }, [filteredByPosition, filteredByMacro, results, positionFilters]);

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto p-4 pt-12 space-y-6">
        {/* Mode Toggle – 3 equal-width icon buttons */}
        <div className="grid grid-cols-3 gap-2 w-full">
          <Button
            variant={mode === 'words' ? 'default' : 'outline'}
            size="sm"
            className={`flex items-center justify-center h-12 ${mode === 'words' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
            onClick={() => setMode('words')}
          >
            <Book className="w-6 h-6" aria-label="Words" />
          </Button>
          <Button
            variant={mode === 'places' ? 'default' : 'outline'}
            size="sm"
            className={`flex items-center justify-center h-12 ${mode === 'places' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
            onClick={() => setMode('places')}
          >
            <MapPin className="w-6 h-6" aria-label="Places" />
          </Button>
          <Button
            variant={mode === 'names' ? 'default' : 'outline'}
            size="sm"
            className={`flex items-center justify-center h-12 ${mode === 'names' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
            onClick={() => setMode('names')}
          >
            <User className="w-6 h-6" aria-label="Names" />
          </Button>
        </div>

        {/* Length Selection - Mobile-first button row */}
        <div className="space-y-2">
          <div className="grid grid-cols-5 gap-2">
            {[1, 2, 3, 4, 5].map((num) => (
              <Button
                key={num}
                variant={length === num ? "default" : "outline"}
                size="sm"
                className={`h-11 ${
                  length === num 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setLength(num)}
              >
                {num}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-5 gap-2">
            {[6, 7, 8, 9, 10].map((num) => (
              <Button
                key={num}
                variant={length === num ? "default" : "outline"}
                size="sm"
                className={`h-11 ${
                  length === num 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setLength(num)}
              >
                {num}
              </Button>
            ))}
          </div>
        </div>

        {/* Category Selection - Icon buttons only */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">FL</label>
          <div className="flex gap-2">
            {categories.map((cat) => {
              const IconComponent = cat.icon;
              return (
                <Button
                  key={cat.id}
                  variant={category === cat.id ? "default" : "outline"}
                  size="sm"
                  className={`min-w-[36px] h-10 sm:min-w-[44px] sm:h-11 ${
                    category === cat.id 
                      ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                      : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                  }`}
                  onClick={() => setCategory(cat.id)}
                >
                  <IconComponent className="w-5 h-5" />
                </Button>
              );
            })}
          </div>
        </div>

        {/* Combined Vowels & Random Input */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">V1&V2+#L</label>
          <input 
            type="text" 
            value={vowelsAndRandom} 
            onChange={(e) => setVowelsAndRandom(e.target.value.toUpperCase())}
            placeholder="e.g. 123R"
            className="w-full border border-gray-600 bg-transparent text-gray-400 rounded-lg p-3 text-lg placeholder-gray-500"
          />
        </div>

        {/* Must Contain Letters (optional) */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">Other</label>
          <input
            type="text"
            value={mustLetters}
            onChange={(e) => setMustLetters(e.target.value.toUpperCase())}
            placeholder="e.g. LRS"
            className="w-full border border-gray-600 bg-transparent text-gray-400 rounded-lg p-3 text-lg placeholder-gray-500"
          />
        </div>

        {/* V1, V2, LL Categories – same row with dividers */}
        <div className="flex divide-x divide-gray-600">
          {/* V1 */}
          <div className="flex flex-col items-center space-y-1 sm:space-y-2 px-2 flex-1">
            <span className="text-sm font-medium text-gray-300">V1</span>
            <div className="flex gap-2 justify-center">
              {categories.map((cat) => {
                const IconComponent = cat.icon;
                return (
                  <Button
                    key={cat.id}
                    variant={v1Category === cat.id ? 'default' : 'outline'}
                    size="sm"
                    className={`min-w-[36px] h-10 sm:min-w-[44px] sm:h-11 ${
                      v1Category === cat.id
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600'
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                    }`}
                    onClick={() => setV1Category(v1Category === cat.id ? null : cat.id)}
                  >
                    <IconComponent className="w-5 h-5" />
                  </Button>
                );
              })}
            </div>
          </div>

          {/* V2 */}
          <div className="flex flex-col items-center space-y-1 sm:space-y-2 px-2 flex-1">
            <span className="text-sm font-medium text-gray-300">V2</span>
            <div className="flex gap-2 justify-center">
              {categories.map((cat) => {
                const IconComponent = cat.icon;
                return (
                  <Button
                    key={cat.id}
                    variant={v2Category === cat.id ? 'default' : 'outline'}
                    size="sm"
                    className={`min-w-[36px] h-10 sm:min-w-[44px] sm:h-11 ${
                      v2Category === cat.id
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600'
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                    }`}
                    onClick={() => setV2Category(v2Category === cat.id ? null : cat.id)}
                  >
                    <IconComponent className="w-5 h-5" />
                  </Button>
                );
              })}
            </div>
          </div>

          {/* LL */}
          <div className="flex flex-col items-center space-y-1 sm:space-y-2 px-2 flex-1">
            <span className="text-sm font-medium text-gray-300">LL</span>
            <div className="flex gap-2 justify-center">
              {categories.map((cat) => {
                const IconComponent = cat.icon;
                return (
                  <Button
                    key={cat.id}
                    variant={lastCategory === cat.id ? 'default' : 'outline'}
                    size="sm"
                    className={`min-w-[36px] h-10 sm:min-w-[44px] sm:h-11 ${
                      lastCategory === cat.id
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600'
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                    }`}
                    onClick={() => setLastCategory(lastCategory === cat.id ? null : cat.id)}
                  >
                    <IconComponent className="w-5 h-5" />
                  </Button>
                );
              })}
            </div>
          </div>
        </div>

        {/* More Vowels + MTSF Filter Row */}
        <div className="space-y-2">
          <div className="flex gap-2 items-center flex-wrap">
            <Button
              variant={moreVowels === true ? "default" : "outline"}
              size="sm"
              className={`min-w-[36px] h-10 sm:min-w-[44px] sm:h-11 ${
                moreVowels === true 
                  ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                  : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
              }`}
              onClick={() => setMoreVowels(moreVowels === true ? undefined : true)}
            >
              V=2+
            </Button>
            {/* MTSF buttons inline */}
            <Button variant={msFilter === 'yes' ? 'default' : 'outline'} size="sm" className={`h-11 ${msFilter === 'yes' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`} onClick={() => setMsFilter(msFilter === 'yes' ? 'all' : 'yes')}>✓ M/T/W/F/S</Button>
            <Button variant={msFilter === 'no' ? 'default' : 'outline'} size="sm" className={`h-11 ${msFilter === 'no' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`} onClick={() => setMsFilter(msFilter === 'no' ? 'all' : 'no')}>✕ M/T/W/F/S</Button>
            {mode === 'words' && (
              <></>
            )}
          </div>
        </div>

        {/* Search Button */}
        <Button 
          onClick={submit} 
          className="w-full h-12 text-lg bg-transparent hover:bg-gray-700 border border-gray-600 text-gray-400" 
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="animate-spin mr-2" size={20} />
          ) : (
            <Search className="mr-2" size={20} />
          )}
          Search
        </Button>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12 space-y-4 text-white">
            <Loader2 className="animate-spin h-8 w-8 text-blue-600" />
            <p className="text-lg font-medium">Searching for words...</p>
            <p className="text-sm text-gray-500">This may take a moment</p>
          </div>
        )}

        {/* Results */}
        {!loading && searched && (
          <div className="space-y-4">
            <div className="text-sm text-gray-400">
              Found {filteredByPosition.length} results, showing {displayed.length}
            </div>
            
            {/* City / Country filter row - now above frequency row */}
            {mode === 'places' && (
              <div className="flex gap-2 mt-2">
                <Button
                  variant={lexFilter === 'all' ? "default" : "outline"}
                  size="sm"
                  className={`${lexFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setLexFilter('all')}
                >
                  All ({filteredByPosition.length})
                </Button>
                {Object.entries(filteredLexCounts)
                  .sort(([, aCount], [, bCount]) => bCount - aCount)
                  .map(([cleanedLex, cnt]) => (
                    <Button
                      key={cleanedLex}
                      variant={lexFilter === cleanedLex ? "default" : "outline"}
                      size="sm"
                      className={`${lexFilter === cleanedLex ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                      onClick={() => setLexFilter(cleanedLex)}
                    >
                      {getLexLabel(cleanedLex)} ({cnt})
                    </Button>
                  ))}
              </div>
            )}
            
            {/* Frequency + Nickname Filter Buttons */}
            <div className="flex gap-2">
              <Button
                variant={commonFilter === 'all' ? "default" : "outline"}
                size="sm"
                className={`${
                  commonFilter === 'all' 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setCommonFilter('all')}
              >
                All ({results.length})
              </Button>
              <Button
                variant={commonFilter === 'common' ? "default" : "outline"}
                size="sm"
                className={`${
                  commonFilter === 'common' 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setCommonFilter('common')}
              >
                Common ({commonCounts.common})
              </Button>
              <Button
                variant={commonFilter === 'uncommon' ? "default" : "outline"}
                size="sm"
                className={`${
                  commonFilter === 'uncommon' 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setCommonFilter('uncommon')}
              >
                Uncommon ({commonCounts.uncommon})
              </Button>
            </div>
            
            {/* Region buttons (after frequency row) */}
            {mode === 'places' && (
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.entries(regionCountsWithAll).filter(([code,c])=>c>0).map(([code,count])=> (
                  <Button
                    key={code}
                    variant={regionFilter === code ? 'default' : 'outline'}
                    size="sm"
                    className={`${regionFilter === code ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setRegionFilter(code)}
                  >
                    {(code && REGION_LABELS[code]) || 'All'} ({count})
                  </Button>
                ))}
              </div>
            )}
            
            {/* Macro Man-made / Natural Filter Buttons - Only show for Words mode */}
            {mode === 'words' && (
              <>
                <div className="flex gap-2">
                  <Button
                    variant={macroFilter === 'all' ? 'default' : 'outline'}
                    size="sm"
                    className={`${
                      macroFilter === 'all' 
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700 h-11'
                    }`}
                    onClick={() => setMacroFilter('all')}
                  >
                    All Types ({filteredByRegion.length})
                  </Button>
                  <Button
                    variant={macroFilter === 'manmade' ? 'default' : 'outline'}
                    size="sm"
                    className={`${
                      macroFilter === 'manmade' 
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700 h-11'
                    }`}
                    onClick={() => setMacroFilter('manmade')}
                  >
                    Man-made ({manCounts.man})
                  </Button>
                  <Button
                    variant={macroFilter === 'natural' ? 'default' : 'outline'}
                    size="sm"
                    className={`${
                      macroFilter === 'natural' 
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700 h-11'
                    }`}
                    onClick={() => setMacroFilter('natural')}
                  >
                    Natural ({manCounts.nat})
                  </Button>
                </div>

                {/* Size Filter Row (Small / Big) */}
                <div className="flex gap-2 mt-2">
                  <Button
                    variant={sizeFilter === 'all' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${sizeFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setSizeFilter('all')}
                  >
                    Any Size ({filteredByRegion.length})
                  </Button>
                  <Button
                    variant={sizeFilter === 'small' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${sizeFilter === 'small' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => handleSizeFilter('small')}
                  >
                    Small ({sizeCounts.small})
                  </Button>
                  <Button
                    variant={sizeFilter === 'big' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${sizeFilter === 'big' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => handleSizeFilter('big')}
                  >
                    Big ({sizeCounts.big})
                  </Button>
                </div>
              </>
            )}
            
            {/* Lex filter row (non-places) or second rendering for words/names */}
            {mode !== 'places' && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant={lexFilter === 'all' ? "default" : "outline"}
                size="sm"
                className={`${
                  lexFilter === 'all' 
                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                    : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                }`}
                onClick={() => setLexFilter('all')}
              >
                All ({filteredByPosition.length})
              </Button>
              {Object.entries(filteredLexCounts)
                .sort(([, aCount], [, bCount]) => bCount - aCount)
                .map(([cleanedLex, cnt]) => (
                  <Button
                    key={cleanedLex}
                    variant={lexFilter === cleanedLex ? "default" : "outline"}
                    size="sm"
                    className={`${
                      lexFilter === cleanedLex 
                        ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                        : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                    }`}
                    onClick={() => setLexFilter(cleanedLex)}
                  >
                    {getLexLabel(cleanedLex)} ({cnt})
                  </Button>
                ))}
            </div>
            )}



            {/* Nickname Filter Row (Names mode) */}
            {mode === 'names' && (
              <div className="flex gap-2 mt-2">
                <Button
                  variant={nicknameFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  className={`${nicknameFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setNicknameFilter('all')}
                >
                  Any
                </Button>
                <Button
                  variant={nicknameFilter === 'none' ? 'default' : 'outline'}
                  size="sm"
                  className={`${nicknameFilter === 'none' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setNicknameFilter('none')}
                >
                  None
                </Button>
                <Button
                  variant={nicknameFilter === 'nickname' ? 'default' : 'outline'}
                  size="sm"
                  className={`${nicknameFilter === 'nickname' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setNicknameFilter('nickname')}
                >
                  Nickname
                </Button>
                <Button
                  variant={nicknameFilter === 'multiple' ? 'default' : 'outline'}
                  size="sm"
                  className={`${nicknameFilter === 'multiple' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setNicknameFilter('multiple')}
                >
                  Multiple
                </Button>
              </div>
            )}

            {/* Letter Efficiency Helper */}
            {searched && (
                              <div className="space-y-4">
                  <label className="block text-sm font-medium text-gray-300">Most efficient positions</label>
                                    {currentLetterEfficiency.length > 0 || Object.keys(positionFilters).length > 0 ? (
                    (currentLetterEfficiency.length > 0 ? currentLetterEfficiency : 
                      Object.keys(positionFilters).map(pos => [
                        parseInt(pos), 
                        { uniqueLetters: 1, distribution: { [positionFilters[parseInt(pos)]]: 0 } }
                      ] as [number, { uniqueLetters: number; distribution: Record<string, number> }])
                    ).map(([pos, data], index) => (
                      <div key={pos} className="space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-400">#{index + 1}:</span>
                          <span className="text-sm font-medium text-gray-300">Position {pos}</span>
                          {positionFilters[pos] && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 px-2 text-xs bg-transparent border-gray-600 text-gray-400 hover:bg-gray-700"
                              onClick={() => {
                                setPositionFilters(prev => {
                                  const newFilters = { ...prev };
                                  delete newFilters[pos];
                                  return newFilters;
                                });
                              }}
                            >
                              Clear
                            </Button>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(data.distribution)
                            .sort(([, aCount], [, bCount]) => bCount - aCount)
                            .map(([letter, count]) => (
                              <Button
                                key={letter}
                                size="sm"
                                variant={positionFilters[pos] === letter ? 'default' : 'outline'}
                                className={`h-8 px-2 text-xs ${
                                  positionFilters[pos] === letter
                                    ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600'
                                    : 'bg-transparent text-gray-400 border-gray-600 hover:bg-gray-700'
                                }`}
                                onClick={() => {
                                  setPositionFilters(prev => {
                                    const newFilters = { ...prev };
                                    if (newFilters[pos] === letter) {
                                      delete newFilters[pos];
                                    } else {
                                      newFilters[pos] = letter;
                                    }
                                    return newFilters;
                                  });
                                }}
                              >
                                {letter} ({count})
                              </Button>
                            ))}
                        </div>
                      </div>
                    ))
                  ) : Object.keys(positionFilters).length > 0 ? (
                    <div className="text-sm text-gray-400">
                      Active position filters - clear filters or search again to see suggestions
                    </div>
                  ) : (
                    <div className="text-sm text-gray-400">
                      Search for words to see position suggestions
                    </div>
                  )}
                </div>
              )}

            {displayed.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {displayed.map((r) => (
                  <div 
                    key={r.word} 
                    className="border border-gray-600 bg-transparent rounded-lg p-3 flex justify-between items-center cursor-pointer hover:bg-gray-900 transition-colors"
                    onClick={() => window.open(`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(r.word)}`, '_blank')}
                  >
                    <span className="font-medium text-gray-400">{r.word}</span>
                    <span className="text-sm text-gray-500">{r.freq.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-center py-8">
                No words found matching your criteria
              </div>
            )}
          </div>
        )}

        {/* No results after search completed */}
        {!loading && Object.keys(lexCounts).length === 0 && results.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <div className="text-gray-400 mb-2">
              <Search className="h-12 w-12 mx-auto mb-4" />
            </div>
            <p className="text-lg text-gray-600">No results yet</p>
            <p className="text-lg text-gray-400">No results yet</p>
            <p className="text-sm text-gray-500">Enter your search criteria and click Search</p>
            <p className="text-sm text-gray-500">Enter your search criteria and click Search</p>
          </div>
        )}
      </div>
    </div>
  );
} 