# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Ngô Hoàng Thụy Khuê
**Nhóm:** Finding Vinno
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Khi hai vector điểm cùng hướng trong không gian nhiều chiều, tức là chúng biểu diễn cùng một khái niệm hoặc cùng chủ đề, độ tương tự cosine sẽ cao. Về mặt ngôn ngữ, hai câu có cùng chủ đề hoặc cùng hành động sẽ có xu hướng gần nhau hơn.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Con mèo đang ngồi bên cạnh cửa sổ."
- Câu B: "Con mèo đang ngồi trên bậu cửa sổ."
- Tại sao tương đồng: Cả hai mô tả cùng một sự kiện về mèo ngồi trên cửa sổ, dù có một vài từ khác nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Tôi thích ăn phở."
- Câu B: "Bầu trời có màu xanh."
- Tại sao khác: Chủ đề gần như hoàn toàn khác nhau, không cùng hành động, không cùng đối tượng và không cùng bối cảnh.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine mô tả hướng của vector, nên nó tập trung vào ý nghĩa tương đồng hơn là độ lớn tuyệt đối của vector. Trong embedding văn bản, độ dài và cách biểu diễn có thể khác nhau nhưng ý nghĩa có thể tương tự, vì vậy cosine phù hợp hơn để đo sự liên quan ngữ nghĩa.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Bước tính: step = chunk_size - overlap = 500 - 50 = 450. Số chunk ≈ ceil((10000 - 50) / 450) = ceil(9950 / 450) = ceil(22.11) = 23 chunks.
> **Đáp án:** 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Với overlap = 100, step = 500 - 100 = 400. Số chunk ≈ ceil((10000 - 100) / 400) = ceil(9900 / 400) = ceil(24.75) = 25 chunks. Khi overlap tăng, step giảm nên số lượng chunk tăng lên; độ chồng chéo nhiều hơn giúp duy trì ngữ cảnh giữa các chunk và giảm mất thông tin ở biên.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi sử dụng `re.split` để chia văn bản theo dấu câu kết thúc như `.`, `!`, `?` kèm theo khoảng trắng hoặc xuống dòng, rồi gom các câu lại theo `max_sentences_per_chunk`. Nếu văn bản có khoảng trắng thừa hoặc dòng mới, tôi chuẩn hóa bằng cách `strip()` và `re.sub(r"\s+", " ", text)` để tránh lỗi cấu trúc và chunk rỗng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán ưu tiên tách theo các separator theo thứ tự ưu tiên như đoạn văn (`\n\n`), dòng mới (`\n`), dấu chấm câu (`. `), dấu cách (` `), cuối cùng là trường hợp fallback bằng cách cắt theo `chunk_size`. Base case là khi độ dài hiện tại nhỏ hơn hoặc bằng `chunk_size`, hoặc khi không còn separator để tách; lúc đó sẽ trả về chunk cuối cùng hoặc chia theo kích thước tối đa.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi document được chuyển thành một record chứa `id`, `content`, `metadata` và `embedding` tính từ `embedding_fn` để lưu trong bộ nhớ. Khi truy vấn, tôi nhúng query bằng cùng hàm embedding, tính độ tương tự bằng tích vô hướng (dot product) giữa query vector và từng vector đã lưu, rồi sắp xếp giảm dần theo `score`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Tôi áp dụng lọc metadata trước khi tính độ tương tự để giảm không gian tìm kiếm và tránh nhầm tài liệu không thuộc phạm vi câu hỏi. Với xóa tài liệu, tôi loại bỏ tất cả các record có `metadata['doc_id'] == doc_id` hoặc `id == doc_id`, trả về `True` nếu đã xóa ít nhất một chunk.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `answer()` đầu tiên gọi `store.search(question, top_k)` để lấy các chunk liên quan nhất. Sau đó, tôi xây dựng prompt theo mẫu: `Question` + `Context` + yêu cầu trả lời theo dữ kiện được cung cấp, chèn từng chunk vào phần context dưới dạng `[Context n] ...` để model dựa vào bằng chứng thực tế hơn và giảm hiện tượng “đoán mò”.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```bash
===================================== test session starts ======================================
platform darwin -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0 -- /opt/miniconda3/bin/python
cachedir: .pytest_cache
rootdir: /Users/mal/Documents/Vin/K4-L3B-2A202603017-NgoHoangThuyKhue-Data-Foundations
plugins: anyio-4.12.1, asyncio-1.4.0, langsmith-0.13.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 42 items                                                                             

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED    [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED             [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED      [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED       [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED            [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED  [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED   [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED                   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED   [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED              [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED          [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED                    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED                   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED     [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED       [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED             [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED  [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED    [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED     [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED              [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED             [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED        [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED    [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED   [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED         [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED   [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

====================================== 42 passed in 0.03s ======================================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | The cat sat on the mat. | The cat is sitting on the rug. | cao | thấp | Sai |
| 2 | I love pizza. | The sky is blue today. | thấp | thấp | Đúng |
| 3 | Python is a programming language. | Python is used for software development. | cao | thấp | Sai |
| 4 | Marketing teams plan campaigns. | A cat sleeps on a warm couch. | thấp | thấp | Đúng |
| 5 | Embedding models convert text into vectors. | Vector databases store embeddings for retrieval. | cao | cao | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 1 và 3 là những cặp rất dễ đoán là có liên quan nhưng trong mock embeddings thực tế lại không cho điểm cao. Điều này cho thấy cách embeddings biểu diễn ý nghĩa phụ thuộc rất lớn vào model và cách dữ liệu được mã hóa; nếu model không học được ngữ nghĩa thực sự thì sự tương đồng sẽ không phản ánh đúng “ý nghĩa” tự nhiên theo cảm nhận của con người.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân trong gói `src`. Bộ câu hỏi này khớp với bộ câu hỏi chung của nhóm và được chọn trực tiếp từ chính corpus `data/warranty`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | Chính sách "Lỗi Đổi Liền" quy định đổi mới miễn phí trong 15 hoặc 30 ngày đầu, tùy dòng sản phẩm, nếu lỗi phần cứng do nhà sản xuất. | 0.267602 | Có | Khách hàng được đổi mới miễn phí trong 15 hoặc 30 ngày đầu nếu xác nhận lỗi phần cứng do nhà sản xuất. |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | Mô hình Dropship/SD nhấn mạnh đơn hàng cần Nhà Bán phản hồi và quy định xử lý trong 02 ngày làm việc. | 0.309930 | Có | Nhà Bán có 02 ngày làm việc để xác nhận phương án xử lý qua Seller Center. |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | Tiki xử lý theo yêu cầu Khách Hàng và có quyền từ chối khiếu nại/các phản hồi của Nhà Bán không hợp lệ. | 0.333611 | Có | Tiki sẽ chủ động xử lý theo yêu cầu Khách Hàng và không chấp nhận khiếu nại không có căn cứ. |
| 4 | Nhà Bán xác nhận phương án xử lý yêu cầu đổi trả qua đâu trong hệ thống? | Quy trình yêu cầu đổi trả cho Nhà Bán quy định xác nhận qua Seller Center > Đơn hàng > Đổi trả bảo hành > tab Cần Nhà Bán phản hồi. | 0.234556 | Có | Nhà Bán xác nhận giải pháp trên Seller Center ở tab Cần Nhà Bán phản hồi. |
| 5 | Theo quy trình đổi mới của Hoàng Hà Mobile, khách hàng cần làm gì trước khi nhận sản phẩm mới? | Khách hàng mang sản phẩm đến cửa hàng, nhân viên thẩm định lỗi ngay tại chỗ và đổi máy mới nếu đủ điều kiện. | 0.210950 | Có | Trước khi nhận máy mới, khách hàng mang sản phẩm đến cửa hàng để nhân viên kiểm tra và xác nhận lỗi ngay. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ cách đánh giá trong nhóm:**
> Tôi học thấy rõ rằng retrieval quality không chỉ phụ thuộc vào chunking, mà còn phụ thuộc rất nhiều vào việc lựa chọn câu hỏi và metadata đúng với từng audience. Khi lọc theo `audience = buyer` hoặc `seller`, kết quả truy xuất ít nhiễu và dễ khớp đúng với ngữ cảnh nghiệp vụ hơn so với tìm kiếm không lọc.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
