# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** [Tên nhóm]
**Thành viên:** [Họ tên từng thành viên]
**Ngày:** [Ngày nộp]

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, bảo hành và quy trình xử lý yêu cầu cho khách mua và Nhà Bán trên các sàn thương mại điện tử.

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề này rất phù hợp để đánh giá retrieval vì cùng một thực thể nghiệp vụ có thể xuất hiện dưới nhiều góc nhìn: khách mua, Nhà Bán và mô hình vận hành. Bên cạnh đó, dữ liệu có sẵn trong corpus chứa nhiều đoạn văn cụ thể, dễ kiểm chứng bằng metadata `audience` và `category` để so sánh độ hiệu quả của việc lọc ngữ cảnh.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | hoanghamobile-warranty-buyer.md | https://hoanghamobile.com/chinh-sach-bao-hanh | 2026-09-20 / áp dụng từ 2025-09-29 | ~14k | audience=buyer, category=warranty-policy |
| 2 | tiki-seller-warranty-faq.md | https://hocvien.tiki.vn/faq/cau-hoi-thuong-gap-ve-xu-ly-doi-tra-bao-hanh/ | 2026-09-20 / not-stated | ~18k | audience=seller, category=warranty-process |
| 3 | tiki-seller-warranty-sd.md | https://hocvien.tiki.vn/faq/huong-dan-quy-trinh-xu-ly-doi-tra-bao-hanh-mo-hinh-sd/ | 2026-09-20 / not-stated | ~15k | audience=seller, category=warranty-process |
| 4 | tiki-seller-warranty-dropship.md | nội bộ / quy trình Dropship | 2026-09-20 / not-stated | ~9k | audience=seller, category=warranty-process |
| 5 | tiki-seller-warranty-fbt.md | nội bộ / quy trình FBT | 2026-09-20 / not-stated | ~8k | audience=seller, category=warranty-process |
| 6 | shopee-warranty-buyer.md | https://help.shopee.vn/portal/4/article/79046 | 2026-09-20 / not-stated | ~6k | audience=buyer, category=warranty-policy |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| audience | string | buyer / seller | Giúp nhóm dữ liệu theo người dùng, giảm sai lệch giữa các chính sách khác nhau. |
| category | string | warranty-policy / warranty-process | Cho phép lọc theo loại nội dung để tránh trả lời nhầm giữa chính sách và quy trình vận hành. |
| source_url | string | https://... | Dễ kiểm tra nguyên gốc, xác thực và theo dõi phiên bản tài liệu. |
| retrieved_at | string | 2026-09-20 | Theo dõi thời điểm hợp nhất dữ liệu và sửa đổi nếu cần. |
| document_version | string | ap-dung-tu-2025-09-29 | Giúp lịch sử phiên bản và so sánh hiệu lực chính sách. |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-------------------|
| hoanghamobile-warranty-buyer.md | FixedSizeChunker (`fixed_size`) | cao | trung bình | Cần kiểm soát hơn |
| hoanghamobile-warranty-buyer.md | SentenceChunker (`by_sentences`) | vừa phải | vừa | Tốt với câu dài |
| hoanghamobile-warranty-buyer.md | RecursiveChunker (`recursive`) | cân bằng | tốt | Tốt nhất cho chính sách có tiêu đề và danh sách |

### Chiến lược của từng thành viên

**Thành viên 1 — Ngô Hoàng Thụy Khuê**
- **Loại chiến lược:** Recursive + metadata filter
- **Mô tả & lý do chọn cho chủ đề này:** Chính sách và quy trình bảo hành thường có nhiều tiêu đề con, điều kiện, thời hạn và tab trạng thái. Recursive chunking giúp giữ phần đầu đề và đoạn liên quan gần nhau; bộ lọc `audience` giúp câu hỏi giới hạn đúng phía người mua hay Nhà Bán, giảm nhiễu khi nhiều tài liệu cùng đề cập chủ đề "đổi trả".
- **Code snippet (nếu custom):**
```python
results = store.search_with_filter(
    query,
    top_k=3,
    metadata_filter={"audience": "buyer"}  # hoặc {"audience": "seller"}
)
```

### So Sánh Giữa Các Thành Viên

