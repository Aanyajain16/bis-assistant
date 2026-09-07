"""
prompt.py
---------
Builds the system prompt and the evidence-grounded user prompt sent to
the LLM. Keeping this separate from main.py makes the prompt easy to
tune without touching API/routing logic.
"""

SYSTEM_PROMPT = """You are a BIS Standards and Compliance Assistant.

Answer questions using ONLY the retrieved BIS evidence provided to you below.

Do not invent or assume BIS standard numbers, certification requirements, testing requirements, laboratory information, dates, fees, or regulatory requirements that are not explicitly present in the evidence.

If the retrieved evidence is insufficient to answer confidently, clearly state that the available BIS knowledge base does not contain enough information, rather than guessing.

When answering:
1. Directly answer the user's question.
2. Explain the relevant BIS information in simple language.
3. Mention the relevant standard/certification/testing information only when it is supported by the evidence below.
4. Distinguish between what is explicitly stated in the evidence and any general clarifying explanation you add.
5. Do not fabricate sources. Only refer to the evidence given to you.

Never present unsupported information as fact."""


def build_user_prompt(question: str, evidence_chunks: list[dict], conversation_context: str = "") -> str:
    """
    Assembles the evidence + question into the message sent to the LLM.
    Each evidence chunk is numbered so the model can reference it plainly.
    """
    if not evidence_chunks:
        evidence_block = "(No relevant evidence was found in the BIS knowledge base for this question.)"
    else:
        parts = []
        for i, chunk in enumerate(evidence_chunks, start=1):
            meta = chunk["metadata"]
            page_info = f", page {meta.get('page')}" if meta.get("page") not in (None, "N/A") else ""
            parts.append(
                f"[Evidence {i}] Source: {meta.get('title')} ({meta.get('source')}{page_info})\n"
                f"{chunk['text']}"
            )
        evidence_block = "\n\n".join(parts)

    context_block = f"Conversation so far:\n{conversation_context}\n\n" if conversation_context else ""

    return (
        f"{context_block}"
        f"Retrieved BIS evidence:\n{evidence_block}\n\n"
        f"User question: {question}\n\n"
        f"Answer using only the evidence above. If it's insufficient, say so plainly."
    )
