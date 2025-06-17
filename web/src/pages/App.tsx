import { useState, useEffect } from 'react';
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
  const [firstLetterFilter, setFirstLetterFilter] = useState<string>('all');
  const [lastLetterFilter, setLastLetterFilter] = useState<string>('all');
  const [nicknameFilter, setNicknameFilter] = useState<'all'|'nickname'|'multiple'|'none'>('all');

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
    // eslint-disable-next-line react-hooks/expressive-deps
  }, [mode]);

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

  async function submit() {
    try {
      setLoading(true);
      console.log('Submitting query...');
      
      const { v1, v2, random } = parseVowelsAndRandom(vowelsAndRandom);
      
      const body: any = { length, category, v1, v2 };
      if (random) body.random = random;
      if (moreVowels !== undefined) body.more_vowels = moreVowels;
      if (lastCategory !== null) body.last_category = lastCategory;
      if (mustLetters.trim()) body.must_letters = mustLetters.trim();
      // Add place filters if in places mode
      let endpoint = '/query';
      if (mode === 'places') {
        endpoint = '/query_place';
        // Don't send place_type - search both countries and cities
        // Send common filter to backend for places
        if (commonFilter !== 'all') {
          body.common = commonFilter === 'common';
        }
      } else if (mode === 'names') {
        endpoint = '/query_first_name';
        // no nickname param; handled client-side
      }

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
      setLexFilter('all');
      setSearched(true);
    } catch (error) {
      console.error('Error submitting query:', error);
    } finally {
      setLoading(false);
    }
  }

  // Filter results by frequency and lexical category
  const filteredByFrequency = results.filter(r => {
    if (mode === 'places') return true;

    let ok = true;
    // common/uncommon filter
    if (commonFilter === 'common') ok = ok && (r as any).common === true;
    if (commonFilter === 'uncommon') ok = ok && (r as any).common === false;

    // nickname filter (names mode only)
    if (nicknameFilter === 'nickname') ok = ok && (r as any).has_nickname === true;
    if (nicknameFilter === 'multiple') ok = ok && ((r as any).nick_count || 0) >= 2;
    if (nicknameFilter === 'none') ok = ok && (r as any).has_nickname === false;

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

  // Apply macro man-made / natural filter
  const filteredByMacro = filteredByRegion.filter(r => {
    if (macroFilter === 'all') return true;
    const isMan = r.manmade;
    if (macroFilter === 'manmade') return isMan;
    if (macroFilter === 'natural') return !isMan;
    return true;
  });

  const displayed = filteredByMacro.filter(r => {
    if (lexFilter !== 'all') {
      if (!r.lex || cleanLexName(r.lex) !== lexFilter) return false;
    }
    if (firstLetterFilter !== 'all') {
      if (r.word[0].toUpperCase() !== firstLetterFilter) return false;
    }
    if (lastLetterFilter !== 'all') {
      const last = r.word[r.word.length - 1].toUpperCase();
      if (last !== lastLetterFilter) return false;
    }
    return true;
  });

  // Update lexCounts based on frequency-filtered results with cleaned names
  const filteredLexCounts = filteredByMacro.reduce((acc, result) => {
    if (result.lex) {
      const cleanedName = cleanLexName(result.lex);
      acc[cleanedName] = (acc[cleanedName] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  // Compute counts for first-letter buttons (after all other filters except FL itself)
  const firstLetterCounts = filteredByMacro.reduce((acc, r) => {
    const fl = r.word[0].toUpperCase();
    acc[fl] = (acc[fl] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Build list after all active filters *except* last-letter so counts stay in sync
  const listBeforeLastFilter = filteredByMacro.filter(r => {
    if (lexFilter !== 'all') {
      if (!r.lex || cleanLexName(r.lex) !== lexFilter) return false;
    }
    if (firstLetterFilter !== 'all') {
      if (r.word[0].toUpperCase() !== firstLetterFilter) return false;
    }
    return true;
  });

  const lastLetterCounts = listBeforeLastFilter.reduce((acc, r) => {
    const last = r.word[r.word.length - 1].toUpperCase();
    acc[last] = (acc[last] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Reset FL and LL filters whenever new results arrive (new query)
  useEffect(() => {
    setFirstLetterFilter('all');
    setLastLetterFilter('all');
  }, [results]);

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
                  className={`min-w-[44px] h-11 ${
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

        {/* Last Letter Category (optional) */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-300">LL</label>
          <div className="flex gap-2">
            {categories.map((cat) => {
              const IconComponent = cat.icon;
              return (
                <Button
                  key={cat.id}
                  variant={lastCategory === cat.id ? "default" : "outline"}
                  size="sm"
                  className={`min-w-[44px] h-11 ${
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

        {/* More Vowels Button */}
        <div className="space-y-2">
          <div className="flex gap-2">
            <Button
              variant={moreVowels === true ? "default" : "outline"}
              size="sm"
              className={`min-w-[44px] h-11 ${
                moreVowels === true 
                  ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                  : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
              }`}
              onClick={() => setMoreVowels(moreVowels === true ? undefined : true)}
            >
              2+
            </Button>
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
              Found {filteredByMacro.length} results, showing {displayed.length}
            </div>
            
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
                All
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
                Common
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
                Uncommon
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
              <div className="flex gap-2">
                <Button
                  variant={macroFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  className={`${
                    macroFilter === 'all' 
                      ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                      : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                  }`}
                  onClick={() => setMacroFilter('all')}
                >
                  All Types
                </Button>
                <Button
                  variant={macroFilter === 'manmade' ? 'default' : 'outline'}
                  size="sm"
                  className={`${
                    macroFilter === 'manmade' 
                      ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                      : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                  }`}
                  onClick={() => setMacroFilter('manmade')}
                >
                  Man-made
                </Button>
                <Button
                  variant={macroFilter === 'natural' ? 'default' : 'outline'}
                  size="sm"
                  className={`${
                    macroFilter === 'natural' 
                      ? 'bg-gray-600 text-white hover:bg-gray-500 border-gray-600' 
                      : 'bg-transparent text-white border-gray-600 hover:bg-gray-700'
                  }`}
                  onClick={() => setMacroFilter('natural')}
                >
                  Natural
                </Button>
              </div>
            )}
            
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
                All ({filteredByMacro.length})
              </Button>
              {Object.entries(filteredLexCounts)
                .sort(([, aCount], [, bCount]) => bCount - aCount) // Sort by count descending
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

            {/* First-letter filter buttons */}
            <div className="flex flex-wrap gap-2 mt-2">
              <Button
                variant={firstLetterFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                className={`${firstLetterFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                onClick={() => setFirstLetterFilter('all')}
              >
                First: All ({filteredByMacro.length})
              </Button>
              {Object.entries(firstLetterCounts)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([letter, cnt]) => (
                  <Button
                    key={letter}
                    variant={firstLetterFilter === letter ? 'default' : 'outline'}
                    size="sm"
                    className={`${firstLetterFilter === letter ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setFirstLetterFilter(letter)}
                  >
                    {letter} ({cnt})
                  </Button>
                ))}
            </div>

            {/* Last-letter filter buttons */}
            <div className="flex flex-wrap gap-2 mt-2">
              <Button
                variant={lastLetterFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                className={`${lastLetterFilter === 'all' ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                onClick={() => setLastLetterFilter('all')}
              >
                Last: All ({displayed.length})
              </Button>
              {Object.entries(lastLetterCounts)
                .sort(([a],[b]) => a.localeCompare(b))
                .map(([letter,cnt]) => (
                  <Button
                    key={letter}
                    variant={lastLetterFilter === letter ? 'default' : 'outline'}
                    size="sm"
                    className={`${lastLetterFilter === letter ? 'bg-gray-600' : 'bg-transparent border-gray-600'}`}
                    onClick={() => setLastLetterFilter(letter)}
                  >
                    {letter} ({cnt})
                  </Button>
                ))}
            </div>

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