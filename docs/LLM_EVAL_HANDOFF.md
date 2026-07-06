# Handoff P2 → P1: đánh giá LLM fine-tune theo metric BTC

Mục tiêu: giúp P1 biết **bản LLM fine-tune đã VƯỢT rule (leaderboard 30.75) chưa** — TRƯỚC khi tốn lượt nộp. Memory nhóm: đừng nộp bản LLM tệ hơn rule.

## TL;DR — quy trình go/no-go
```bash
# 1. P1 sinh LLM output trên Colab/Kaggle (có GPU + lora_adapter):
python src/pipeline.py --input data/test/input --output output_llm --backend llm
# 2. So với rule baseline theo metric CHÍNH THỨC BTC (dùng gold căn WHO):
python src/eval/compare_backends.py --a output --a-name rule --b output_llm --b-name llm
```
→ chỉ nộp bản LLM nếu **FINAL(llm) > FINAL(rule)**.

## Baseline rule phải vượt (official metric, gold_who, n=30 dev)
| | rule |
|---|---|
| text_score (0.3) | 0.3636 |
| assertions_score (0.3) | 0.3272 |
| candidates_score (0.4) | 0.3443 |
| **FINAL** | **0.3449** |

## ⚠️ 2 điều P1 PHẢI biết

### 1. Dùng `data/dev/gold_who`, KHÔNG dùng `data/dev/gold` để chấm candidate ICD
- `data/dev/gold` được nhóm tự gán bằng **ICD-10-CM 5 ký tự**. Nhưng bằng chứng leaderboard (probe #10) cho thấy **BTC chấm ở granularity WHO/BYT 4 ký tự**, và pipeline giờ đã rút mã về 4 ký tự (`icd_who_truncate`).
- Chấm output-WHO trên gold-CM → candidate score **thấp giả tạo** (lệch chuẩn). `data/dev/gold_who` là bản dev gold đã truncate ICD về 4 ký tự cho khớp (P2 tạo, không ghi đè bản gốc).
- Bằng chứng: rule baseline candidates_score 0.286 (gold CM) → **0.344 (gold_who)**.

### 2. Calibration: chỉ tin SO SÁNH TƯƠNG ĐỐI + text/assertion
Đối chiếu offline (gold_who) vs leaderboard #10:
| | offline | leaderboard #10 | |
|---|---|---|---|
| text_score | 0.3636 | 0.3605 | ✅ khớp tốt |
| assertions | 0.3272 | 0.3881 | offline hơi thấp |
| candidates | 0.3443 | 0.2072 | ⚠️ offline LẠC QUAN (dev vòng tròn) |

→ Absolute candidate offline phóng đại (dev gold tự-gán khớp linker của ta). **Tin phần Δ (LLM vs rule) trên cùng gold**, và text/WER (calibrate tốt).

## Fine-tune nên nhắm vào EXTRACTION, không phải candidate
Pipeline: `extract_fn` (LLM) → assertion tagger → **linker** (thêm candidates). Tức **candidates luôn do linker P2 sinh** (đã đúng WHO + RxNorm tiered), bất kể extractor. LLM chỉ cần giỏi:
- **Recall + biên span text** (ăn điểm WER — nút thắt lớn nhất, ~25% concept rule đang miss, dạng cụm tự do "đau âm ỉ vùng quanh rốn").
- **Đúng type** (sai type bị PHẠT KÉP — New_info dòng 281: tính 2 lần, mỗi lần 0đ cả 3 metric).
- Assertions do tagger lo (nhưng nếu LLM tự xuất assertions tốt hơn tagger thì càng tốt).

## Nhận xét data SFT (`data/synthetic/train_sft.jsonl`, 1500 mẫu)
- Target = `{text, type}` (không có assertions/candidates) — hợp lý vì downstream lo.
- **Thiếu KQXN dạng CHỮ**: prompt chỉ dạy giá trị số ("11.6", "90%"). BTC (forum) nói lấy cả "dương tính"/"âm tính"/"bình thường". Nên bổ sung ví dụ dạng này vào data.
- **Kiểm lặp**: BTC yêu cầu trích MỌI lần xuất hiện (nhiều JSON cùng khái niệm, khác position). Đảm bảo data dạy điều này (đừng dedup).
- Vài concept phủ định bị bỏ trong target (vd "lú lẫn", "lơ mơ" trong mẫu #1) — nếu gold thật giữ (isNegated) thì đang dạy LLM miss.

## File P2 giao
- `data/dev/gold_who/` — dev gold căn WHO (30 file) để official_scorer đúng.
- `src/eval/compare_backends.py` — so 2 dir theo metric BTC + phán quyết.
- `src/eval/official_scorer.py` — đã có sẵn, đúng metric.
