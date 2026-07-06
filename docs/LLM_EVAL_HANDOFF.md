# Handoff P2 → P1: đánh giá LLM fine-tune theo metric BTC

Mục tiêu: giúp P1 biết **bản LLM fine-tune đã VƯỢT rule (leaderboard 30.75) chưa** — TRƯỚC khi tốn lượt nộp. Memory nhóm: đừng nộp bản LLM tệ hơn rule.

## TL;DR — quy trình go/no-go
```bash
# 1. P1 sinh LLM output trên Colab/Kaggle (có GPU + lora_adapter):
python src/pipeline.py --input data/test/input --output output_llm --backend llm
# 2. So với rule baseline theo metric CHÍNH THỨC BTC:
python src/eval/compare_backends.py --a output --a-name rule --b output_llm --b-name llm
```
→ chỉ nộp bản LLM nếu **FINAL(llm) > FINAL(rule)**.

## Baseline rule phải vượt (official metric, `data/dev/gold`, n=60)
| | rule |
|---|---|
| text_score (0.3) | 0.3432 |
| assertions_score (0.3) | 0.2906 |
| candidates_score (0.4) | 0.3114 |
| **FINAL** | **0.3147** |

> Dùng `data/dev/gold` — P3 đã chuẩn hóa ICD về **WHO/BYT 4 ký tự** + điền RxNorm tiered (PR#32, issue #40), khớp cách BTC chấm. (Bản `gold_who` tạm của P2 đã bỏ vì gold/ giờ chính là WHO.)

## Calibration — offline giờ khá khớp leaderboard
| | offline (gold, n=60) | leaderboard #10 |
|---|---|---|
| text_score | 0.3432 | 0.3605 |
| assertions | 0.2906 | 0.3881 |
| candidates | 0.3114 | 0.2072 |
| **FINAL** | **0.3147** | **~0.3075** |

FINAL offline (0.3147) ≈ leaderboard (0.3075) → gold/ 60-file WHO là proxy đáng tin cho **so sánh tương đối** LLM-vs-rule. (assertions offline hơi thấp, candidates hơi cao — vẫn dùng tốt cho hướng Δ.)

## Fine-tune nên nhắm EXTRACTION, không phải candidate
Pipeline: `extract_fn` (LLM) → assertion tagger → **linker** (thêm candidates). **Candidates luôn do linker P2 sinh** (đã đúng WHO + RxNorm tiered), bất kể extractor. LLM chỉ cần giỏi:
- **Recall + biên span text** (ăn điểm WER — nút thắt lớn nhất, ~25% concept rule đang miss, dạng cụm tự do "đau âm ỉ vùng quanh rốn").
- **Đúng type** (sai type bị PHẠT KÉP — New_info dòng 281: tính 2 lần, mỗi lần 0đ cả 3 metric).
- Assertions do tagger lo (nếu LLM tự xuất tốt hơn thì càng tốt).

## Nhận xét data SFT (`data/synthetic/train_sft.jsonl`, 1500 mẫu)
- Target = `{text, type}` (không assertions/candidates) — hợp lý vì downstream lo.
- **Thiếu KQXN dạng CHỮ**: prompt chỉ dạy giá trị số. BTC (forum) nói lấy cả "dương tính"/"âm tính"/"bình thường". Nên bổ sung ví dụ.
- **Kiểm lặp**: BTC yêu cầu trích MỌI lần xuất hiện (nhiều JSON, khác position) — đừng dedup.
- Vài concept phủ định bị bỏ trong target (vd "lú lẫn", "lơ mơ") — nếu gold giữ (isNegated) thì đang dạy LLM miss.

## File liên quan
- `src/eval/compare_backends.py` — so 2 dir theo metric BTC + phán quyết (default gold `data/dev/gold`).
- `src/eval/official_scorer.py` — chấm 1 dir theo metric BTC.
