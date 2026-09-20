#!/usr/bin/env python3
"""Benchmark retrieval on a small warranty/corporate-policy corpus.

This script reads Markdown files with YAML front matter, splits the body into
semantically meaningful sections, materializes each section as a Document, and
runs a fixed benchmark of 5 queries through EmbeddingStore.search_with_filter().

The design intentionally keeps the chunking strategy in a single place, so each
team member can swap only one line to test their own approach.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from src.chunking import RecursiveChunker
from src.embeddings import _mock_embed
from src.models import Document
from src.store import EmbeddingStore

DEFAULT_DATA_DIR = Path("data/warranty")
DEFAULT_OUTPUT = Path("ket_qua_benchmark.txt")

BENCHMARK_QUERIES = [
    {
        "query": "Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%.",
    },
    {
        "query": "Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành.",
    },
    {
        "query": "Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Tiki sẽ chủ động xử lý theo yêu cầu Khách Hàng và được quyền từ chối tiếp nhận các khiếu nại của Nhà Bán; nếu không có lý do hợp lệ, Tiki có thể bồi thường cho Khách Hàng.",
    },
    {
        "query": "Nhà Bán xác nhận phương án xử lý yêu cầu đổi trả qua đâu trong hệ thống?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán xác nhận phương án xử lý qua hệ thống Seller Center, vào mục Đơn hàng > Đổi trả bảo hành, tab Cần Nhà Bán phản hồi.",
    },
    {
        "query": "Theo quy trình đổi mới của Hoàng Hà Mobile, khách hàng cần làm gì trước khi nhận sản phẩm mới?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Khách hàng mang sản phẩm đến cửa hàng, nhân viên tiếp nhận và thẩm định lỗi ngay tại chỗ; nếu lỗi do nhà sản xuất và đủ điều kiện thì tiến hành đổi sản phẩm mới.",
    },
]


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a Markdown file into front matter and body.

    Front matter is delimited by leading --- ... --- at the top of the file.
    """
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text

    lines = stripped.splitlines()
    if len(lines) < 3:
        return {}, text

    end_index = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_index = i
            break

    if end_index is None:
        return {}, text

    metadata: dict[str, str] = {}
    for raw in lines[1:end_index]:
        if not raw.strip() or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')

    body = "\n".join(lines[end_index + 1 :])
    return metadata, body


def split_sections(text: str) -> list[str]:
    """Split Markdown by heading boundaries; keep heading with each section."""
    if not text.strip():
        return []

    lines = text.splitlines()
    sections: list[str] = []
    current_heading = ""
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_lines
        if not current_lines and not current_heading:
            return
        section = current_heading.strip() + "\n\n" + "\n".join(current_lines).strip()
        if section.strip():
            sections.append(section.strip())
        current_heading = ""
        current_lines = []

    for line in lines:
        if line.startswith("#"):
            if current_heading or current_lines:
                flush()
            current_heading = line.strip()
        else:
            current_lines.append(line.rstrip())

    flush()
    return sections or [text.strip()]


def split_long_section(heading: str, content: str, chunk_size: int = 650) -> list[str]:
    """Split a section into smaller chunks while preserving the heading context."""
    cleaned = content.strip()
    if not cleaned:
        return []

    if len(cleaned) <= chunk_size:
        if heading:
            return [f"{heading}\n\n{cleaned}".strip()]
        return [cleaned]

    chunks = RecursiveChunker(chunk_size=chunk_size).chunk(cleaned)
    if not heading:
        return chunks

    prefixed = [f"{heading}\n\n{chunk}".strip() for chunk in chunks if chunk.strip()]
    return prefixed


def section_chunks_for_document(text: str, chunk_size: int = 650) -> list[str]:
    """Create chunk list from a markdown body, preserving section headings."""
    sections = split_sections(text)
    chunks: list[str] = []
    for section in sections:
        if not section.strip():
            continue
        lines = section.splitlines()
        heading = lines[0].strip() if lines and lines[0].startswith("#") else ""
        body = "\n".join(lines[1:]) if heading else section
        if heading and len((heading + "\n\n" + body).strip()) <= chunk_size:
            chunks.append((heading + "\n\n" + body).strip())
        else:
            chunks.extend(split_long_section(heading, body, chunk_size=chunk_size))
    return chunks or [text.strip()]


def markdown_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in data_dir.glob("**/*.md") if p.is_file())


def build_documents(data_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in markdown_files(data_dir):
        text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        chunks = section_chunks_for_document(body or text)

        for index, chunk in enumerate(chunks):
            metadata = dict(frontmatter)
            metadata["doc_id"] = frontmatter.get("doc_id") or path.stem
            metadata["source_file"] = str(path)
            metadata["document_path"] = str(path)
            metadata["chunk_index"] = str(index)
            docs.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    metadata=metadata,
                )
            )
    return docs


def run_benchmark(data_dir: Path, output_path: Path) -> None:
    documents = build_documents(data_dir)
    store = EmbeddingStore(collection_name="benchmark_store", embedding_fn=_mock_embed)
    store.add_documents(documents)

    lines: list[str] = []
    lines.append(f"Loaded {len(documents)} chunks from {len(markdown_files(data_dir))} markdown files.")
    lines.append("")

    for item in BENCHMARK_QUERIES:
        query = item["query"]
        metadata_filter = item.get("metadata_filter")
        results = store.search_with_filter(query, top_k=3, metadata_filter=metadata_filter)
        lines.append(f"QUERY: {query}")
        lines.append(f"FILTER: {metadata_filter}")
        for rank, result in enumerate(results, start=1):
            score = result.get("score")
            doc_id = result.get("metadata", {}).get("doc_id")
            chunk_id = result.get("id")
            snippet = re.sub(r"\s+", " ", result.get("content", "")[:180]).strip()
            lines.append(f"  {rank}. score={score:.6f} doc_id={doc_id} chunk_id={chunk_id}")
            lines.append(f"     snippet: {snippet}")
        lines.append(f"GOLD: {item['gold']}")
        lines.append("")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the benchmark suite for the warranty corpus.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Folder containing markdown documents.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="File to write benchmark output to.")
    args = parser.parse_args()

    if not args.data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {args.data_dir}")

    run_benchmark(args.data_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
