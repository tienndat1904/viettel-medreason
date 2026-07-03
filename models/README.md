# models/ — LoRA adapter (weights) cho inference

`.gitignore` bỏ qua file weights (`*.safetensors`, `*.bin`) để repo không phình.
Khi **nộp source-code cho BTC**, PHẢI kèm adapter theo 1 trong 2 cách:

## Cách A (khuyến nghị): đóng adapter vào gói nộp
Sau khi QLoRA xong, thư mục adapter (vd `qwen-lora/`) gồm:
```
models/qwen-lora/
├── adapter_config.json
├── adapter_model.safetensors
└── (tokenizer files)
```
Copy nguyên thư mục này vào `models/` **trong gói zip nộp BTC** (dù không commit lên git).
`configs/config.yaml → extract.lora_adapter: models/qwen-lora` để pipeline nạp.

## Cách B: script tải + checksum
Nếu adapter host ở nơi khác (HF Hub / Drive public), thêm `models/download_adapter.sh`
tải về `models/qwen-lora/` và ghi checksum trong README để BTC verify.

## Base model
Pipeline nạp base **Qwen2.5-3B-Instruct** (hoặc model ghi ở `config.yaml → extract.llm_model`)
từ HuggingFace. Môi trường BTC cần **internet** để tải (hoặc mount HF cache sẵn).
Nếu BTC offline: kèm cả base model weights và trỏ `llm_model` về đường dẫn local.

## Kiểm tra nhanh sau khi có adapter
```bash
python src/pipeline.py --input data/test/input --output output --backend llm
python scripts/package_submission.py --output output --input data/test/input --n 100
```
Không cần adapter (few-shot) vẫn chạy được: để trống `extract.lora_adapter`.
