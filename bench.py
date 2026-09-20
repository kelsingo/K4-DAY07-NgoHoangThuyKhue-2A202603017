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
        "id": 1,
        "kind": "hỏi điều kiện",
        "query": "Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%.",
        "gold_phrase": "Đổi mới miễn phí 100% nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất",
        "expect_doc_id": "hoanghamobile-warranty-buyer",
    },
    {
        "id": 2,
        "kind": "tra số liệu",
        "query": "Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành.",
        "gold_phrase": "02 ngày làm việc kể từ khi mã yêu cầu ghi nhận",
        "expect_doc_id": "tiki-seller-warranty-faq",
    },
    {
        "id": 3,
        "kind": "hỏi quy trình",
        "query": "Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào?",
        "metadata_filter": {"audience": "seller"},
        # Gold lấy từ FAQ mục 6 (dòng 54), KHÔNG phải mục 4 (dòng 40).
        # Hai mục dễ lẫn nhưng khác điều kiện kích hoạt và khác hậu quả:
        #   mục 4 = Nhà Bán không XÁC NHẬN PHƯƠNG ÁN trong 02 ngày -> Tiki chủ động xử lý
        #   mục 6 = Nhà Bán KHÔNG PHẢN HỒI               -> Tiki hoàn tiền, cấn trừ kỳ sau
        # Câu hỏi dùng chữ "không phản hồi" nên gold phải là mục 6.
        # (Bản gốc của R2 ghép cả vế "bồi thường" từ dòng 36/82 — điều khoản bảo
        #  hành quá hạn, khác ngữ cảnh hẳn — nên đã bỏ.)
        "gold": "Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm trong trường hợp Nhà Bán không "
                "hoặc không thể thu hồi hàng hóa; số tiền hoàn trả được cấn trừ vào kỳ thanh toán tiếp theo của Nhà Bán.",
        "gold_phrase": "Tiki sẽ hoàn tiền cho Khách Hàng và không chịu trách nhiệm",
        "expect_doc_id": "tiki-seller-warranty-faq",
    },
    {
        "id": 4,
        "kind": "liệt kê",
        # Thay câu "Nhà Bán xác nhận ... qua đâu trong hệ thống?": câu đó trùng
        # chủ đề với câu 2 và 3 (đều là seller + xác nhận yêu cầu đổi trả), và
        # bộ 5 câu đang thiếu hẳn dạng liệt kê.
        "query": "Sản phẩm cần thỏa những điều kiện nào để được bảo hành miễn phí?",
        "metadata_filter": {"audience": "buyer"},
        "gold": "Lỗi kỹ thuật do nhà sản xuất; còn trong thời hạn bảo hành; có hóa đơn điện tử hoặc mã đơn hàng; "
                "với hàng điện gia dụng thì phiếu/tem bảo hành và tem niêm phong còn nguyên vẹn.",
        "gold_phrase": "Sản phẩm được bảo hành miễn phí nếu sản phẩm đó hội đủ các điều kiện sau",
        "expect_doc_id": "shopee-warranty-buyer",
    },
    {
        "id": 5,
        "kind": "câu cần lọc metadata",
        # Câu hỏi KHÔNG nêu người hỏi là ai, trong khi cả hai phía corpus đều nói
        # về thời hạn bảo hành bằng cùng từ vựng nhưng cho đáp án khác nhau:
        #   buyer  -> 12 tháng máy mới (Hoàng Hà) / 20-45 ngày làm việc (Shopee)
        #   seller -> Nhà Bán cam kết tối đa không quá 30 ngày
        # Không lọc thì top-3 lẫn cả hai và agent trả lời sai đối tượng.
        # Thay câu "Theo quy trình đổi mới của Hoàng Hà Mobile...": câu đó nêu
        # đích danh Hoàng Hà nên embedding tự tách được, filter thành thừa.
        "query": "Thời gian bảo hành tối đa là bao lâu?",
        "metadata_filter": {"audience": "seller"},
        "gold": "Nhà Bán cam kết thời gian bảo hành tối đa không quá 30 ngày, tính từ khi Nhà Bán nhận được hàng "
                "đến khi bảo hành xong, không tính thời gian vận chuyển.",
        "gold_phrase": "tối đa không quá 30 ngày",
        "expect_doc_id": "tiki-seller-warranty-faq",
        # Chạy hai lần (có lọc / không lọc) để lấy bằng chứng cho mục 3 REPORT_NHOM.
        "demo_filter_effect": True,
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