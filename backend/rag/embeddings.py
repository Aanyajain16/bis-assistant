"""
embeddings.py
-------------
Wraps the embedding model and the ChromaDB client so that ingestion.py
and retriever.py always use the exact same embedding function and
collection. If you ever want to swap the embedding model (e.g. to an
API-based one), this is the ONLY file you need to change.
"""

import chromadb
from chromadb.utils import embedding_functions

from rag import config


def get_embedding_function():
    """
    Returns a local, offline sentence-transformers embedding function.
    Using a local model (instead of an API) means the knowledge base can
    still be built and searched even if the LLM API key/provider is
    unavailable — only answer *generation* needs the LLM API.
    """
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL_NAME
    )


def get_chroma_client():
    """Returns a persistent ChromaDB client backed by disk storage."""
    config.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))


def get_collection():
    """
    Returns the shared BIS documents collection, creating it if it
    doesn't exist yet. Both ingestion and retrieval call this so they
    are always looking at the same data with the same embedding space.
    """
    client = get_chroma_client()
    embedding_fn = get_embedding_function()
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={"description": "BIS standards, certification, testing, and lab documents"},
    )
