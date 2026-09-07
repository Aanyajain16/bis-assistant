"""
ingestion.py
------------
Automatic ingestion pipeline for the BIS knowledge base.

Drop PDF / TXT / JSON files into:
    backend/data/bis_documents/

Then run:
    python -m rag.ingestion

For each file this pipeline will:
    1. Detect the file type (.pdf / .txt / .json)
    2. Extract text (page-by-page for PDFs)
    3. Clean the text
    4. Split it into overlapping chunks
    5. Embed each chunk
    6. Store the chunk + embedding + metadata in ChromaDB

Metadata stored per chunk:
    - filename          e.g. "is_302_household_appliances.pdf"
    - title             human-readable document title
    - source            e.g. "Bureau of Indian Standards"
    - url               link to the original document, if available
    - category          e.g. "Product Standard", "Certification", "Testing"
    - page              page number (PDF) or "N/A"
    - chunk_index       position of this chunk within the document

RE-RUNNING IS SAFE:
    A small cache file (.ingestion_cache.json) tracks a content hash per
    file. Unchanged files are skipped. If a file changed (or is new),
    its old chunks (if any) are deleted and it is re-ingested fresh.

NO FAKE DATA:
    This script does not generate or invent any BIS content. It only
    processes whatever real files you place in backend/data/bis_documents/.
    If that folder is empty, ingestion simply reports "0 files found".
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from rag import config
from rag.embeddings import get_collection


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def compute_file_hash(path: Path) -> str:
    """Content hash used to detect whether a file changed since last ingestion."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_cache() -> dict:
    if config.INGESTION_CACHE_FILE.exists():
        try:
            return json.loads(config.INGESTION_CACHE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"[warn] Could not read cache file, starting fresh: {config.INGESTION_CACHE_FILE}")
    return {}


def save_cache(cache: dict) -> None:
    config.INGESTION_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def load_metadata_manifest() -> dict:
    """
    Loads the optional metadata.json manifest, which lets you attach
    title/source/url/category to files by filename. See
    backend/data/bis_documents/README.md for the format.
    """
    if config.METADATA_MANIFEST_FILE.exists():
        try:
            return json.loads(config.METADATA_MANIFEST_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"[warn] metadata.json is malformed and will be ignored: {e}")
    return {}


def clean_text(text: str) -> str:
    """Basic whitespace/control-character cleanup. Keeps punctuation intact."""
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)   # drop spaces hugging line breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size_words: int, overlap_words: int) -> list[str]:
    """
    Splits text into overlapping chunks measured in words. Word-based
    chunking is simple, dependency-free, and avoids cutting sentences
    as harshly as fixed character windows.
    """
    words = text.split()
    if not words:
        return []

    if overlap_words >= chunk_size_words:
        overlap_words = max(0, chunk_size_words // 4)  # guard against bad config

    chunks = []
    start = 0
    step = chunk_size_words - overlap_words
    while start < len(words):
        chunk_words = words[start:start + chunk_size_words]
        chunk = " ".join(chunk_words).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size_words >= len(words):
            break
        start += step
    return chunks


def resolve_metadata(filename: str, manifest: dict, override: dict | None = None) -> dict:
    """
    Builds the final metadata dict for a file, in priority order:
        1. Per-record override (e.g. a JSON file that specifies its own title)
        2. Entry in metadata.json manifest, keyed by filename
        3. Sensible defaults derived from the filename
    """
    manifest_entry = manifest.get(filename, {})
    override = override or {}

    def pick(key: str, default: str) -> str:
        return override.get(key) or manifest_entry.get(key) or default

    default_title = Path(filename).stem.replace("_", " ").replace("-", " ").strip().title()

    meta = {
        "filename": filename,
        "title": pick("title", default_title),
        "source": pick("source", "Unknown source - please update metadata.json"),
        "url": pick("url", "N/A"),
        "category": pick("category", "Uncategorized"),
    }

    if meta["source"].startswith("Unknown source"):
        print(f"  [notice] No metadata entry for '{filename}'. "
              f"Add one to {config.METADATA_MANIFEST_FILE.name} for accurate sourcing.")

    return meta


# ---------------------------------------------------------------------------
# File type extractors
# Each returns a list of (page_label, text, metadata_override) tuples.
# page_label is a string (e.g. "3") or "N/A" when pages don't apply.
# metadata_override is None unless the source format carries its own metadata.
# ---------------------------------------------------------------------------

def extract_pdf(path: Path) -> list[tuple[str, str, dict | None]]:
    results = []
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        print(f"  [error] Could not open PDF '{path.name}': {e}")
        return results

    if reader.is_encrypted:
        print(f"  [error] '{path.name}' is password-protected. Skipping.")
        return results

    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"  [warn] Could not extract text from page {i} of '{path.name}': {e}")
            text = ""
        text = clean_text(text)
        if text:
            results.append((str(i), text, None))

    if not results:
        print(f"  [warn] No extractable text found in '{path.name}' "
              f"(it may be a scanned/image-only PDF and would need OCR).")

    return results


def extract_txt(path: Path) -> list[tuple[str, str, dict | None]]:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        print(f"  [error] Could not read TXT '{path.name}': {e}")
        return []
    text = clean_text(raw)
    if not text:
        print(f"  [warn] '{path.name}' appears to be empty.")
        return []
    return [("N/A", text, None)]


