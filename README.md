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

# LLM (Qwen2.5-7B) — chạy trên GPU Kaggle/Colab (self-host ≤9B, KHÔNG API ngoài)
pip install -r requirements-gpu.txt        # torch/transformers/bitsandbytes/peft
python src/pipeline.py --input <thư_mục_test> --output output --backend llm
#   hoặc mở notebooks/run_llm_colab.ipynb (Colab) / run_llm_kaggle.ipynb (Kaggle)
#   QLoRA fine-tune trên synthetic: notebooks/train_qlora_colab.ipynb
#   Hướng dẫn chi tiết (cả Colab & Kaggle): docs/KAGGLE_GUIDE.md

# Đóng gói + validate (JSON lỗi = 0 điểm nên luôn chạy bước này trước khi nộp)
python scripts/package_submission.py --output output --input data/test/input --n 100
```
**LLM extractor:** chunk văn bản theo dòng (`extract.max_chunk_chars`) để tránh cắt output với note dài;
LLM chỉ sinh `{text, type}` (few-shot), offset do `resolve_spans` tính, assertion do `assertions.py`
điền (`extract.assertion_mode`), candidates do `linker`. Điền `extract.lora_adapter` sau khi QLoRA.

## Dev set có nhãn (để đo offline)
30 file dev đã gán nhãn (bản nháp — xem `data/dev/ANNOTATION_GUIDE.md`, cần người review).
```bash
# Sinh gold từ label spec (tự tính offset ký tự, validate schema)
python src/datagen/make_dev.py                    # data/dev/labels/*.json -> data/dev/gold/*.json
# Xem review trực quan (span tô màu trên văn bản gốc)
python src/datagen/build_review_html.py           # -> data/dev/review/index.html
```

## Chấm offline (dev set có nhãn tại data/dev/gold)
```bash
python src/pipeline.py --input data/test/input --output output --backend rule
python src/eval/scorer.py --pred output --gold data/dev/gold --mode overlap   # span+type, assertion
python src/eval/eval_linking.py                                               # linking ICD/RxNorm (tách khỏi extractor)
```
Baseline backend `rule` trên 30 file dev: **F1(span+type) ≈ 0.34 (overlap) / 0.24 (exact)**;
CHẨN_ĐOÁN & THUỐC span = 0 (rule chưa phủ) → cần LLM extractor (P1). Assertion (P1) ≈ 0.97.
Linking (P2, đo riêng): ICD hit@k 16.5%, RxNorm ingredient-hit 78.9%.

## Synthetic data + QLoRA (train LLM extractor)
```bash
# Sinh 1500 bệnh án VN + gold + train_sft.jsonl (offline, không API — reproducible, seed=42)
python src/datagen/gen_synthetic.py --n 1500 --seed 42
# QLoRA fine-tune Qwen2.5-7B trên GPU (Kaggle/Colab) -> LoRA adapter
python scripts/train_qlora.py --data data/synthetic/train_sft.jsonl --out models/qwen7b-lora
# rồi điền configs/config.yaml: extract.lora_adapter: models/qwen7b-lora ; backend: llm
```
Chi tiết bộ dữ liệu: `data/synthetic/DATA_CARD.md`. `train_sft.jsonl` khớp `prompt.py` (target `[{text,type}]`).

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
- [x] Dev set ~30 file có nhãn (nháp) + tooling make_dev/review + baseline đo được (P3)
- [ ] KB: ICD-10 VN + RxNorm index
- [ ] LLM extractor fine-tune (QLoRA) + synthetic data
- [ ] Linking hoàn chỉnh (retrieve + rerank)
- [ ] Mở rộng dev set ~150 file + review tay
```
