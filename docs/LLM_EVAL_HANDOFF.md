# Handoff P2 → P1: đánh giá LLM fine-tune theo metric BTC

Mục tiêu: giúp P1 biết **bản LLM fine-tune đã VƯỢT rule chưa** — TRƯỚC khi tốn lượt nộp. Memory nhóm: đừng nộp bản LLM tệ hơn rule.

> ⚠️ **CẬP NHẬT 07/07/2026 — LLM đã bị GẠCH khỏi bản nộp** (P1, `fc4a7b5`): LLM extractor dev **0.156 ≪ rule 0.368** (sai biên span bệnh án thật), RAG không cải thiện. **Bản nộp chính thức = `--backend rule`** (không GPU/internet). Doc này giữ lại vì (a) quy trình go/no-go còn dùng nếu LLM hồi sinh, (b) **bảng calibration bên dưới là công cụ đọc offline↔leaderboard cho MỌI thay đổi rule.**

## TL;DR — quy trình go/no-go
```bash
# 1. P1 sinh LLM output trên Colab/Kaggle (có GPU + lora_adapter):
python src/pipeline.py --input data/test/input --output output_llm --backend llm
# 2. So với rule baseline theo metric CHÍNH THỨC BTC:
python src/eval/compare_backends.py --a output --a-name rule --b output_llm --b-name llm
```
→ chỉ nộp bản LLM nếu **FINAL(llm) > FINAL(rule)**.

## Baseline rule (official metric, `data/dev/gold`, n=60) — theo tiến độ
| | state #12 | bản rule 34.19 (đã nộp) | +nhóm3 đợt2 (chưa nộp) |
|---|---|---|---|
| text_score (0.3) | 0.3928 | 0.4439 | 0.4552 |
| assertions_score (0.3) | 0.3502 | 0.4238 | 0.4409 |
| candidates_score (0.4) | 0.3624 | 0.5039 | 0.5391 |
| **FINAL (offline)** | 0.3679 | 0.4619 | 0.4845 |
| **leaderboard thật** | 32.691 | **34.191** | (chưa nộp) |

> ⚠️ **Offline FINAL KHÔNG bằng leaderboard** — xem bảng calibration bên dưới. Bản rule 34.19 offline 0.4619 nhưng leaderboard chỉ 0.3419 (candidate vòng tròn).
> Dùng `data/dev/gold` (WHO/BYT 4 ký tự + RxNorm tiered). State 34.19 = longest-match cross-type (`resolve_spans`) + biên chẩn đoán có đuôi + bệnh phổ biến (commit `902e53a`, theo `docs/EXTRACTION_MISS_DX.md`).

## Calibration — offline ↔ leaderboard (2 data point trực tiếp)
| | offline #12 | lb #12 | offline 34.19 | lb 34.19 | nhận xét |
|---|---|---|---|---|---|
| text_score | 0.3928 | 0.3858 | 0.4439 | 0.4073 | #12 sát khít (lệch .007); sau khi THÊM CỤM DEV → offline vống ~+.037 |
| assertions | 0.3502 | 0.4103 | 0.4238 | 0.4203 | giờ **sát khít** (trước bi quan ~-.06) |
| candidates | 0.3624 | 0.2202 | 0.5039 | 0.2341 | **vòng tròn NẶNG**: offline 0.50 vs lb 0.23 (lệch +.27!) |
| **FINAL** | 0.3679 | 0.3269 | 0.4619 | **0.3419** | offline overshoot **~6.5×** (dự +.094, thật +.015) |

**⚠️ BÀI HỌC BẮT BUỘC (chuẩn lại 07/07/2026):** thêm gazetteer/synonym **lấy từ dev-gold** làm offline THỔI PHỒNG cả candidate (nặng) LẪN text (vừa) — vì khớp trivial 60 file dev; gain thật chỉ ở 40 file leaderboard ngoài dev + phần generalize private-test. Đo rule-change trên dev: **discount candidate mạnh (>50%), text ~30%; chỉ tin Δ hướng + độ lớn nhỏ, submission mới là thật.** Fix **cấu trúc** (longest-match, luật) generalize tốt hơn nhiều so với thêm cụm cụ thể.

**Quy tắc dùng:** tin `text_score`/`assert` ở mức tương đối (Δ, hướng); **KHÔNG** tin candidate offline absolute. Bản rule 34.19: offline dự +0.094 nhưng leaderboard thật chỉ +0.0145 (32.740→34.191) — cả 3 sub-score vẫn tăng thật, đóng góp đều.

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
