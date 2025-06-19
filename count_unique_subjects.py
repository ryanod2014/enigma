import json, sys
subjects=set()
with open('data/enhanced_twentyquestions.jsonl') as f:
  for line in f:
    try:
      e=json.loads(line)
    except: continue
    if 'source' in e:
      subjects.add(e['subject'].lower())
print(len(subjects)) 