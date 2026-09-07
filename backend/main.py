"""
main.py
-------
FastAPI backend for the BIS Intelligence Assistant.

Run (from backend/):
    uvicorn main:app --reload --port 8000
"""

import uuid
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rag.retriever import retrieve, group_sources
from rag.prompt import SYSTEM_PROMPT, build_user_prompt
from rag.llm_client import generate_answer, LLM_API_KEY
from rag.embeddings import get_collection

app = FastAPI(title="BIS Intelligence Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # hackathon prototype - tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation store: {conversation_id: [{"role": "user"/"assistant", "text": "..."}]}
# Deliberately simple - a prototype-scale, session-only memory as scoped in the brief.
CONVERSATIONS: dict[str, list[dict]] = {}
MAX_HISTORY_TURNS = 6


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    evidence: list[dict]
    conversation_id: str
    demo_mode: bool


@app.get("/api/health")
def health():
    try:
        collection = get_collection()
        chunk_count = collection.count()
        chroma_ok = True
    except Exception as e:
        chunk_count = 0
        chroma_ok = False
        print(f"[health] ChromaDB check failed: {e}")

    return {
        "status": "ok" if chroma_ok else "degraded",
        "chroma_connected": chroma_ok,
        "chunks_indexed": chunk_count,
        "llm_api_key_configured": bool(LLM_API_KEY),
    }


def _build_retrieval_query(message: str, history: list[dict]) -> str:
    """
    Very simple conversation-context handling: if there's prior turns,
    prepend the last user message so a short follow-up like "LED bulbs"
    still retrieves in the context of "LED lighting products".
    """
    if not history:
        return message
    last_user_turns = [t["text"] for t in history if t["role"] == "user"]
    if not last_user_turns:
        return message
    return f"{last_user_turns[-1]} {message}"


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    conversation_id = req.conversation_id or str(uuid.uuid4())

    if not message:
        return ChatResponse(
            answer="Please enter a question about BIS standards, certification, testing, or laboratories.",
            sources=[], evidence=[], conversation_id=conversation_id, demo_mode=True,
        )

    history = CONVERSATIONS.setdefault(conversation_id, [])

    try:
        retrieval_query = _build_retrieval_query(message, history)
        evidence_chunks = retrieve(retrieval_query, top_k=5)
    except Exception as e:
        print(f"[chat] Retrieval failed: {e}")
        return ChatResponse(
            answer="The knowledge base is currently unavailable. Please try again shortly.",
            sources=[], evidence=[], conversation_id=conversation_id, demo_mode=True,
        )

    conversation_context = "\n".join(
        f"{t['role']}: {t['text']}" for t in history[-MAX_HISTORY_TURNS:]
    )
    user_prompt = build_user_prompt(message, evidence_chunks, conversation_context)

    answer, demo_mode = generate_answer(SYSTEM_PROMPT, user_prompt, evidence_chunks, message)

    history.append({"role": "user", "text": message})
    history.append({"role": "assistant", "text": answer})
    CONVERSATIONS[conversation_id] = history[-(MAX_HISTORY_TURNS * 2):]

    sources = group_sources(evidence_chunks)
    evidence = [
        {"text": c["text"][:500], "title": c["metadata"].get("title"), "page": c["metadata"].get("page")}
        for c in evidence_chunks
    ]

    return ChatResponse(
        answer=answer,
        sources=sources,
        evidence=evidence,
        conversation_id=conversation_id,
        demo_mode=demo_mode,
    )
