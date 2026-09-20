from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        sentence_parts = re.split(r"(?<=[.!?])\s+|\n+", normalized)
        sentences = [part.strip() for part in sentence_parts if part and part.strip()]
        if not sentences:
            return [normalized]

        chunks: list[str] = []
        current: list[str] = []

        for sentence in sentences:
            current.append(sentence)
            if len(current) >= self.max_sentences_per_chunk:
                chunks.append(" ".join(current).strip())
                current = []

        if current:
            chunks.append(" ".join(current).strip())

        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = max(1, chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        normalized = text.strip()
        if not normalized:
            return []
        if len(normalized) <= self.chunk_size:
            return [normalized]

        return self._split(normalized, list(self.separators))

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text.strip()]

        if not remaining_separators:
            chunks: list[str] = []
            for start in range(0, len(current_text), self.chunk_size):
                piece = current_text[start : start + self.chunk_size].strip()
                if piece:
                    chunks.append(piece)
            return chunks

        separator = remaining_separators[0]
        if separator == "":
            return self._split(current_text, remaining_separators[1:])

        if separator not in current_text:
            return self._split(current_text, remaining_separators[1:])

        parts = [part.strip() for part in current_text.split(separator) if part.strip()]
        if len(parts) <= 1:
            return self._split(current_text, remaining_separators[1:])

        merged: list[str] = []
        buffer = ""

        for part in parts:
            candidate = f"{buffer}{separator}{part}" if buffer else part
            if len(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                if buffer:
                    merged.append(buffer)
                if len(part) <= self.chunk_size:
                    buffer = part
                else:
                    merged.extend(self._split(part, remaining_separators[1:]))
                    buffer = ""

        if buffer:
            merged.append(buffer)

        return merged


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    if not vec_a or not vec_b:
        return 0.0

    length = min(len(vec_a), len(vec_b))
    dot_product = sum(vec_a[i] * vec_b[i] for i in range(length))
    norm_a = math.sqrt(sum(value * value for value in vec_a))
    norm_b = math.sqrt(sum(value * value for value in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        chunk_size = max(1, chunk_size)
        fixed = FixedSizeChunker(chunk_size=chunk_size, overlap=max(0, chunk_size // 10)).chunk(text)
        by_sentences = SentenceChunker(max_sentences_per_chunk=3).chunk(text)
        recursive = RecursiveChunker(chunk_size=chunk_size).chunk(text)

        def stats(chunks: list[str]) -> dict:
            if not chunks:
                return {"count": 0, "avg_length": 0.0, "chunks": chunks}
            avg_length = sum(len(chunk) for chunk in chunks) / len(chunks)
            return {"count": len(chunks), "avg_length": avg_length, "chunks": chunks}

        return {
            "fixed_size": stats(fixed),
            "by_sentences": stats(by_sentences),
            "recursive": stats(recursive),
        }
