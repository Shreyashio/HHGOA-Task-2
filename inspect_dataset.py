"""
Quick schema inspection using pyarrow + direct parquet URL.
Fetches only the first ~1MB of the parquet shard to get real example rows.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

# ── Confirmed schema from datasets-server API ──────────────────────────────
CONFIRMED_SCHEMA = {
    "source_lang":  "string",
    "target_lang":  "string",
    "meta": {
        "frequency_penalty": "int64",
        "max_tokens":        "int64",
        "model_name":        "string",
        "presence_penalty":  "int64",
        "temperature":       "int64",
        "top_p":             "int64",
    },
    "Answer":       "string",
    "query_id":     "int64",
    "query_type":   "string",
    "passages": {
        "English_passages":    "list[string]",
        "Translated_passages": "list[string]",
        "is_selected":         "list[int64]",
    },
    "Eng_Query":    "string",
    "Eng_Answer":   "string",
    "query":        "string",
}

SPLIT_SIZES = {
    "train":      {"num_examples": 10_080_140, "num_bytes_uncompressed": 129_888_900_480,
                   "download_size_compressed": 55_619_599_557},
    "validation": {"num_examples": 1_371_174,  "num_bytes_uncompressed": 16_749_366_641},
}

print("=" * 70)
print("  MSMARCO-XI  —  Confirmed Schema (datasets-server API)")
print("=" * 70)

print("\n── Top-level fields ──────────────────────────────────────────────────")
for k, v in CONFIRMED_SCHEMA.items():
    if isinstance(v, dict):
        print(f"  {k:20s} dict")
        for sk, sv in v.items():
            print(f"    {'':4s}{sk:22s} {sv}")
    else:
        print(f"  {k:20s} {v}")

print("\n── Split sizes ───────────────────────────────────────────────────────")
for split, info in SPLIT_SIZES.items():
    n = info["num_examples"]
    gb = info["num_bytes_uncompressed"] / 1e9
    print(f"  {split:12s}: {n:>10,} rows  (~{gb:.1f} GB uncompressed)")
dl = SPLIT_SIZES["train"]["download_size_compressed"] / 1e9
print(f"  {'total DL':12s}: ~{dl:.1f} GB compressed parquet")

print("\n── Real row sample (via datasets streaming, 1 row) ───────────────────")
try:
    from datasets import load_dataset as hf_load
    ds = hf_load("ai4bharat/MSMARCO-XI", split="train", streaming=True)
    for row in ds:
        print(f"  query_id   : {row['query_id']}")
        print(f"  target_lang: {row['target_lang']}")
        print(f"  query_type : {row['query_type']}")
        print(f"  Eng_Query  : {(row.get('Eng_Query') or '')[:90]}")
        print(f"  query      : {(row.get('query') or '')[:90]}")
        print(f"  Eng_Answer : {(row.get('Eng_Answer') or '')[:120]}")

        passages = row.get("passages", {})
        eng_p = passages.get("English_passages") or []
        sel   = passages.get("is_selected") or []
        trans = passages.get("Translated_passages") or []
        print(f"\n  # English passages  : {len(eng_p)}")
        print(f"  # Translated passages: {len(trans)}")
        print(f"  is_selected         : {sel}")

        if eng_p:
            word_counts = [len(p.split()) for p in eng_p if p]
            print(f"\n  Passage word counts : min={min(word_counts)} "
                  f"max={max(word_counts)} avg={sum(word_counts)//len(word_counts)}")
            print(f"\n  passage[0] ({len(eng_p[0].split())} words):")
            print(f"    {eng_p[0][:200]}")
            if len(eng_p) > 1:
                print(f"\n  passage[1] ({len(eng_p[1].split())} words):")
                print(f"    {eng_p[1][:200]}")

        meta = row.get("meta") or {}
        print(f"\n  meta.model_name: {meta.get('model_name', 'N/A')}")
        print(f"  meta.temperature: {meta.get('temperature', 'N/A')}")
        break  # only first row

except Exception as e:
    print(f"  [streaming error: {e}]")
    print("  (Schema already confirmed above from API — streaming optional for inspection)")

print("\n" + "=" * 70)
print("  Inspection complete.")
print("=" * 70)
