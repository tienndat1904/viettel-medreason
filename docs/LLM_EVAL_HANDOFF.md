# Handoff P2 → P1: đánh giá LLM fine-tune theo metric BTC

Mục tiêu: giúp P1 biết **bản LLM fine-tune đã VƯỢT rule (leaderboard #12 = 32.691) chưa** — TRƯỚC khi tốn lượt nộp. Memory nhóm: đừng nộp bản LLM tệ hơn rule.

## TL;DR — quy trình go/no-go
```bash
# 1. P1 sinh LLM output trên Colab/Kaggle (có GPU + lora_adapter):
python src/pipeline.py --input data/test/input --output output_llm --backend llm
# 2. So với rule baseline theo metric CHÍNH THỨC BTC:
python src/eval/compare_backends.py --a output --a-name rule --b output_llm --b-name llm
```
→ chỉ nộp bản LLM nếu **FINAL(llm) > FINAL(rule)**.

## Baseline rule phải vượt (official metric, `data/dev/gold`, n=60) — cập nhật sau #12
| | rule (state #12) |
|---|---|
| text_score (0.3) | 0.3928 |
| assertions_score (0.3) | 0.3502 |
| candidates_score (0.4) | 0.3624 |
| **FINAL** | **0.3679** |

> Dùng `data/dev/gold` — P3 đã chuẩn hóa ICD về **WHO/BYT 4 ký tự** + điền RxNorm tiered (PR#32, issue #40), khớp cách BTC chấm. (Bản `gold_who` tạm của P2 đã bỏ vì gold/ giờ chính là WHO.)
> State #12 = gazetteer dấu hiệu thực thể/triệu chứng (PR#46) + offset giữ mọi occurrence (P1, `08b266d`).

## Calibration — offline ↔ leaderboard (chuẩn lại bằng #12, đo trực tiếp)
| | offline (gold, n=60) | leaderboard #12 | nhận xét |
|---|---|---|---|
| text_score | 0.3928 | 0.3858 | **SÁT KHÍT** — tin tuyệt đối |
| assertions | 0.3502 | 0.4103 | offline **bi quan** (~ -0.06) |
| candidates | 0.3624 | 0.2202 | offline **lạc quan** (~ +0.14, dev vòng tròn) |
| **FINAL** | **0.3679** | **0.3269** | lệch chủ yếu do candidates |

**Quy tắc dùng:** tin `text_score` absolute; tin assert/cand chỉ ở phần **so sánh tương đối** (Δ giữa A và B). Offline dự Δfinal +0.0167 (state #11→#12), leaderboard thực +0.0095 — cùng chiều, độ lớn hơi thổi (do cand).

**Ngưỡng go/no-go cho LLM:** bản LLM phải cho **text_score offline > ~0.393** (và KHÔNG tụt assert) mới thực sự vượt rule trên leaderboard. text_score là phần LLM có thể ăn (recall + biên span cụm tự do); candidates do linker P2 sinh nên gần như không đổi giữa rule/LLM.

## Fine-tune nên nhắm EXTRACTION, không phải candidate
Pipeline: `extract_fn` (LLM) → assertion tagger → **linker** (thêm candidates). **Candidates luôn do linker P2 sinh** (đã đúng WHO + RxNorm tiered), bất kể extractor. LLM chỉ cần giỏi:
- **Recall + biên span text** (ăn điểm WER — nút thắt lớn nhất, ~25% concept rule đang miss, dạng cụm tự do "đau âm ỉ vùng quanh rốn").
- **Đúng type** (sai type bị PHẠT KÉP — New_info dòng 281: tính 2 lần, mỗi lần 0đ cả 3 metric).
- Assertions do tagger lo (nếu LLM tự xuất tốt hơn thì càng tốt).

## Data SFT (`data/synthetic/train_sft.jsonl`, 1500 mẫu) — các gap đã xử lý
- Target = `{text, type}` (không assertions/candidates) — hợp lý vì downstream lo.
- ✅ **KQXN dạng CHỮ ngắn** (dương/âm tính/bình thường): đã thêm — PR#45.
- ✅ **KQXN mô tả chẩn đoán hình ảnh** (cụm dài "xẹp phổi thùy dưới phải…"): đã thêm — PR#46 (`IMAGING_FINDINGS`, 1453/1500 mẫu). BTC forum HHM #2 xác nhận là KẾT_QUẢ_XÉT_NGHIỆM; rule không vét được → đây là recall LLM ăn được.
- ✅ **Lặp occurrence**: P1 đã fix ở `resolve_offsets` (`08b266d`, giữ mọi occurrence) → đường LLM không còn mất mention lặp.
- (Ghi chú "concept phủ định bị bỏ trong target" ở bản cũ đã RÚT — kiểm lại target #1 vẫn giữ đủ lú lẫn/lơ mơ, quan sát cũ do view bị cắt 700 ký tự.)

→ **Việc còn lại của P1: retrain QLoRA trên `train_sft.jsonl` mới** rồi chạy go/no-go ở trên.

## File liên quan
- `src/eval/compare_backends.py` — so 2 dir theo metric BTC + phán quyết (default gold `data/dev/gold`).
- `src/eval/official_scorer.py` — chấm 1 dir theo metric BTC.