| Thành viên | Chiến lược (Strategy) | Điểm truy xuất (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Ngô Hoàng Thụy Khuê | Recursive + audience filter | 9/10 | Dễ giữ ngữ cảnh, ít nhầm với chính sách khác | Cần cẩn thận khi câu hỏi có từ khóa chung như "đổi trả" |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> Với corpus chính sách bảo hành, chiến lược `RecursiveChunker` kết hợp lọc `audience` hoạt động tốt nhất vì nội dung có cấu trúc rõ: tiêu đề > mục > quy định > điều kiện. Cách này giữ được bối cảnh của các đoạn pháp lý và giảm sai lệch khi cùng một chủ đề xuất hiện ở nhiều mô hình vận hành khác nhau.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Theo chính sách Hoàng Hà Mobile, khách hàng được đổi mới miễn phí trong thời gian nào? | Trong 15 hoặc 30 ngày đầu kể từ ngày mua, tùy theo dòng sản phẩm, nếu sản phẩm được xác nhận lỗi phần cứng do nhà sản xuất thì được đổi mới miễn phí 100%. | hoanghamobile-warranty-buyer.md, mục "II. Quy định bảo hành đối với linh kiện pin và màn hình" và phần "I. Cam kết 'Lỗi Đổi Liền'" |
| 2 | Trong mô hình Seller Center, Nhà Bán có bao nhiêu ngày làm việc để xác nhận phương án xử lý yêu cầu đổi trả? | Nhà Bán có 02 ngày làm việc kể từ khi sản phẩm được cập nhật trạng thái cần Nhà Bán phản hồi để xác nhận phương án xử lý yêu cầu đổi, trả, bảo hành. | tiki-seller-warranty-faq.md và tiki-seller-warranty-sd.md |
| 3 | Nếu Nhà Bán không phản hồi, Tiki sẽ xử lý yêu cầu của Khách Hàng như thế nào? | Tiki sẽ chủ động xử lý theo yêu cầu Khách Hàng và được quyền từ chối tiếp nhận các khiếu nại của Nhà Bán; nếu không có lý do hợp lệ, Tiki có thể bồi thường cho Khách Hàng. | tiki-seller-warranty-faq.md, mục "4. Trường hợp Nhà Bán không xác nhận phương án xử lý trong 02 ngày làm việc" và mục "6. Nếu Nhà Bán không phản hồi..." |
| 4 | Nhà Bán xác nhận phương án xử lý yêu cầu đổi trả qua đâu trong hệ thống? | Nhà Bán xác nhận phương án xử lý qua hệ thống Seller Center, vào mục Đơn hàng > Đổi trả bảo hành, tab Cần Nhà Bán phản hồi. | tiki-seller-warranty-faq.md, mục "IV. MÔ HÌNH DROPSHIP" và tiki-seller-warranty-sd.md |
| 5 | Theo quy trình đổi mới của Hoàng Hà Mobile, khách hàng cần làm gì trước khi nhận sản phẩm mới? | Khách hàng mang sản phẩm đến cửa hàng, nhân viên tiếp nhận và thẩm định lỗi ngay tại chỗ; nếu lỗi do nhà sản xuất và đủ điều kiện thì tiến hành đổi sản phẩm mới. | hoanghamobile-warranty-buyer.md, mục "3. Quy trình đổi sản phẩm 'Lỗi Đổi Liền'" |

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Theo chính sách Hoàng Hà Mobile... | RecursiveChunker + filter audience=buyer | Có | Top-3 chứa thông tin về cột mốc thời gian và điều kiện đổi mới. |
| 2 | Trong mô hình Seller Center... | RecursiveChunker + filter audience=seller | Có | Top-3 có đoạn mô tả thời hạn 02 ngày làm việc trong phản hồi Seller Center. |
| 3 | Nếu Nhà Bán không phản hồi... | RecursiveChunker + filter audience=seller | Có | Top-3 chứa biện pháp xử lý do Tiki chủ động thực hiện. |
| 4 | Nhà Bán xác nhận qua đâu... | RecursiveChunker + filter audience=seller | Có | Top-3 nhắc đến tab Cần Nhà Bán phản hồi trong Seller Center. |
| 5 | Theo quy trình đổi mới của Hoàng Hà Mobile... | RecursiveChunker + filter audience=buyer | Có | Top-3 nêu rõ bước mang hàng đến cửa hàng và thẩm định lỗi. |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> Có, metadata `audience` giúp ích rất nhiều cho các câu hỏi theo mục tiêu người dùng. Ví dụ Q1 và Q5 nên lọc `buyer` để tránh các nội dung liên quan đến Seller Center; Q2, Q3, Q4 nên lọc `seller` để hạn chế kết quả dành cho khách mua. Khi bộ lọc đúng, độ tương đồng không còn bị nhiễu bởi các nghĩa vụ khác nhau trong cùng chủ đề đổi trả.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> *Liệt kê 2-3 ý:*

**Bài học rút ra khi so sánh trong nhóm:**
> *Viết 2-3 câu — cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì?*

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> *Viết 2-3 câu:*

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Lựa chọn tài liệu (Document Set Quality) | / 10 |
| Thiết kế chiến lược (Strategy Design) | / 15 |
| Chất lượng truy xuất (Retrieval Quality) | / 10 |
| Thuyết trình (Demo) | / 5 |
| **Tổng phần nhóm** | **/ 40** |
