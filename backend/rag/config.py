"""
config.py
---------
Central configuration for the RAG pipeline. Everything here can be
overridden with environment variables (via a .env file), so you never
need to edit code to tune chunk sizes, swap the embedding model, or
change where data lives.

This file is imported by BOTH ingestion.py (to build the knowledge
base) and retriever.py (to query it), so the two always stay in sync
on chunk size, collection name, and embedding model.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# backend/  (this file lives at backend/rag/config.py)
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Where you drop raw BIS documents (PDF / TXT / JSON) to be ingested.
DOCS_DIR = Path(os.getenv("BIS_DOCS_DIR", BACKEND_DIR / "data" / "bis_documents"))

# Where ChromaDB persists its vector index to disk.
CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", BACKEND_DIR / "chroma_db"))

# Small JSON file used to skip re-embedding files that haven't changed
# since the last ingestion run. Safe to delete if you want a full rebuild.
INGESTION_CACHE_FILE = DOCS_DIR / ".ingestion_cache.json"

# Optional manifest where you can attach/override metadata (title, source,
# url, category) for any file by filename. See data/bis_documents/README.md.
METADATA_MANIFEST_FILE = DOCS_DIR / "metadata.json"

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

# Chunk size and overlap are measured in WORDS (simple, dependency-free,
# and good enough for a RAG prototype). ~220 words ≈ 900-1100 characters,
# a reasonable amount of context per chunk for standards/compliance text.
CHUNK_SIZE_WORDS = int(os.getenv("CHUNK_SIZE_WORDS", "220"))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", "40"))

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

# A small, fast, fully local sentence-transformers model. No API key
# needed, so ingestion and retrieval keep working even if the LLM
# provider's API is down (aligns with the project's "demo mode" goal).
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "bis_documents")

# ---------------------------------------------------------------------------
# Supported input file types for ingestion
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".json"}

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

# How many chunks to retrieve per question.
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# Chroma returns a distance (lower = more similar) for each result, not a
# 0-1 similarity score. This is the cutoff used to decide "not enough
# evidence" — tune it if retrieval feels too strict/loose for your data.
MAX_RELEVANT_DISTANCE = float(os.getenv("MAX_RELEVANT_DISTANCE", "1.1"))

# ---------------------------------------------------------------------------
# LLM provider
# ---------------------------------------------------------------------------

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # "anthropic" | "openai" | "demo"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")
