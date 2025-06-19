import json
import re
import sys
from pathlib import Path

# File path to the JSONL dataset
FILE_PATH = Path('/Users/ryanodonnell/Desktop/20questions/data/combined_twentyquestions.jsonl')

VOWELS = set('aeiouAEIOU')

def second_vowel_position(word: str) -> int:
    """Return the 1-indexed position of the 2nd vowel in `word`. If <2 vowels, return -1."""
    count = 0
    for idx, ch in enumerate(word, 1):  # 1-indexed
        if ch in VOWELS:
            count += 1
            if count == 2:
                return idx
    return -1  # Less than 2 vowels


def find_furthest_second_vowel(file_path: Path):
    max_pos = -1
    max_word = ''
    unique_subjects = set()

    with file_path.open('r', encoding='utf-8') as fh:
        for line_num, line in enumerate(fh, 1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed line
                continue

            subject = obj.get('subject', '').strip()
            if not subject or subject in unique_subjects:
                continue
            unique_subjects.add(subject)

            # Iterate through each individual word (letters only) within the subject
            for word in re.findall(r"[A-Za-z]+", subject):
                pos = second_vowel_position(word)
                if pos > max_pos:
                    max_pos = pos
                    max_word = word  # store the specific word, not the entire phrase

    return max_pos, max_word, len(unique_subjects)


def main():
    max_pos, max_word, total = find_furthest_second_vowel(FILE_PATH)
    print(f"Total unique nouns analyzed: {total}")
    if max_pos == -1:
        print("No word contains two vowels.")
        sys.exit(0)
    print(f"Furthest 2nd-vowel position: {max_pos}")
    print(f"Word with furthest 2nd vowel: '{max_word}'")

if __name__ == '__main__':
    main() 