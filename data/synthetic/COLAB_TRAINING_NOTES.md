# QLoRA trên Colab T4 — nhật ký chạy & phát hiện (2026-07-03, tự động)

Chạy `notebooks/train_qlora_colab.ipynb` (điều khiển từ Claude Code qua colab-mcp) trên **Tesla T4**.

## ✅ Đã xác nhận (pipeline chạy được)
- Env numpy-safe: numpy 2.0.2 (KHÔNG hạ cấp), torch 2.11.0+cu128, transformers 5.12.1, T4.
  → chỉ `pip install -U bitsandbytes peft accelerate rapidfuzz`, KHÔNG `-r requirements.txt` (tránh hạ numpy → phải restart).
- `scripts/train_qlora.py` chạy được với transformers 5.x: tải Qwen2.5-3B (6.17G), nạp 4-bit,
  LoRA áp đúng (`trainable 29.9M / 3.12B = 0.96%`), các bước train thực thi.

## ⛔ Vấn đề chặn: T4 QUÁ CHẬM cho QLoRA
- Smoke-train (3B, 4-bit, batch1×ga16, max_len 2048): **~379 giây/step**.
- → train đầy đủ 2 epoch (1500 mẫu ≈ 187 step) ≈ **~20 GIỜ**. **Bất khả thi** trên Colab T4
  (giới hạn 12h + hay ngắt + tab MCP phải mở suốt).
- Nguyên nhân: QLoRA 4-bit (bitsandbytes) trên T4 (compute 7.5) đi đường kernel chậm; seq dài.

**Khuyến nghị:** dùng **L4 / A100** (Colab Pro) — nhanh nhiều lần. Trên T4 chỉ nên smoke-test.

## 🐞 Bug format SFT (đã sửa) — target bị cắt cụt
- Log train: **1168/1500 mẫu bị cắt ở max_len=2048**. Do mỗi mẫu SFT (bản cũ) **nhúng cả few-shot**
  → phình token; đáp án assistant ở CUỐI bị cắt → nhiều mẫu dạy model xuất JSON cụt (hại chất lượng).
- **Đã sửa `src/datagen/gen_synthetic.py`**: thêm cờ `--fewshot` (mặc định TẮT). Mẫu SFT giờ gọn
  `system + user(note) → assistant`, target JSON compact.
  - Độ dài mẫu: fewshot ~4488 ký tự → leaner ~3595 ký tự (−20%); giảm/hết cắt cụt.
  - Tiếng Việt ~1.75 ký tự/token → vài mẫu leaner vẫn ~2048 tok: nên train với `--max-len 2560`.
- ⚠️ **Cần P1 lưu ý:** khi train bằng data leaner (không few-shot), lúc **inference với model đã FT
  cũng nên BỎ few-shot** (chỉ `system + user`) cho khớp cách train. Hiện `prompt.build_messages`
  luôn kèm few-shot — cân nhắc thêm chế độ "đã FT".

## Việc đã làm để KHÔNG mất output
- `gen_synthetic.py`: fix format SFT (cờ `--fewshot`, mặc định leaner) + báo cáo token/mẫu.
- Regenerate `data/synthetic/train_sft.jsonl` bản leaner (seed 42).
- File này (nhật ký) + đẩy lên git (branch Deadpool, PR — KHÔNG merge).
- Notebook Colab: đã sửa cell 1 (Drive-free), cell 3 (numpy-safe) + thêm cell trạng thái tóm tắt.

## Bước tiếp (khi bạn dậy)
1. Đổi runtime Colab sang **L4/A100** rồi chạy lại (train khả thi về thời gian).
2. Hoặc train ở máy có GPU mạnh hơn; adapter lưu Drive (mount cần bạn bấm OAuth — tôi không tự làm được).
3. Cân nhắc adopt data leaner + chỉnh inference P1 (bỏ few-shot cho model FT), rồi đo dev bằng
   `official_scorer.py`.
