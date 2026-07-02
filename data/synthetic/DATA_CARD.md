# Synthetic training data — viettel-medreason (P3)

Dữ liệu huấn luyện tự sinh cho LLM extractor (P1). **Sinh offline, KHÔNG dùng API ngoài**
→ reproducible, ship kèm submission (đề cho phép synthetic data).

## Sinh lại (deterministic)
```bash
python src/datagen/gen_synthetic.py --n 1500 --seed 42 --out-dir data/synthetic
```
`seed=42` → luôn ra đúng bộ này. Muốn ship toàn bộ note+gold: thêm `--save-notes`.

## Nội dung
| File | Ý nghĩa |
|---|---|
| `train_sft.jsonl` | **1500 mẫu SFT** cho QLoRA. Mỗi dòng `{"messages":[...]}` khớp `src/extract/prompt.py` (import `build_messages` → không lệch). Target assistant = `[{text,type}]`. |
| `notes/*.txt` | 20 note mẫu (soi bằng mắt) |
| `gold/*.json` | full gold 20 note mẫu (text/type/**position**/assertions/candidates) |

Thống kê 1500 note: ~47.2k concept (tb 31.5/note), độ dài ~640–1100 ký tự.
Phân bố: TRIỆU_CHỨNG 12.7k · TÊN_XÉT_NGHIỆM 12.0k · KẾT_QUẢ 8.9k · THUỐC 7.5k · CHẨN_ĐOÁN 6.1k.

## Cách sinh (compositional — vì sao chọn)
Lắp ghép từ `src/datagen/pools.py` theo cấu trúc 3 mục giống bệnh án test:
`1. Tiền sử bệnh` → `2. Bệnh sử hiện tại` → `3. Đánh giá tại bệnh viện`.
- **Offset chính xác 100%**: ta tự đặt span khi build chuỗi (đã assert `text[s:e]==text` mọi concept).
- **Assertion theo ngữ cảnh**: mục "Thuốc trước khi nhập viện"/"bệnh mạn tính"/"Tiền sử" → `isHistorical`;
  tiền tố "Không/Phủ nhận/không có" → `isNegated`; "Vợ/Bố/Con... có" → `isFamily`.
- **Candidates**: CHẨN_ĐOÁN → mã ICD-10 (pools, best-effort); THUỐC → RxNorm ingredient rxcui.
- **Nhiễu dịch máy**: dính chữ (bỏ dấu cách), `**markdown**`, double-space, dấu phẩy thập phân,
  route/tần suất `po bid`/`q4h`/`iv`/`nebs`, tách TÊN_XÉT_NGHIỆM vs KẾT_QUẢ.
- **Dòng nhiễu không nhãn** (hành chính, lối sống) để dạy model KHÔNG trích lung tung.

## Huấn luyện (→ QLoRA)
```bash
python scripts/train_qlora.py --data data/synthetic/train_sft.jsonl --out models/qwen7b-lora
# xong: điền configs/config.yaml -> extract.lora_adapter: models/qwen7b-lora
```
`train_qlora.py` completion-only (chỉ học phần assistant), 4-bit nf4, LoRA r=16/α=32, seed=42.

## Giới hạn & hướng mở rộng
- Vocab bệnh/thuốc từ pools (~50 bệnh, ~35 thuốc) → **đa dạng vừa phải**; template có cấu trúc
  nên câu văn "sạch" hơn note thật. Nên trộn với dev/i2b2 dịch để tăng độ khó (T2–T3).
- Mã ICD/RxNorm là best-effort (train chỉ dùng text+type; candidates cho eval là phụ).
- Mở rộng: thêm entry vào `pools.py`, thêm mẫu câu tự sự (narrative) dạng đoạn văn dài.
