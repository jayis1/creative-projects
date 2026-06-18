"""Example: MinHash + LSH for near-duplicate document detection.

Demonstrates using MinHash signatures and an LSH index to efficiently
find near-duplicate documents among a large collection, without O(n²)
pairwise comparisons.
"""
import sys
import os
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pds import MinHash, LSHIndex

# Generate a collection of "documents" (sets of words)
random.seed(42)
base_words = ["the", "quick", "brown", "fox", "jumps", "over", "lazy",
              "dog", "runs", "fast", "slow", "big", "small", "red", "blue",
              "green", "sky", "land", "sea", "mountain", "river", "forest",
              "tree", "rock", "cloud", "wind", "rain", "sun", "moon", "star",
              "road", "city", "village", "bridge", "tower", "castle", "field",
              "valley", "hill", "lake", "ocean", "desert", "island", "coast",
              "harbor", "ship", "horse", "bird", "fish", "snake", "bear",
              "wolf", "eagle", "hawk", "owl", "deer", "rabbit", "mouse",
              "cat", "lion", "tiger", "elephant", "whale", "shark", "spider"]

documents = {}
for i in range(1000):
    # Each document is a random subset of 10-20 words
    n = random.randint(10, 20)
    words = set(random.sample(base_words, n))
    documents[f"doc-{i}"] = words

# Add some near-duplicates: copy a doc and change 1-2 words
for i in range(0, 100, 10):
    orig = documents[f"doc-{i}"]
    modified = set(orig)
    modified.discard(random.choice(list(orig)))
    modified.add("EXTRA_WORD")
    documents[f"doc-{i}-dup"] = modified

print(f"Document collection: {len(documents)} documents")

# Build MinHash signatures and LSH index
NUM_PERM = 128
NUM_BANDS = 32
idx = LSHIndex(num_perm=NUM_PERM, num_bands=NUM_BANDS, seed=0)
signatures = {}

for doc_id, words in documents.items():
    mh = MinHash(num_perm=NUM_PERM, seed=0)
    for word in words:
        mh.add(word)
    signatures[doc_id] = mh
    idx.add(doc_id, mh)

print(f"LSH index: {NUM_PERM} perms, {NUM_BANDS} bands, "
      f"threshold ≈ {idx.threshold:.3f}")

# Query for near-duplicates of doc-0
query_id = "doc-0"
candidates = idx.query(signatures[query_id], exclude=query_id)
print(f"\nNear-duplicates of {query_id}:")
print(f"  Candidates from LSH: {len(candidates)}")

# Verify with actual Jaccard
verified = []
for cand_id in candidates:
    j = signatures[query_id].jaccard(signatures[cand_id])
    if j > 0.5:
        verified.append((cand_id, j))

verified.sort(key=lambda x: -x[1])
for doc_id, j in verified[:10]:
    print(f"  {doc_id}: Jaccard ≈ {j:.3f}")

# Find the known duplicate
if "doc-0-dup" in documents:
    j = signatures["doc-0"].jaccard(signatures["doc-0-dup"])
    print(f"\n  Known duplicate 'doc-0-dup': Jaccard ≈ {j:.3f}")

print(f"\nLSH reduced comparisons from {len(documents)-1} to {len(candidates)} "
      f"({len(candidates)/(len(documents)-1)*100:.1f}% of brute-force)")