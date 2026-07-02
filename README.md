# viettel-medreason — Bài 2: Ontological Reasoning in Medical Knowledge Retrieval

Hệ thống trích xuất & chuẩn hóa khái niệm y tế từ bệnh án tiếng Việt (Viettel AI Race, Vòng 1).
Đọc `input/*.txt` → xuất `output/*.json` gồm: `text`, `position [start,end]`, `type` (5 nhãn),
`assertions` (isNegated/isFamily/isHistorical), `candidates` (ICD-10 cho CHẨN_ĐOÁN, RxNorm cho THUỐC).

> Kế hoạch chi tiết & phân công: xem **`PLAN.md`**.

## Ràng buộc thi (Vòng 1)
- Inference **chỉ self-host model ≤ 9B**, CẤM API ngoài.
- Được dùng LLM lớn **sinh synthetic data offline** (đóng gói kèm submission).
- **Reproducible**: BTC dựng lại & chấm trên private test. Seed cố định, path tương đối, không cloud cá nhân.

## Cài đặt
```bash
python -m venv .venv && source .venv/bin/activate   # hoặc conda
pip install -r requirements.txt
# Train QLoRA cài thêm trong notebook: unsloth, bitsandbytes, peft, trl (xem notebooks/)
```

## Chạy pipeline
```bash
# Baseline rule (chạy được ngay, không cần GPU) → có submission hợp lệ #1
python src/pipeline.py --input data/test/input --output output --backend rule

# LLM (Qwen2.5-7B + LoRA) — chạy trên GPU Kaggle/Colab
python src/pipeline.py --input <thư_mục_test> --output output --backend llm

# Đóng gói + validate (JSON lỗi = 0 điểm nên luôn chạy bước này trước khi nộp)
python scripts/package_submission.py --output output --input data/test/input --n 100
```

## Chấm offline (khi có dev set có nhãn tại data/dev/gold)
```bash
python src/eval/scorer.py --pred output --gold data/dev/gold --mode overlap
```

## Cấu trúc
```
src/
  pipeline.py          # end-to-end
  extract/             # rules_baseline.py (baseline) | llm_extractor.py + prompt.py
  offset/              # resolve_spans.py  (tự tính offset ký tự, KHÔNG tin LLM)
  linking/             # linker.py (bge-m3 + reranker) | drug_parser.py (RxNorm SCD)
  postprocess/         # validate.py (schema check)
  eval/                # scorer.py
  kb/                  # build index ICD-10 VN + RxNorm (TODO)
  datagen/             # sinh synthetic + dịch i2b2 (TODO)
data/
  test/input/          # 100 file test public
  kb/                  # ICD-10 VN, RxNorm (chưa build)
  synthetic/ dev/      # data tự sinh (ship được) + dev set có nhãn
  external/            # i2b2/n2c2 — KHÔNG commit (vướng DUA)
```

## Trạng thái
- [x] Khung repo reproducible + pipeline chạy được (backend rule)
- [x] Offset resolver, validator, scorer, packager
- [ ] KB: ICD-10 VN + RxNorm index
- [ ] LLM extractor fine-tune (QLoRA) + synthetic data
- [ ] Linking hoàn chỉnh (retrieve + rerank)
- [ ] Dev set có nhãn để đo offline
```
