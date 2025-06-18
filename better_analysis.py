import re

# Read missing words
with open('missing_words.txt', 'r') as f:
    words = [line.strip() for line in f]

# Let's manually check for common everyday objects that might be missing
# These are words most people would know and could guess in 20 questions

common_animals = ['badger', 'bat', 'beaver', 'bee', 'beetle', 'buffalo', 'bull', 'butterfly', 
                  'camel', 'canary', 'caribou', 'caterpillar', 'cheetah', 'chipmunk', 'cobra',
                  'deer', 'donkey', 'dove', 'dragonfly', 'eagle', 'falcon', 'firefly', 'fox',
                  'frog', 'giraffe', 'goat', 'goose', 'grasshopper', 'hawk', 'hedgehog', 'hippo',
                  'jay', 'kangaroo', 'lamb', 'leopard', 'lion', 'llama', 'lobster', 'moose',
                  'moth', 'owl', 'ox', 'panda', 'parrot', 'peacock', 'penguin', 'pig', 'pigeon',
                  'porcupine', 'rabbit', 'raccoon', 'ram', 'rat', 'raven', 'robin', 'seal',
                  'sheep', 'skunk', 'sloth', 'snail', 'sparrow', 'spider', 'squirrel', 'stork',
                  'swan', 'tiger', 'toad', 'turkey', 'turtle', 'vulture', 'walrus', 'wasp',
                  'weasel', 'whale', 'wolf', 'woodpecker', 'worm', 'zebra']

common_household = ['attic', 'basement', 'bathroom', 'bedroom', 'blanket', 'broom', 'bucket',
                    'candle', 'ceiling', 'chair', 'closet', 'couch', 'curtain', 'desk', 'door',
                    'drawer', 'dresser', 'fence', 'floor', 'garage', 'garden', 'gate', 'hammer',
                    'hinge', 'kitchen', 'ladder', 'lamp', 'mailbox', 'mirror', 'mop', 'nail',
                    'pillow', 'porch', 'rake', 'roof', 'rug', 'shelf', 'sink', 'sofa', 'stairs',
                    'stove', 'table', 'toilet', 'towel', 'vacuum', 'wall', 'window', 'yard']

common_food = ['bacon', 'bagel', 'banana', 'bean', 'beef', 'beet', 'berry', 'biscuit', 'bread',
               'broccoli', 'burger', 'butter', 'cabbage', 'cake', 'candy', 'carrot', 'celery',
               'cereal', 'cheese', 'cherry', 'chicken', 'chili', 'chocolate', 'coconut', 'cookie',
               'corn', 'crab', 'cream', 'cucumber', 'egg', 'fish', 'flour', 'fruit', 'garlic',
               'grape', 'ham', 'honey', 'ice', 'jam', 'juice', 'lemon', 'lettuce', 'lime',
               'lobster', 'meat', 'melon', 'milk', 'mushroom', 'noodle', 'nut', 'oat', 'oil',
               'onion', 'orange', 'pasta', 'peach', 'pear', 'pepper', 'pickle', 'pie', 'pizza',
               'pork', 'potato', 'rice', 'salad', 'salt', 'sandwich', 'sauce', 'soup', 'steak',
               'sugar', 'tea', 'tomato', 'turkey', 'vegetable', 'water', 'wine', 'yogurt']

common_objects = ['anchor', 'arrow', 'axe', 'badge', 'bag', 'ball', 'balloon', 'barrel',
                  'basket', 'bat', 'battery', 'bell', 'belt', 'bicycle', 'boat', 'bone',
                  'bottle', 'bow', 'box', 'brick', 'bridge', 'brush', 'button', 'camera',
                  'canoe', 'cap', 'card', 'chain', 'coin', 'comb', 'compass', 'crown',
                  'cup', 'diamond', 'dice', 'drum', 'envelope', 'eraser', 'fan', 'feather',
                  'flag', 'flower', 'fork', 'frame', 'gem', 'gift', 'glass', 'glove',
                  'gold', 'gun', 'hat', 'hook', 'horn', 'jar', 'jewel', 'key', 'kite',
                  'knife', 'knot', 'leaf', 'lens', 'lock', 'mask', 'medal', 'needle',
                  'net', 'oar', 'paddle', 'pan', 'paper', 'pen', 'pencil', 'pipe',
                  'plate', 'pot', 'puzzle', 'ring', 'rope', 'ruler', 'scissors', 'screw',
                  'shield', 'shoe', 'shovel', 'spear', 'spoon', 'stick', 'stone', 'string',
                  'sword', 'thread', 'tire', 'tool', 'toy', 'treasure', 'umbrella', 'vase',
                  'violin', 'wheel', 'whistle', 'wing', 'wire', 'wood']

# Combine all common word lists
all_common = common_animals + common_household + common_food + common_objects

# Find which common words are missing from the dataset
missing_common = [word for word in all_common if word in words]

print(f"Analysis of {len(words)} missing words:")
print(f"Common everyday words that SHOULD be in a 20 questions game but are missing:")
print(f"Found {len(missing_common)} obviously missing common words\n")

if missing_common:
    print("Missing Animals:")
    missing_animals = [w for w in missing_common if w in common_animals]
    if missing_animals:
        print(f"  {', '.join(missing_animals)}")
    else:
        print("  (None from our list)")
    
    print("\nMissing Household Items:")
    missing_household = [w for w in missing_common if w in common_household]
    if missing_household:
        print(f"  {', '.join(missing_household)}")
    else:
        print("  (None from our list)")
    
    print("\nMissing Food Items:")
    missing_food = [w for w in missing_common if w in common_food]
    if missing_food:
        print(f"  {', '.join(missing_food)}")
    else:
        print("  (None from our list)")
    
    print("\nMissing Common Objects:")
    missing_objects = [w for w in missing_common if w in common_objects]
    if missing_objects:
        print(f"  {', '.join(missing_objects)}")
    else:
        print("  (None from our list)")
else:
    print("Great! All the common words we checked are already in the dataset.")

# Let's also look for simple, short common words in the missing list
simple_words = [w for w in words if len(w) <= 6 and w.isalpha() and not w.endswith('ly') and not w.endswith('ed')]
print(f"\n\nSimple short words (6 letters or less) that are missing:")
print(f"Found {len(simple_words)} simple words")
if simple_words:
    print("First 30 simple missing words:")
    for i, word in enumerate(simple_words[:30]):
        print(f"  {word}", end=", " if (i+1) % 10 != 0 else "\n")
    if len(simple_words) > 30:
        print(f"\n  ... and {len(simple_words) - 30} more") 