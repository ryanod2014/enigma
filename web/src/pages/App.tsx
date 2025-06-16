import { useState } from 'react';
import { Loader2, Search, Minus, Circle, CircleSlash } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Result {
  word: string;
  freq: number;
  lex: string | null;
  manmade: boolean;
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
  const [commonFilter, setCommonFilter] = useState<CommonFilter>('all');
  const [macroFilter, setMacroFilter] = useState<'all' | 'manmade' | 'natural'>('all');
  const [results, setResults] = useState<Result[]>([]);
  const [lexFilter, setLexFilter] = useState<string>('all');
  const [lexCounts, setLexCounts] = useState<Record<string, number>>({});

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
      // Don't send commonFilter to backend - we'll filter client-side
      console.log('Request body:', body);
      const res = await fetch('/query', {
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
    } catch (error) {
      console.error('Error submitting query:', error);
    } finally {
      setLoading(false);
    }
  }

  // Filter results by frequency and lexical category
  const filteredByFrequency = results.filter(r => {
    if (commonFilter === 'all') return true;
    if (commonFilter === 'common') return r.freq >= 1.0;
    if (commonFilter === 'uncommon') return r.freq < 1.0;
    return true;
  });

  // Apply macro man-made / natural filter
  const filteredByMacro = filteredByFrequency.filter(r => {
    if (macroFilter === 'all') return true;
    const isMan = r.manmade;
    if (macroFilter === 'manmade') return isMan;
    if (macroFilter === 'natural') return !isMan;
    return true;
  });

  const displayed = filteredByMacro.filter(r => {
    if (lexFilter === 'all') return true;
    return r.lex && cleanLexName(r.lex) === lexFilter;
  });

  // Update lexCounts based on frequency-filtered results with cleaned names
  const filteredLexCounts = filteredByMacro.reduce((acc, result) => {
    if (result.lex) {
      const cleanedName = cleanLexName(result.lex);
      acc[cleanedName] = (acc[cleanedName] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto p-4 pt-12 space-y-6">
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
            className="w-full border border-gray-600 bg-gray-800 text-white rounded-lg p-3 text-lg placeholder-gray-400"
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
            className="w-full border border-gray-600 bg-gray-800 text-white rounded-lg p-3 text-lg placeholder-gray-400"
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
          className="w-full h-12 text-lg bg-gray-600 hover:bg-gray-500 border-gray-600 text-white" 
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
        {!loading && Object.keys(lexCounts).length > 0 && (
          <div className="space-y-4">
            <div className="text-sm text-gray-400">
              Found {filteredByMacro.length} results, showing {displayed.length}
            </div>
            
            {/* Frequency Filter Buttons */}
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
            
            {/* Macro Man-made / Natural Filter Buttons */}
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
                    {cleanedLex} ({cnt})
                  </Button>
                ))}
            </div>
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