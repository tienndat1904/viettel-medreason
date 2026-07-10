# Frontier reference output (silver) — 100 file test

Bộ **nhãn bạc** cho toàn bộ 100 file `data/test/input/*.txt`, sinh bằng **LLM frontier**
(đọc input, KHÔNG đọc gold) đóng vai **extractor**, rồi đẩy qua ĐÚNG pipeline P2
(`resolve_offsets` → assertion tagger → linker). Dùng làm **trần chất lượng để đối chiếu**
hướng fine-tune của P1 — **KHÔNG phải bản nộp**.

## Thư mục
- `raw_extract/N.json` — đầu ra thô của extractor: `[{text, type}]` (chỉ text + loại).
- `full/N.json` — bộ đầy đủ format BTC: `{text, type, position, assertions, candidates}`
  (candidates/assertions do linker/tagger P2 sinh, y hệt đường rule).
  *(đặt tên `full/` thay vì `output/` để tránh `.gitignore` chặn thư mục `output/`.)*

## Điểm (60 file có gold, metric BTC offline)
| | text | assert | cand | FINAL |
|---|---|---|---|---|
| rule (bản nộp 34.315) | 0.4164 | 0.4224 | 0.4996 | 0.4515 |
| **frontier (bộ này)** | 0.4706 | 0.5745 | 0.5795 | **0.5453** (+0.094) |

→ ước lượng leaderboard **~40-43đ**. Trần "extraction hoàn hảo + linker/tagger P2" đo được là
**0.922** offline → nút thắt là **extraction**, không phải linker (0.836) hay tagger (0.958).

## ⚠️ Không đồng đều — đọc kỹ trước khi dùng
100 file do **18 agent frontier độc lập** trích, mỗi agent tự quyết biên/ngưỡng → có phương sai:
- Chất lượng theo batch (60 file gold): mean FINAL trải **0.33 → 0.68** (chênh 0.35).
- Mật độ concept/1000 ký tự theo batch: **9.0 → 22.6** (chênh 2.5×) = khác nhau về độ mạnh tay.
- Outlier đã biết: file 41 over-extract (điểm âm), file 26 chỉ 1 concept (under-extract).

**Tính đồng đều thật sự đến từ MỘT model đơn áp một chính sách** — tức chính là output QLoRA của P1.
Bộ đa-agent này là *trần tham chiếu*, không phải *chuẩn vàng đồng đều*.

## Cách dùng cho fine-tune (P1)
1. **Nhãn bạc distill**: train QLoRA ≤9B trên `{input → raw_extract concepts}` để model học
   biên/recall của frontier mà vẫn chạy offline hợp lệ.
2. **Mốc đối chiếu**: sau mỗi lần FT, so output QLoRA vs `full/` để biết còn cách trần bao xa,
   thua ở loại nào (recall? biên? type?).
3. **Cô lập biến**: vì candidates/assertions ở đây do linker/tagger P2 sinh, chênh giữa QLoRA và
   frontier là **thuần extraction**.

## 🚫 KHÔNG nộp trực tiếp
Đây là output do LLM frontier (API, không offline/≤9B) sinh cho input CÔNG KHAI. Nộp file này lên
leaderboard = "hard-code output" mà BTC nêu đích danh sẽ bắt khi dựng lại code trên private test
(New_info.md dòng 85). Điểm public sẽ sụp ở vòng code + rủi ro DQ. Con đường ăn điểm THẬT là
distill vào model nộp được của nhóm.

## Tái tạo
- Extractor: LLM frontier, spec theo `data/dev/ANNOTATION_GUIDE.md` (5 type, biên bổ ngữ, tách
  tên-XN vs kết-quả, giữ concept bị phủ định, bỏ thủ thuật/yếu-tố-nguy-cơ).
- Pipeline hoàn thiện: `resolve_offsets` + `assertions.annotate(mode=replace)` + `Linker`.