def extract_json(path: Path) -> list[tuple[str, str, dict | None]]:
    """
    Supports three flexible JSON shapes so real BIS data can be dropped
    in with minimal reformatting:

    1) Single document:
       {
         "title": "...", "source": "...", "url": "...", "category": "...",
         "content": "full text here"
       }

    2) List of documents (same shape as above, repeated):
       [ {...}, {...} ]

    3) Single document split into pages:
       {
         "title": "...", "source": "...", "url": "...", "category": "...",
         "pages": [ {"page": 1, "text": "..."}, {"page": 2, "text": "..."} ]
       }
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [error] Could not parse JSON '{path.name}': {e}")
        return []

    results: list[tuple[str, str, dict | None]] = []

    def handle_record(record: dict):
        override = {k: record[k] for k in ("title", "source", "url", "category") if k in record}

        if "pages" in record and isinstance(record["pages"], list):
            for page_entry in record["pages"]:
                page_num = str(page_entry.get("page", "N/A"))
                text = clean_text(str(page_entry.get("text", "")))
                if text:
                    results.append((page_num, text, override or None))
        elif "content" in record:
            text = clean_text(str(record["content"]))
            if text:
                results.append(("N/A", text, override or None))
        else:
            print(f"  [warn] JSON record in '{path.name}' has neither 'content' nor 'pages'. Skipping record.")

    if isinstance(data, list):
        for record in data:
            if isinstance(record, dict):
                handle_record(record)
    elif isinstance(data, dict):
        handle_record(data)
    else:
        print(f"  [error] '{path.name}' must contain a JSON object or list of objects.")

    if not results:
        print(f"  [warn] No usable text found in '{path.name}'.")

    return results


EXTRACTORS = {
    ".pdf": extract_pdf,
    ".txt": extract_txt,
    ".json": extract_json,
}


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------

def delete_existing_chunks(collection, filename: str) -> None:
    """Removes previously stored chunks for a file before re-ingesting it."""
    try:
        collection.delete(where={"filename": filename})
    except Exception as e:
        print(f"  [warn] Could not clear old chunks for '{filename}': {e}")


def ingest_file(path: Path, collection, manifest: dict) -> int:
    """Ingests a single file. Returns the number of chunks stored."""
    ext = path.suffix.lower()
    extractor = EXTRACTORS.get(ext)
    if extractor is None:
        print(f"  [skip] Unsupported file type: '{path.name}'")
        return 0

    page_units = extractor(path)
    if not page_units:
        return 0

    filename = path.name
    delete_existing_chunks(collection, filename)

    ids, documents, metadatas = [], [], []
    chunk_counter = 0

    for page_label, page_text, meta_override in page_units:
        meta = resolve_metadata(filename, manifest, meta_override)
        chunks = chunk_text(page_text, config.CHUNK_SIZE_WORDS, config.CHUNK_OVERLAP_WORDS)

        for chunk in chunks:
            chunk_id = f"{filename}::p{page_label}::c{chunk_counter}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "filename": filename,
                "title": meta["title"],
                "source": meta["source"],
                "url": meta["url"],
                "category": meta["category"],
                "page": page_label,
                "chunk_index": chunk_counter,
            })
            chunk_counter += 1

    if not ids:
        print(f"  [warn] '{filename}' produced no chunks after cleaning/chunking.")
        return 0

    # Chroma has a practical batch size limit on some backends; batch to be safe.
    BATCH = 100
    for i in range(0, len(ids), BATCH):
        collection.add(
            ids=ids[i:i + BATCH],
            documents=documents[i:i + BATCH],
            metadatas=metadatas[i:i + BATCH],
        )

    return len(ids)


def ingest_all(force: bool = False) -> None:
    """
    Walks backend/data/bis_documents/, ingests every new/changed
    supported file, and prints a summary. Pass force=True to re-ingest
    everything regardless of the cache.
    """
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)

    IGNORED_FILENAMES = {config.METADATA_MANIFEST_FILE.name, "metadata.example.json", "README.md"}

    all_files = [
        p for p in sorted(config.DOCS_DIR.rglob("*"))
        if p.is_file()
        and p.suffix.lower() in config.SUPPORTED_EXTENSIONS
        and p.name not in IGNORED_FILENAMES
    ]

    if not all_files:
        print(f"No documents found in {config.DOCS_DIR}")
        print("Add real BIS PDF / TXT / JSON files there, then re-run this script.")
        return

    print(f"Found {len(all_files)} file(s) in {config.DOCS_DIR}\n")

    manifest = load_metadata_manifest()
    cache = load_cache()
    collection = get_collection()

    total_chunks = 0
    ingested_count = 0
    skipped_count = 0

    for path in all_files:
        file_hash = compute_file_hash(path)
        cache_key = str(path.relative_to(config.DOCS_DIR))

        if not force and cache.get(cache_key) == file_hash:
            print(f"[skip - unchanged] {path.name}")
            skipped_count += 1
            continue

        print(f"[ingesting] {path.name}")
        n_chunks = ingest_file(path, collection, manifest)
        print(f"  -> stored {n_chunks} chunk(s)\n")

        cache[cache_key] = file_hash
        total_chunks += n_chunks
        ingested_count += 1

    save_cache(cache)

    print("=" * 60)
    print("Ingestion complete.")
    print(f"  Files processed : {ingested_count}")
    print(f"  Files unchanged : {skipped_count}")
    print(f"  Chunks stored   : {total_chunks}")
    print(f"  Collection size : {collection.count()} total chunks")
    print(f"  Chroma storage  : {config.CHROMA_PERSIST_DIR}")
    print("=" * 60)


def main():
    force = "--force" in sys.argv
    if force:
        print("Force mode: re-ingesting all files regardless of cache.\n")
    ingest_all(force=force)


if __name__ == "__main__":
    main()
