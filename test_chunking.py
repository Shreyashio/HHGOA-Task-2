"""
test_chunking.py
─────────────────
Fast smoke-test for all three chunking strategies.
No HuggingFace download needed — uses synthetic Documents.

Run: python test_chunking.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from ingestion.loader import Document
from ingestion.chunking import (
    FixedSizeChunker, SentenceChunker, MetadataAwareChunker,
    get_chunker, available_strategies, Chunk,
)

# ── Synthetic test documents ───────────────────────────────────────────────────
SHORT_DOC = Document(
    id="test_001_0",
    text="Photosynthesis is the process by which plants convert light into energy. "
         "It occurs in the chloroplasts of plant cells. "
         "Carbon dioxide and water are converted to glucose and oxygen.",
    lang="en",
    query_id=1,
    query="What is photosynthesis?",
    eng_query="What is photosynthesis?",
    query_type="DESCRIPTION",
    is_selected=1,
    passage_idx=0,
)

LONG_DOC = Document(
    id="test_002_0",
    text=" ".join([
        "The mitochondria is known as the powerhouse of the cell.",
        "It generates most of the cell's supply of adenosine triphosphate (ATP), used as a source of chemical energy.",
        "A mitochondrion is a double-membrane-bound organelle found in most eukaryotic organisms.",
        "The name comes from the Greek words mitos (thread) and khondrion (granule).",
        "Mitochondria generate ATP via the process of oxidative phosphorylation.",
        "This process uses oxygen and simple sugars to create ATP.",
        "The outer membrane surrounds the organelle and contains proteins called porins.",
        "The inner membrane is folded into cristae, which increase the surface area.",
        "The matrix is the space enclosed by the inner membrane.",
        "It contains the mitochondrial DNA, ribosomes, and enzymes needed for the citric acid cycle.",
    ] * 3),  # repeat to make it long enough to trigger multi-chunk
    lang="en",
    query_id=2,
    query="What is a mitochondria?",
    eng_query="What is a mitochondria?",
    query_type="DESCRIPTION",
    is_selected=0,
    passage_idx=2,
)

MULTILANG_DOC = Document(
    id="test_003_0",
    text="The Taj Mahal is an ivory-white marble mausoleum on the right bank of the river Yamuna. "
         "It was commissioned in 1632 by the Mughal emperor Shah Jahan.",
    lang="hi",
    query_id=3,
    query="ताज महल क्या है?",
    eng_query="What is the Taj Mahal?",
    query_type="LOCATION",
    is_selected=1,
    passage_idx=0,
)

PASS  = "\033[92mPASS\033[0m"
FAIL  = "\033[91mFAIL\033[0m"


def check(condition: bool, label: str) -> bool:
    icon = PASS if condition else FAIL
    print(f"  [{icon}] {label}")
    return condition


def test_strategy(name: str, chunker, doc: Document, label: str) -> int:
    """Test one chunker on one doc. Returns number of failures."""
    chunks = chunker.chunk(doc)
    failures = 0

    ok = check(len(chunks) > 0, f"{label}: produces at least 1 chunk")
    failures += (0 if ok else 1)

    ok = check(all(isinstance(c, Chunk) for c in chunks),
               f"{label}: all outputs are Chunk instances")
    failures += (0 if ok else 1)

    ok = check(all(c.text.strip() for c in chunks),
               f"{label}: no empty chunk texts")
    failures += (0 if ok else 1)

    ok = check(all(c.strategy == name for c in chunks),
               f"{label}: strategy tag = '{name}'")
    failures += (0 if ok else 1)

    ok = check(all("lang" in c.metadata for c in chunks),
               f"{label}: metadata contains 'lang'")
    failures += (0 if ok else 1)

    ok = check(all("query_type" in c.metadata for c in chunks),
               f"{label}: metadata contains 'query_type'")
    failures += (0 if ok else 1)

    ok = check(len(set(c.chunk_id for c in chunks)) == len(chunks),
               f"{label}: chunk IDs are unique")
    failures += (0 if ok else 1)

    # Print chunk stats
    for i, c in enumerate(chunks):
        print(f"    chunk[{i}]: {c.token_count} tokens | "
              f"{c.word_count} words | id={c.chunk_id[:8]}...")
    return failures


def test_factory():
    """Test get_chunker factory."""
    failures = 0
    for strat in ["fixed", "sentence", "metadata"]:
        c = get_chunker(strat)
        ok = check(hasattr(c, "chunk"), f"factory: get_chunker('{strat}') has .chunk()")
        failures += (0 if ok else 1)

    try:
        get_chunker("nonexistent")
        ok = False
    except ValueError:
        ok = True
    failures += (0 if check(ok, "factory: raises ValueError for unknown strategy") else 1)
    return failures


def test_chroma_format():
    """Test to_chroma() returns valid Chroma-compatible types."""
    chunker = SentenceChunker()
    chunks = chunker.chunk(SHORT_DOC)
    failures = 0
    for c in chunks:
        cid, text, meta = c.to_chroma()
        ok = check(isinstance(cid, str), f"to_chroma: id is str")
        failures += (0 if ok else 1)
        ok = check(isinstance(text, str) and len(text) > 0, "to_chroma: text is non-empty str")
        failures += (0 if ok else 1)
        ok = check(
            all(isinstance(v, (str, int, float, bool)) for v in meta.values()),
            "to_chroma: metadata values are Chroma-compatible types"
        )
        failures += (0 if ok else 1)
    return failures


def main():
    total_failures = 0

    print("\n" + "="*60)
    print("  Chunking Strategy Unit Tests")
    print("="*60)

    print("\n[1] FixedSizeChunker — short doc")
    fc = FixedSizeChunker(chunk_size=128, overlap=16)
    total_failures += test_strategy("fixed", fc, SHORT_DOC, "fixed/short")

    print("\n[2] FixedSizeChunker — long doc (should produce multiple chunks)")
    total_failures += test_strategy("fixed", fc, LONG_DOC, "fixed/long")
    chunks = fc.chunk(LONG_DOC)
    ok = check(len(chunks) > 1, f"fixed/long: multi-chunk for long doc (got {len(chunks)})")
    total_failures += (0 if ok else 1)

    print("\n[3] SentenceChunker — short doc")
    sc = SentenceChunker(max_tokens=128, sentence_overlap=1)
    total_failures += test_strategy("sentence", sc, SHORT_DOC, "sentence/short")

    print("\n[4] SentenceChunker — long doc")
    total_failures += test_strategy("sentence", sc, LONG_DOC, "sentence/long")
    chunks = sc.chunk(LONG_DOC)
    ok = check(len(chunks) > 1, f"sentence/long: multi-chunk for long doc (got {len(chunks)})")
    total_failures += (0 if ok else 1)

    print("\n[5] MetadataAwareChunker — multilingual doc")
    mc = MetadataAwareChunker(max_tokens=128)
    total_failures += test_strategy("metadata", mc, MULTILANG_DOC, "metadata/multilang")
    chunks = mc.chunk(MULTILANG_DOC)
    if chunks:
        ok = check("[LANG: hi]" in chunks[0].text or "LANG" in chunks[0].text,
                   "metadata: header contains [LANG: hi]")
        total_failures += (0 if ok else 1)
        ok = check("[TYPE: LOCATION]" in chunks[0].text or "TYPE" in chunks[0].text,
                   "metadata: header contains [TYPE: LOCATION]")
        total_failures += (0 if ok else 1)
        ok = check("[Q:" in chunks[0].text or "Q:" in chunks[0].text,
                   "metadata: header contains [Q: ...]")
        total_failures += (0 if ok else 1)
        print(f"    Header injected: {chunks[0].text[:120]!r}")

    print("\n[6] Factory & Chroma format")
    total_failures += test_factory()
    total_failures += test_chroma_format()

    print("\n[7] available_strategies()")
    strats = available_strategies()
    ok = check(set(strats) == {"fixed", "sentence", "metadata"},
               f"available_strategies() returns all 3 (got {strats})")
    total_failures += (0 if ok else 1)

    print("\n" + "="*60)
    if total_failures == 0:
        print(f"  {PASS}  All tests passed!")
    else:
        print(f"  {FAIL}  {total_failures} test(s) failed.")
    print("="*60 + "\n")
    return total_failures


if __name__ == "__main__":
    sys.exit(main())
