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
100 file dev đã gán nhãn (phủ toàn bộ test public; bản nháp — xem `data/dev/ANNOTATION_GUIDE.md`, cần người review).
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
Chấm chính thức bằng `official_scorer` (metric BTC) trên **100 file** `data/dev/gold` (1756 concept):
backend `rule` (bản nộp) FINAL ≈ **0.3325** (text 0.353 · assert 0.303 · cand 0.339). Đây là baseline
go/no-go: chỉ chuyển sang LLM nếu `compare_backends.py` cho FINAL(llm) > FINAL(rule).
(Trên 60 file dev đầu FINAL ≈ 0.3679; giảm khi thêm 40 file sau nhiều KQXN/vitals/mô tả hình ảnh hơn.)

## Synthetic data + QLoRA (train LLM extractor) — ⚠️ THÍ NGHIỆM, KHÔNG dùng khi nộp
> LLM extractor sai biên span trên bệnh án thật (dev 0.156 ≪ rule 0.368). Giữ lại để tham khảo; **bản nộp dùng `rule`**.
```bash
# Sinh 1500 bệnh án VN + gold + train_sft.jsonl (offline, không API — reproducible, seed=42)
python src/datagen/gen_synthetic.py --n 1500 --seed 42
# QLoRA fine-tune Qwen2.5-3B (default) trên GPU -> LoRA adapter. T4-lite: notebooks/train_qlora_colab.ipynb
python scripts/train_qlora.py --data data/synthetic/train_sft.jsonl --model Qwen/Qwen2.5-3B-Instruct \
    --out models/qwen-lora --max-samples 500 --epochs 1 --max-len 1536   # T4-lite; bỏ --max-samples cho L4/A100
# rồi điền configs/config.yaml: extract.lora_adapter: models/qwen-lora ; backend: llm
# (inference tự bỏ few-shot khi có adapter — khớp SFT leaner)
```
Chi tiết bộ dữ liệu: `data/synthetic/DATA_CARD.md`. `train_sft.jsonl` khớp `prompt.py` (target `[{text,type}]`).

## Tái lập cho BTC (nộp source-code vòng top-15)
BTC dựng lại & chấm trên **private test**. Gói nộp gồm: toàn bộ code, data (synthetic + KB parquet đã ship), README này.

> **BẢN NỘP CHÍNH THỨC = `--backend rule`** (đạt leaderboard 32.74). Đường này **KHÔNG cần GPU, KHÔNG cần internet** (KB đã ship trong `data/kb/*.parquet`) → tái lập tuyệt đối, chạy vài giây/100 file. Các nhánh LLM (QLoRA) và RAG (bge-m3) là **thí nghiệm — KHÔNG dùng khi nộp** (LLM sai biên span, RAG không cải thiện; xem `docs/`). Đừng chạy `--backend llm`.

**Cách 1 — pip (khuyến nghị, không cần GPU):**
```bash
pip install -r requirements-submit.txt        # 6 gói core đã PIN, KHÔNG torch/GPU/internet
python src/pipeline.py --input <private_test>/input --output output --backend rule
python scripts/package_submission.py --output output --input <private_test>/input --n <N>
```

**Cách 2 — Docker (bulletproof):**
```bash
docker build -t viettel-medreason .
docker run -v /path/private_test/input:/data/input -v $PWD/out:/app/output \
    viettel-medreason python3 src/pipeline.py --input /data/input --output output --backend rule
docker run -v $PWD/out:/app/output viettel-medreason \
    python3 scripts/package_submission.py --output output --input /data/input --n <N>
```

**Yêu cầu tái lập đã đảm bảo:** seed=42 mọi nơi · `temperature=0` (deterministic) · path tương đối · KB parquet ship kèm (không cần tải/đăng ký/internet) · `requirements-lock.txt` pin version đã test · rule không phụ thuộc model ngoài → output bất biến trên mọi máy.

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
- [x] Khung repo reproducible + pipeline (rule/llm) + offset/validator/scorer/packager
- [x] official_scorer (metric BTC) — khớp leaderboard (0.20 ≈ 0.197)
- [x] KB ICD-10-CM + RxNorm + linking tối ưu Jaccard (ICD 0.443 / RxNorm 0.823)
- [x] Assertion module (~0.94) · LLM extractor + chunking · synthetic 1500 + QLoRA script
- [x] Dev set 100 file có nhãn (phủ toàn bộ test public) + tooling (ICD chuẩn WHO/BYT, RxNorm tiered)
- [x] Gói tái lập BTC: Dockerfile + requirements-lock + README rebuild + models/README
- [ ] QLoRA thật (đang train T4-lite / cần L4-A100 cho full)
- [x] Test dựng lại máy sạch (venv sạch + requirements-submit → rule pipeline + package = 100 file hợp lệ, không GPU/internet). Adapter LLM là thí nghiệm, KHÔNG vào bản nộp rule.
- [x] Dev phủ 100/100 file test public · [ ] (Nên có) ensemble · semantic v1
```
