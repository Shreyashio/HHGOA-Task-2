"""
Quick loader smoke test: load 50 rows, print stats.
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

from ingestion.loader import load_dataset

print("Loading 50 rows from MSMARCO-XI train split...")
t0 = time.perf_counter()
docs = list(load_dataset(split="train", lang="all", max_docs=50))
elapsed = time.perf_counter() - t0

print(f"\nLoaded {len(docs)} documents (passages) from 50 rows in {elapsed:.1f}s")
if docs:
    d = docs[0]
    print(f"\nFirst doc:")
    print(f"  id           : {d.id}")
    print(f"  lang         : {d.lang}")
    print(f"  query_type   : {d.query_type}")
    print(f"  is_selected  : {d.is_selected}")
    print(f"  eng_query    : {d.eng_query[:80]}")
    print(f"  text (100c)  : {d.text[:100]}")
    print(f"  words        : {len(d.text.split())}")

    selected = sum(1 for d in docs if d.is_selected == 1)
    avg_words = sum(len(d.text.split()) for d in docs) / len(docs)
    print(f"\nStats across {len(docs)} passages:")
    print(f"  is_selected=1 : {selected}")
    print(f"  avg word count: {avg_words:.0f}")
    print(f"  min words     : {min(len(d.text.split()) for d in docs)}")
    print(f"  max words     : {max(len(d.text.split()) for d in docs)}")
