# BIS Intelligence Assistant (SIH26107 Prototype)

An AI-powered assistant for Indian Standards & BIS services (standards,
certification, testing, laboratories), built on Retrieval-Augmented
Generation (RAG) so answers are grounded in real BIS documents instead
of the LLM's own (possibly hallucinated) knowledge.

## 1. Problem being solved

Users (manufacturers, consumers, students) need to navigate BIS
standards, certification schemes, and testing/lab requirements, but
this information is scattered across many documents. A naive
LLM-only chatbot risks inventing standard numbers, fees, or
requirements. This prototype instead retrieves real evidence first,
and only answers from that evidence — clearly saying "not enough
information" when it can't find support.

## 2. Architecture

```
┌─────────────┐     1. question      ┌──────────────┐
│   React UI  │ ───────────────────► │   FastAPI    │
│  (frontend) │ ◄─────────────────── │  /api/chat   │
└─────────────┘   4. answer+sources  └──────┬───────┘
                                              │
                                   2. embed + search
                                              ▼
                                     ┌─────────────────┐
                                     │    ChromaDB      │
                                     │ (vector store)   │
                                     └────────┬─────────┘
                                              │ top-k chunks
                                              ▼
                                   3. evidence + question
                                              ▼
                                     ┌─────────────────┐
                                     │   LLM API        │
                                     │ (or demo mode)    │
                                     └─────────────────┘
```

**Ingestion (offline, run once / whenever documents change):**
```
BIS PDFs/TXT/JSON → text extraction → cleaning → chunking
                  → embeddings → stored in ChromaDB with metadata
```

## 3. How RAG works in this project

1. User asks a question.
2. The question (plus a bit of recent conversation context) is embedded
   and used to semantically search ChromaDB for the most relevant chunks.
3. If nothing relevant is found, the assistant says so — it never
   fabricates an answer.
4. If relevant chunks are found, they're inserted into a strict system
   prompt ("answer ONLY from this evidence") along with the question,
   and sent to the LLM.
5. The answer is returned to the frontend along with the source
   documents and the raw evidence chunks used, shown in an
   "🔎 Evidence Used" panel so judges can see the grounding.

## 4. Folder structure

```
bis-assistant/
  backend/
    main.py                 FastAPI app: /api/chat, /api/health
    requirements.txt
    .env.example
    rag/
      config.py              chunking/embedding/paths config
      embeddings.py           embedding function + ChromaDB client
      ingestion.py            document ingestion pipeline
      retriever.py            semantic search over ChromaDB
      prompt.py               system prompt + prompt building
      llm_client.py           LLM API wrapper (swappable + demo fallback)
    data/
      bis_documents/          <- put real BIS PDFs/TXT/JSON here
        README.md
        metadata.example.json
    chroma_db/                 created automatically on first ingestion
  frontend/
    src/
      App.jsx
      api.js
      index.css
      components/
        Chat.jsx
        Message.jsx
        SourceCard.jsx
        QuickActions.jsx
    package.json
    vite.config.js
    index.html
```

## 5. Installation

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

**Frontend:**
```bash
cd frontend
npm install
```

## 6. Environment variables (backend/.env)

| Variable | Purpose | Default |
|---|---|---|
| `LLM_API_KEY` | Your LLM provider's API key | (empty → demo mode) |
| `LLM_PROVIDER` | `anthropic` or `demo` | `anthropic` |
| `LLM_MODEL` | Model name | `claude-sonnet-4-6` |
| `BIS_DOCS_DIR` | Folder to ingest documents from | `data/bis_documents` |
| `CHROMA_PERSIST_DIR` | Where the vector index is stored | `chroma_db` |
| `CHUNK_SIZE_WORDS` | Words per chunk | `220` |
| `CHUNK_OVERLAP_WORDS` | Overlap between chunks | `40` |

If `LLM_API_KEY` is missing or the API call fails, the backend
automatically falls back to a clearly-labeled **DEMO MODE** that
builds an answer directly from retrieved evidence text, so the app
still demos end-to-end without a live LLM connection.

## 7. How to add BIS documents

1. Copy real `.pdf` / `.txt` / `.json` files into `backend/data/bis_documents/`.
2. (Recommended) Create `backend/data/bis_documents/metadata.json`
   (see `metadata.example.json`) to attach accurate title/source/URL/
   category to each file — otherwise these are marked "Unknown source"
   rather than guessed.
3. See `backend/data/bis_documents/README.md` for the full JSON schema
   options and formatting notes.

**No sample/fake BIS documents are included in this prototype** — the
knowledge base starts empty and is meant to be populated with real
BIS material.

## 8. How to ingest documents

```bash
cd backend
python -m rag.ingestion            # ingest new/changed files
python -m rag.ingestion --force    # force full re-ingestion
```

## 9. How to start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```
Check it's up: `curl http://localhost:8000/api/health`

## 10. How to start the frontend

```bash
cd frontend
npm run dev
```
Open the printed local URL (typically `http://localhost:5173`).

## 11. How to test the RAG

- `GET /api/health` → shows `chunks_indexed` count and whether an LLM
  key is configured.
- Ask a question covered by your ingested documents → should return
  an answer with source cards and an Evidence Used panel.
- Ask something unrelated to your documents → should honestly say
  the knowledge base doesn't have enough information.

## 12. Example questions

- "I manufacture LED lighting products. What BIS standards and
  certification requirements may apply?"
- "What is the process to get BIS certification for a product?"
- "Which BIS-recognized laboratories can test my product?"

## 13. Demo flow for judges

1. Show `backend/data/bis_documents/` populated with real BIS files.
2. Run `python -m rag.ingestion` live — show chunk counts being stored.
3. Open the UI, click the example question or a quick-action button.
4. Point out: the answer, the Source cards (with real document titles/
   pages), and the expandable "🔎 Evidence Used" section showing the
   exact retrieved text the answer is grounded in.
5. Ask a follow-up like "LED bulbs" after a broader question, to show
   basic conversation memory feeding retrieval.
6. Ask something outside the knowledge base to show it says "not
   enough evidence" instead of guessing.
7. (Optional) Unset `LLM_API_KEY` and restart to show DEMO MODE still
   produces a grounded, evidence-based response.

## 14. Limitations

- Session-only conversation memory (no long-term memory).
- Word-based chunking (not token-aware) — fine for a prototype.
- Scanned/image-only PDFs are not OCR'd; they're skipped with a warning.
- Relevance threshold and top-k are simple heuristics, not tuned on a
  real evaluation set.
- No authentication — not intended for production deployment.

## 15. Future improvements

- OCR support for scanned BIS documents.
- Hybrid retrieval (keyword + semantic) for exact standard-number lookups.
- Streaming responses in the UI.
- Admin view for managing ingested documents and metadata.
- Long-term user memory across sessions.
