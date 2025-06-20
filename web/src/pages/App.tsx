import { useState, useEffect, useMemo } from 'react';
import { Loader2, Search, Minus, Circle, CircleSlash, Book, MapPin, User } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Result {
  word: string;
  freq: number;
  lex: string | null;
  manmade: boolean;
  region?: string | null;
  compound?: boolean;
}

const categories = [
  { id: 1, icon: Minus }, // "|" icon
  { id: 2, icon: Circle }, // "○" icon  
  { id: 3, icon: CircleSlash }, // "⊘" icon (circle with line through it)
];

type CommonFilter = 'all' | 'common' | 'uncommon';

export default function App() {
  const [length, setLength] = useState<number>(4);
  const [category, setCategory] = useState<number | null>(null);
  const [selectedVowels, setSelectedVowels] = useState<number[]>([1]);
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
  const [nicknameFilter, setNicknameFilter] = useState<'all'|'nickname'|'multiple'|'none'|'is_nick'>('all');
  const [msFilter, setMsFilter] = useState<'all'|'yes'|'no'>('all');
  const [sizeFilter, setSizeFilter] = useState<'all' | 'small' | 'big'>('all');
  const [compoundFilter, setCompoundFilter] = useState<'all' | 'simple' | 'compound'>('all');
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
      
      const v1 = selectedVowels[0] || 1;
      const v2 = selectedVowels[1] || 0;
      
      // Add place filters if in places mode
      let endpoint = '/query';
      if (mode === 'places') {
        endpoint = '/query_place';
        // common filter handled client-side for places
      } else if (mode === 'names') {
        endpoint = '/query_first_name';
      }

      if (category === null) {
        // No category selected - fetch all categories and merge results
        const requests = [1, 2, 3].map(cat => {
          const body: any = { length, category: cat, v1, v2 };
          if (moreVowels !== undefined) body.more_vowels = moreVowels;
          if (mustLetters) body.must_letters = mustLetters;
          if (mode === 'names' && nicknameFilter !== 'all') body.nickname = nicknameFilter;
          if (msFilter === 'yes') body.ms = true;
          if (msFilter === 'no') body.ms = false;
          if (sizeFilter === 'small') body.holdable = true;
          if (compoundFilter === 'compound') body.compound = true;
          if (compoundFilter === 'simple') body.compound = false;
          
          return fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
          });
        });

        const responses = await Promise.all(requests);
        const dataPromises = responses.map(res => {
          if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
          return res.json();
        });
        const allData = await Promise.all(dataPromises);

        // Merge results and deduplicate by word
        const mergedResults: any[] = [];
        const seenWords = new Set<string>();
        const mergedLexCounts: Record<string, number> = {};

        for (const data of allData) {
          for (const result of data.results) {
            if (!seenWords.has(result.word)) {
              mergedResults.push(result);
              seenWords.add(result.word);
            }
          }
          // Merge lex counts
          for (const [lex, count] of Object.entries(data.by_lexname || {})) {
            mergedLexCounts[lex] = (mergedLexCounts[lex] || 0) + (count as number);
          }
        }

        console.log('Merged results from all categories:', mergedResults);
        setResults(mergedResults);
        setLexCounts(mergedLexCounts);
        setLetterEfficiency(allData[0]?.letter_efficiency || []);
      } else {
        // Single category selected
        const body: any = { length, category, v1, v2 };
        if (moreVowels !== undefined) body.more_vowels = moreVowels;
        if (mustLetters) body.must_letters = mustLetters;
        if (mode === 'names' && nicknameFilter !== 'all') body.nickname = nicknameFilter;
        if (msFilter === 'yes') body.ms = true;
        if (msFilter === 'no') body.ms = false;
        if (sizeFilter === 'small') body.holdable = true;
        if (compoundFilter === 'compound') body.compound = true;
        if (compoundFilter === 'simple') body.compound = false;

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
      }
      
      setLexFilter('all');
      setSearched(true);
    } catch (error) {
      console.error('Error submitting query:', error);
    } finally {
      setLoading(false);
    }
  }

  // Apply position-based letter filters FIRST so every downstream computation already respects them
  const positionFiltered = useMemo(() => {
    return results.filter(r => {
      for (const [pos, letter] of Object.entries(positionFilters)) {
        const p = parseInt(pos);
        if (r.word.length >= p && r.word[p - 1].toUpperCase() !== letter) {
          return false;
        }
      }
      return true;
    });
  }, [results, positionFilters]);

  // Filter results by frequency and lexical category – starts from positionFiltered so counts stay in sync
  const filteredByFrequency = positionFiltered.filter(r => {
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
    if (nicknameFilter === 'is_nick') ok = ok && (r as any).is_nickname === true;

    if (msFilter === 'yes') ok = ok && ['m', 't', 's', 'f', 'w'].includes(r.word[0].toLowerCase());
    if (msFilter === 'no') ok = ok && !['m', 't', 's', 'f', 'w'].includes(r.word[0].toLowerCase());

    // Size filter (client-side)
    if (sizeFilter === 'small') ok = ok && ((r as any).holdable !== false);
    if (sizeFilter === 'big') ok = ok && ((r as any).holdable !== true);

    // Compound filter is server-side but apply client-side too for counts accuracy
    if (compoundFilter === 'compound') ok = ok && ((r as any).compound === true);
    if (compoundFilter === 'simple') ok = ok && ((r as any).compound !== true);

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

  // Compute man-made / natural counts (top-down – after position & common filters, before size)
  const manCounts = (() => {
    let base = results
      // Apply common/uncommon filter (row above)
      .filter(r => {
        if (commonFilter === 'common') return (r as any).common === true;
        if (commonFilter === 'uncommon') return (r as any).common === false;
        return true;
      })
      // Apply letter-position filters (very top)
      .filter(r => {
        for (const [pos, letter] of Object.entries(positionFilters)) {
          const p = parseInt(pos);
          if (r.word.length >= p && r.word[p - 1].toUpperCase() !== letter) return false;
        }
        return true;
      });

    // Count manmade vs natural
    let man = 0;
    let nat = 0;
    for (const r of base) {
      if (r.manmade) man++; else nat++;
    }
    return { man, nat };
  })();

  // Size counts (words mode only) before size filter is applied – now based on positionFiltered
  const sizeCounts = (() => {
    if (mode !== 'words') return { small: 0, big: 0 };
    // Build base list with all active filters EXCEPT size filter
    const base = positionFiltered.filter(r => {
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
      // Macro filter (manmade/natural)
      if (macroFilter === 'manmade') return r.manmade;
      if (macroFilter === 'natural') return !r.manmade;
      return true;
    });

    let small = 0;
    let big = 0;
    for (const r of base) {
      const holdable = (r as any).holdable;
      if (holdable === true) {
        small += 1;
      } else {
        big += 1; // undefined or explicitly non-small
      }
    }
    return { small, big };
  })();

  // Apply macro man-made / natural filter
  const filteredByMacro = filteredByRegion.filter(r => {
    if (mode==='words') {
      // Exclude adjectives, verbs, proper nouns and untouchable abstractions
      if (r.lex) {
        const intangiblePrefixes = [
          'adj.',
          'verb.',
          'noun.person',
          'noun.attribute',
          'noun.state',
          'noun.event',
          'noun.act',
          'noun.feeling',
          'noun.location',
          'noun.time'
        ];
        if (intangiblePrefixes.some(pref => (r.lex ?? '').startsWith(pref))) {
          return false;
        }
      }
    }
    if (macroFilter === 'all') return true;
    const isMan = r.manmade;
    if (macroFilter === 'manmade') return isMan;
    if (macroFilter === 'natural') return !isMan;
    return true;
  });

  // Since position filtering is already baked in, we can reuse filteredByMacro directly
  const filteredByPosition = filteredByMacro;

  // Compute common/uncommon counts after letter-position, region and macro filters but before the common filter itself
  const commonCounts = (() => {
    // Build a base list that applies every active filter EXCEPT the common/uncommon filter
    const base = results
      // Size filter comes AFTER macro, so ignore it here
      // Nickname / MS filters sit above common in Names mode, keep them
      .filter(r => {
        let ok = true;
        if (nicknameFilter === 'nickname') ok = ok && (r as any).has_nickname === true;
        if (nicknameFilter === 'multiple') ok = ok && ((r as any).nick_count || 0) >= 2;
        if (nicknameFilter === 'none') ok = ok && (r as any).has_nickname === false;
        if (nicknameFilter === 'is_nick') ok = ok && (r as any).is_nickname === true;
        if (msFilter === 'yes') ok = ok && ['m','t','s','f','w'].includes(r.word[0].toLowerCase());
        if (msFilter === 'no') ok = ok && !['m','t','s','f','w'].includes(r.word[0].toLowerCase());
        // Respect current City/Country (lex) filter as well
        if (lexFilter !== 'all') {
          if (!r.lex || cleanLexName(r.lex) !== lexFilter) ok = false;
        }
        return ok;
      })
      // Apply letter-position filters (these are at the very top of the UI stack)
      .filter(r => {
        for (const [pos, letter] of Object.entries(positionFilters)) {
          const p = parseInt(pos);
          if (r.word.length >= p && r.word[p - 1].toUpperCase() !== letter) return false;
        }
        return true;
      });

    const common = base.filter(r => (r as any).common === true).length;
    const uncommon = base.length - common;
    return { common, uncommon };
  })();

  // Total count shown in the Frequency row's "All" button
  const freqRowTotal = commonCounts.common + commonCounts.uncommon;

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

  // Compound counts (words mode only) before compound filter applied
  const compoundCounts = (() => {
    if (mode !== 'words') return { simple: 0, compound: 0 };
    const base = positionFiltered.filter(() => true); // after top position filters
    let simple = 0, compound = 0;
    for (const r of base) {
      if ((r as any).compound) compound++; else simple++;
    }
    return { simple, compound };
  })();

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
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
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
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
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
          <label className="block text-sm font-medium text-gray-300 text-right">FL</label>
          <div className="flex gap-2 justify-end">
            {categories.map((cat) => {
              const IconComponent = cat.icon;
              return (
                <Button
                  key={cat.id}
                  variant={category === cat.id ? "default" : "outline"}
                  size="sm"
                  className={`h-16 w-16 ${
                    category === cat.id 
                      ? 'bg-gray-600 text-white border-gray-600' 
                      : 'bg-transparent text-white border-gray-600'
                  }`}
                  onClick={() => setCategory(category === cat.id ? null : cat.id)}
                >
                  <IconComponent className="w-5 h-5" />
                </Button>
              );
            })}
          </div>
        </div>

        {/* V1 & V2 Selection */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300 text-right">V1&V2</label>
          <div className="grid grid-cols-5 gap-2">
            {[1, 2, 3, 4, 5].map((num) => (
              <Button
                key={`vowel-${num}`}
                variant={selectedVowels.includes(num) ? "default" : "outline"}
                size="sm"
                className={`h-11 ${
                  selectedVowels.includes(num)
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
                }`}
                onClick={() => {
                  if (selectedVowels.includes(num)) {
                    setSelectedVowels(selectedVowels.filter(v => v !== num));
                  } else if (selectedVowels.length < 2) {
                    setSelectedVowels([...selectedVowels, num].sort());
                  } else {
                    setSelectedVowels([selectedVowels[1], num].sort());
                  }
                }}
              >
                {num}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-5 gap-2">
            {[6, 7, 8, 9, 10].map((num) => (
              <Button
                key={`vowel-${num}`}
                variant={selectedVowels.includes(num) ? "default" : "outline"}
                size="sm"
                className={`h-11 ${
                  selectedVowels.includes(num)
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
                }`}
                onClick={() => {
                  if (selectedVowels.includes(num)) {
                    setSelectedVowels(selectedVowels.filter(v => v !== num));
                  } else if (selectedVowels.length < 2) {
                    setSelectedVowels([...selectedVowels, num].sort());
                  } else {
                    setSelectedVowels([selectedVowels[1], num].sort());
                  }
                }}
              >
                {num}
              </Button>
            ))}
          </div>
        </div>

        {/* Must Contain Letters (optional) */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300 text-right">Other</label>
          <input
            type="text"
            value={mustLetters}
            onChange={(e) => setMustLetters(e.target.value.toUpperCase())}
            placeholder="e.g. LRS"
            className="w-full border border-gray-600 bg-transparent text-gray-400 rounded-lg p-3 text-lg placeholder-gray-500"
          />
        </div>

        {/* Search Button */}
        <Button 
          onClick={submit} 
          className="w-full h-12 text-lg bg-transparent border border-gray-600 text-gray-400" 
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
              <div className="flex gap-2 mt-2 justify-end">
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
                      variant={lexFilter === cleanedLex ? 'default' : 'outline'}
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
            <div className="flex gap-2 justify-end">
              <Button
                variant={commonFilter === 'all' ? "default" : "outline"}
                size="sm"
                className={`${
                  commonFilter === 'all' 
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
                }`}
                onClick={() => setCommonFilter('all')}
              >
                All ({mode === 'words' ? freqRowTotal : filteredByPosition.length})
              </Button>
              <Button
                variant={commonFilter === 'common' ? "default" : "outline"}
                size="sm"
                className={`${
                  commonFilter === 'common' 
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
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
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
                }`}
                onClick={() => setCommonFilter('uncommon')}
              >
                Uncommon ({commonCounts.uncommon})
              </Button>
            </div>
            
            {/* Region buttons (after frequency row) */}
            {mode === 'places' && (
              <div className="flex flex-wrap gap-2 mt-2 justify-end">
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
                <div className="flex gap-2 justify-end">
                  <Button
                    variant={macroFilter === 'all' ? 'default' : 'outline'}
                    size="sm"
                    className={`${
                      macroFilter === 'all' 
                        ? 'bg-gray-600 text-white border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 h-11'
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
                        ? 'bg-gray-600 text-white border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 h-11'
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
                        ? 'bg-gray-600 text-white border-gray-600 h-11' 
                        : 'bg-transparent text-white border-gray-600 h-11'
                    }`}
                    onClick={() => setMacroFilter('natural')}
                  >
                    Natural ({manCounts.nat})
                  </Button>
                </div>

                {/* Size Filter Row (Small / Big) */}
                <div className="flex gap-2 mt-2 justify-end">
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

                {/* Compound Filter Row */}
                <div className="flex gap-2 mt-2 justify-end">
                  <Button
                    variant={compoundFilter === 'all' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${compoundFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setCompoundFilter('all')}
                  >
                    All ({filteredByRegion.length})
                  </Button>
                  <Button
                    variant={compoundFilter === 'simple' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${compoundFilter === 'simple' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setCompoundFilter('simple')}
                  >
                    Simple ({compoundCounts.simple})
                  </Button>
                  <Button
                    variant={compoundFilter === 'compound' ? 'default' : 'outline'}
                    size="sm"
                    className={`h-11 ${compoundFilter === 'compound' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setCompoundFilter('compound')}
                  >
                    Compound ({compoundCounts.compound})
                  </Button>
                </div>
              </>
            )}
            
            {/* Lex filter row (non-places) or second rendering for words/names */}
            {mode !== 'places' && (
            <div className="flex flex-wrap gap-2 justify-end">
              <Button
                variant={lexFilter === 'all' ? "default" : "outline"}
                size="sm"
                className={`${
                  lexFilter === 'all' 
                    ? 'bg-gray-600 text-white border-gray-600' 
                    : 'bg-transparent text-white border-gray-600'
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
                    variant={lexFilter === cleanedLex ? 'default' : 'outline'}
                    size="sm"
                    className={`${lexFilter === cleanedLex ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setLexFilter(cleanedLex)}
                  >
                    {getLexLabel(cleanedLex)} ({cnt})
                  </Button>
                ))}
            </div>
            )}

            {/* Nickname Filter Row (Names mode) */}
            {mode === 'names' && (
              <div className="flex gap-2 mt-2 justify-end">
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
                <Button
                  variant={nicknameFilter === 'is_nick' ? 'default' : 'outline'}
                  size="sm"
                  className={`${nicknameFilter === 'is_nick' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                  onClick={() => setNicknameFilter('is_nick')}
                >
                  Is Nick
                </Button>
              </div>
            )}

            {/* Letter Efficiency Helper */}
            {searched && (
                              <div className="space-y-4">
                  <label className="block text-sm font-medium text-gray-300 text-right">Most efficient positions</label>
                                    {currentLetterEfficiency.length > 0 || Object.keys(positionFilters).length > 0 ? (
                    (currentLetterEfficiency.length > 0 ? currentLetterEfficiency : 
                      Object.keys(positionFilters).map(pos => [
                        parseInt(pos), 
                        { uniqueLetters: 1, distribution: { [positionFilters[parseInt(pos)]]: 0 } }
                      ] as [number, { uniqueLetters: number; distribution: Record<string, number> }])
                    ).map(([pos, data], index) => (
                      <div key={pos} className="space-y-2">
                        <div className="flex items-center gap-2 justify-end">
                          <span className="text-sm text-gray-400">#{index + 1}:</span>
                          <span className="text-sm font-medium text-gray-300">Position {pos}</span>
                          {positionFilters[pos] && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 px-2 text-xs bg-transparent border-gray-600 text-gray-400"
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
                        <div className="flex flex-wrap gap-1 justify-end">
                          {Object.entries(data.distribution)
                            .sort(([, aCount], [, bCount]) => bCount - aCount)
                            .map(([letter, count]) => (
                              <Button
                                key={letter}
                                size="sm"
                                variant={positionFilters[pos] === letter ? 'default' : 'outline'}
                                className={`h-8 px-2 text-xs ${
                                  positionFilters[pos] === letter
                                    ? 'bg-gray-600 text-white border-gray-600'
                                    : 'bg-transparent text-gray-400 border-gray-600'
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
                    className="border border-gray-600 bg-transparent rounded-lg p-3 flex justify-between items-center cursor-pointer"
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