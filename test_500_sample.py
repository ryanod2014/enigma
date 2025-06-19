import random
from wordnet_vowel_index import WordIndex, vowel_positions, CATEGORY_MAP, classify_subject

# Build index
print("Building index...")
idx = WordIndex()

# Get all words from our dataset
all_words = []
for key_list in idx.index.values():
    all_words.extend([item['word'] for item in key_list])

print(f"Total words in dataset: {len(all_words)}")

# Sample 500 random words
random.seed(42)  # for reproducible results
test_words = random.sample(all_words, min(500, len(all_words)))

print(f'Testing {len(test_words)} random words from dataset...')

# Test each word's classification
results = {}
for word in test_words:
    vpos = vowel_positions(word)
    if not vpos: 
        continue
    
    first_v = vpos[0]
    second_v = vpos[1] if len(vpos) > 1 else 0
    first_letter = word[0].upper()
    
    # Find category
    cat = None
    for c, letters in CATEGORY_MAP.items():
        if first_letter in letters:
            cat = c
            break
    
    if cat:
        items = idx.query_category(len(word), cat, first_v, second_v)
        for item in items:
            if item['word'] == word:
                results[word] = {
                    'cat': item.get('cat', 'unknown'),
                    'manmade': item.get('manmade', None)
                }
                break

print('\nSample classifications (first 30):')
for i, (word, data) in enumerate(list(results.items())[:30]):
    print(f'{word}: {data["cat"]}, manmade={data["manmade"]}')

# Count categories
cat_counts = {}
manmade_counts = {'True': 0, 'False': 0, 'None': 0}

for data in results.values():
    cat = data['cat']
    cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    mm = data['manmade']
    if mm is True:
        manmade_counts['True'] += 1
    elif mm is False:
        manmade_counts['False'] += 1
    else:
        manmade_counts['None'] += 1

print('\nCategory distribution in 500-word sample:')
for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
    pct = (count / len(results)) * 100
    print(f'{cat}: {count} ({pct:.1f}%)')

print('\nManmade distribution:')
for status, count in manmade_counts.items():
    pct = (count / len(results)) * 100
    print(f'{status}: {count} ({pct:.1f}%)')

print(f'\nClassification metrics:')
print(f'Unknown rate: {cat_counts.get("unknown", 0) / len(results) * 100:.1f}%')
print(f'Classification success rate: {(len(results) - cat_counts.get("unknown", 0)) / len(results) * 100:.1f}%')

# Test some edge cases to check for obvious errors
print('\nTesting some edge cases for sanity check:')
edge_cases = ['computer', 'calculator', 'teacher', 'apple', 'tiger', 'chair', 'bicycle', 'hammer']
for word in edge_cases:
    if word in results:
        data = results[word]
        print(f'{word}: {data["cat"]}, manmade={data["manmade"]}')
    else:
        # Test via classify_subject directly
        cat, mm = classify_subject(word)
        print(f'{word}: {cat}, manmade={mm} (via fallback)')

print('\nTest complete!') 