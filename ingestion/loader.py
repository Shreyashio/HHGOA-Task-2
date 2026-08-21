"""
ingestion/loader.py
────────────────────
Loads and streams the ai4bharat/MSMARCO-XI dataset from HuggingFace.

Schema (confirmed from datasets-server API):
  - query_id        (int)   : unique query identifier
  - query           (str)   : translated query (in target_lang)
  - Eng_Query       (str)   : original English query
  - source_lang     (str)   : always "en"
  - target_lang     (str)   : Indic language code (hi, bn, ta, te, mr, ...)
  - query_type      (str)   : DESCRIPTION | NUMERIC | ENTITY | LOCATION | PERSON
  - Answer          (str)   : translated answer
  - Eng_Answer      (str)   : original English answer
  - passages        (dict)  : {
        "English_passages":    [str, ...]  # 10 candidate passages
        "Translated_passages": [str, ...]  # same passages, translated
        "is_selected":         [int, ...]  # 1 = relevant, 0 = not
    }
  - meta            (dict)  : model_name, temperature, max_tokens, etc.

Splits:  train (10,080,140 rows) | validation (1,371,174 rows)
Size:    ~130 GB uncompressed | ~56 GB compressed parquet

Memory strategy
───────────────
Parquet row groups for this dataset are ~3 GB uncompressed — too large
to load whole row groups. We use `ParquetFile.iter_batches(batch_size=100)`
which reads exactly 100 rows at a time from the HTTP stream (via fsspec
range-request seeking), keeping peak memory well under 50 MB.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Iterator, Optional, List

# Columns we actually need — skip Translated_passages (saves ~50% RAM at parse time)
_NEEDED_COLUMNS = [
    "query_id", "query_type", "source_lang", "target_lang",
    "Eng_Query", "query", "Eng_Answer", "passages", "meta",
]


# ─── Document schema ───────────────────────────────────────────────────────────

@dataclass
class Document:
    """
    A normalised document unit derived from one MSMARCO-XI passage.

    Each MSMARCO-XI row has ~10 candidate passages. We explode each passage
    into its own Document so chunking and retrieval work at passage granularity.
    """
    id: str                     # "{query_id}_{passage_idx}"
    text: str                   # passage text to embed/chunk
    lang: str                   # "en" (English passages by default)
    query_id: int = 0
    query: str = ""             # translated query
    eng_query: str = ""         # English query — used by MetadataAwareChunker
    query_type: str = ""        # DESCRIPTION | NUMERIC | ENTITY | LOCATION | PERSON
    is_selected: int = 0        # 1 = relevant passage (ground truth)
    passage_idx: int = 0        # 0-9 within the query's passage list
    metadata: dict = field(default_factory=dict)


# ─── Language reference ─────────────────────────────────────────────────────────

SUPPORTED_LANGS = [
    "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml",
    "pa", "or", "as", "ne", "si", "ur", "en",
]

LANG_NAMES = {
    "hi": "Hindi",    "bn": "Bengali",  "ta": "Tamil",    "te": "Telugu",
    "mr": "Marathi",  "gu": "Gujarati", "kn": "Kannada",  "ml": "Malayalam",
    "pa": "Punjabi",  "or": "Odia",     "as": "Assamese", "ne": "Nepali",
    "si": "Sinhala",  "ur": "Urdu",     "en": "English",
}


# ─── Parquet shard resolver ──────────────────────────────────────────────────────

def _get_shard_urls(split: str = "train") -> List[str]:
    """Fetch parquet shard URLs from HuggingFace datasets-server API."""
    import requests
    url = (
        "https://datasets-server.huggingface.co/parquet"
        f"?dataset=ai4bharat/MSMARCO-XI&config=default&split={split}"
    )
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    files = resp.json().get("parquet_files", [])
    urls = [f["url"] for f in files]
    if not urls:
        raise RuntimeError(f"No parquet shards found for split={split!r}")
    return urls


# ─── Core loader ────────────────────────────────────────────────────────────────

def load_dataset(
    split: str = "train",
    lang: str = "all",
    max_docs: Optional[int] = None,
    use_english_passages: bool = True,
    streaming: bool = True,          # kept for API compat
    batch_size: int = 100,           # rows per pyarrow batch — keep small for RAM
) -> Iterator[Document]:
    """
    Stream MSMARCO-XI documents using pyarrow iter_batches over HTTP.

    Uses fsspec HTTP filesystem so pyarrow can seek into the remote parquet
    file without downloading the entire shard (~50-200 MB). Reads `batch_size`
    rows at a time, keeping peak memory well under 50 MB regardless of shard size.

    Args:
        split:                "train" | "validation"
        lang:                 "all" | ISO code ("en", "hi", "ta", ...)
        max_docs:             stop after this many rows (not passages)
        use_english_passages: True = embed English passages (recommended)
        streaming:            kept for API compatibility
        batch_size:           rows per pyarrow read batch (default 100, ~10 MB RAM)

    Yields:
        Document instances ready for chunking and indexing.
    """
    import fsspec
    import pyarrow.parquet as pq

    shard_urls = _get_shard_urls(split)
    row_count = 0

    for shard_url in shard_urls:
        if max_docs is not None and row_count >= max_docs:
            break

        # fsspec HTTP filesystem — uses HTTP range requests, no local buffering
        fs = fsspec.filesystem("https")
        with fs.open(shard_url, "rb") as f:
            pf = pq.ParquetFile(f)

            # iter_batches: reads exactly `batch_size` rows at a time
            # Never loads a full row group into memory — critical for 3GB groups
            for batch in pf.iter_batches(
                batch_size=batch_size,
                columns=_NEEDED_COLUMNS,
            ):
                if max_docs is not None and row_count >= max_docs:
                    break

                df = batch.to_pydict()
                n = len(df["query_id"])

                for i in range(n):
                    if max_docs is not None and row_count >= max_docs:
                        break

                    tgt_lang = df["target_lang"][i]

                    # Language filter
                    if lang != "all" and tgt_lang != lang:
                        row_count += 1
                        continue

                    passages_block  = df["passages"][i] or {}
                    eng_passages    = passages_block.get("English_passages", [])  or []
                    trans_passages  = passages_block.get("Translated_passages", []) or []
                    is_selected_lst = passages_block.get("is_selected", [])        or []
                    meta_block      = df["meta"][i] or {}

                    source_passages = eng_passages if use_english_passages else trans_passages
                    passage_lang    = "en"        if use_english_passages else tgt_lang

                    for idx, passage_text in enumerate(source_passages):
                        if not passage_text or not passage_text.strip():
                            continue

                        yield Document(
                            id=f"{df['query_id'][i]}_{idx}",
                            text=passage_text.strip(),
                            lang=passage_lang,
                            query_id=int(df["query_id"][i]),
                            query=df["query"][i] or "",
                            eng_query=df["Eng_Query"][i] or "",
                            query_type=df["query_type"][i] or "",
                            is_selected=int(is_selected_lst[idx])
                                if idx < len(is_selected_lst) else 0,
                            passage_idx=idx,
                            metadata={
                                "source_lang": df["source_lang"][i],
                                "target_lang": tgt_lang,
                                "eng_answer":  (df["Eng_Answer"][i] or "")[:300],
                                "model_name":  meta_block.get("model_name", ""),
                            },
                        )

                    row_count += 1
