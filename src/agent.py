from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        results = self.store.search(question, top_k=top_k)
        if not results:
            prompt = (
                "You are a helpful assistant.\n\n"
                f"Question: {question}\n\n"
                "No relevant context was retrieved from the knowledge base. "
                "Answer briefly and say that the knowledge base did not contain enough information."
            )
            return self.llm_fn(prompt)

        context_blocks = []
        for index, result in enumerate(results, start=1):
            context_blocks.append(f"[Context {index}] {result['content']}")

        prompt = (
            "You are a helpful RAG assistant. Use the provided context to answer the question carefully.\n\n"
            f"Question: {question}\n\n"
            "Context:\n"
            + "\n\n".join(context_blocks)
            + "\n\nAnswer in a concise, factual way."
        )

        return self.llm_fn(prompt)
