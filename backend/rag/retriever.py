"""
retriever.py
------------
Given a user query, embeds it and searches the ChromaDB collection
built by ingestion.py for the most relevant chunks.

This is intentionally the ONLY place that talks to the vector store
for reads, mirroring ingestion.py being the only place that writes to it.
"""

from rag import config
from rag.embeddings import get_collection


def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    """
    Returns a list of dicts, each:
        {
            "id": chunk id,
            "text": chunk text,
            "metadata": {filename, title, source, url, category, page, chunk_index},
            "distance": float (lower = more similar)
        }
    Only chunks within MAX_RELEVANT_DISTANCE are returned. If the
    collection is empty or nothing is relevant, returns [].
    """
    query = (query or "").strip()
    if not query:
        return []

    collection = get_collection()
    if collection.count() == 0:
        return []

    k = top_k or config.RETRIEVAL_TOP_K
    n_results = min(k, collection.count())
    results = collection.query(query_texts=[query], n_results=n_results)

    chunks = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, text, meta, distance in zip(ids, documents, metadatas, distances):
        if distance <= config.MAX_RELEVANT_DISTANCE:
            chunks.append({
                "id": chunk_id,
                "text": text,
                "metadata": meta,
                "distance": distance,
            })

    return chunks


def build_search_query(question: str, recent_history: list[str] | None = None) -> str:
    """
    Folds the last user turn into the search text so short follow-ups
    still retrieve the right documents, e.g.:
        "I manufacture LED lighting products." -> "LED bulbs."
    becomes the search text "I manufacture LED lighting products. LED bulbs."
    Kept deliberately simple - no summarization, just the last turn or two.
    """
    if not recent_history:
        return question
    return f"{' '.join(recent_history[-2:])} {question}".strip()


def group_sources(chunks: list[dict]) -> list[dict]:
    """
    Collapses retrieved chunks into unique source citations (one card
    per document+page) for display, since multiple chunks can come
    from the same page.
    """
    seen = {}
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("filename"), meta.get("page"))
        if key not in seen:
            seen[key] = {
                "title": meta.get("title"),
                "source": meta.get("source"),
                "page": meta.get("page"),
                "url": meta.get("url"),
                "category": meta.get("category"),
                "filename": meta.get("filename"),
            }
    return list(seen.values())
