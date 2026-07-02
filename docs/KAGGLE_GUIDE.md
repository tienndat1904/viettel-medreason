# Hướng dẫn chạy LLM extractor trên Kaggle (chi tiết)

Mục tiêu: chạy `backend=llm` (Qwen2.5-7B-Instruct, self-host ≤9B) sinh `output/*.json`
cho tập test và đo trên dev gold. **Không dùng API ngoài.**

> TL;DR: tạo Notebook GPU + Internet ON → clone repo → cài deps → smoke-test 3 file →
> chạy full 100 file → `package_submission.py` → tải `output.zip`.

---

## Dùng Google Colab (thay cho Kaggle)
Colab OK cho inference Qwen-7B 4-bit; QLoRA sau này nên dùng **Colab Pro** (L4/A100). Mở sẵn: **`notebooks/run_llm_colab.ipynb`**.
1. **Runtime → Change runtime type → GPU** (T4 Free đủ; L4/A100 nếu có Pro).
2. **Mount Google Drive + đặt `HF_HOME` vào Drive** → cache model, khỏi tải lại 15GB mỗi phiên (Colab hay ngắt idle ~90 phút):
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   import os; os.environ['HF_HOME'] = '/content/drive/MyDrive/hf_cache'
   ```
3. Clone repo vào `/content`, cài `requirements.txt` + `requirements-gpu.txt`, rồi chạy như mục 4–7 dưới đây (đường dẫn `/content/viettel-medreason` thay cho `/kaggle/working/...`).
4. Tải kết quả: `from google.colab import files; files.download('output.zip')`.

Khác biệt chính so với Kaggle: Colab không cần phone-verify để có internet, nhưng dễ ngắt phiên → **cache model vào Drive** và **smoke-test trước** càng quan trọng.

---

## 0. Chuẩn bị tài khoản (1 lần)
- Kaggle → **Settings → Phone verification** (bắt buộc để bật Internet + GPU).
- Quota GPU: **~30 giờ/tuần**, mỗi session tối đa ~12h (T4) / 9h. Đừng để notebook chạy không.

## 1. Tạo Notebook
1. kaggle.com → **Create → New Notebook**.
2. Panel bên phải (**Notebook options**):
   - **Accelerator**: `GPU T4 x2` (hoặc `GPU P100`). T4 16GB đủ cho Qwen-7B 4-bit.
   - **Internet**: **On** (cần để `pip install` + tải model từ HuggingFace).
   - **Persistence**: Files only (tùy chọn).

## 2. Lấy code vào notebook
**Cách A — clone GitHub (repo public):**
```python
%cd /kaggle/working
!git clone https://github.com/tienndat1904/viettel-medreason.git
%cd viettel-medreason
```
**Cách B — repo private / không internet lúc chạy:** nén repo → **Add Data → Upload dataset** →
mount ở `/kaggle/input/...` rồi `cp -r` sang `/kaggle/working/viettel-medreason`.

> Repo đã kèm `data/test/input/` (100 file public). Nếu chạy trên **private test của BTC**,
> upload nó thành Kaggle Dataset rồi trỏ `--input /kaggle/input/<tên>/input`.

## 3. Cài dependencies
**KHÔNG cài lại transformers/torch** (dùng bản có sẵn của Kaggle/Colab — đã hợp triton 3.x). Chỉ cài core nhẹ + **cập nhật bitsandbytes** (fix `triton.ops` + binary CUDA):
```python
!pip install -q -r requirements.txt
!pip install -q -U bitsandbytes peft accelerate
import torch, transformers, bitsandbytes as bnb
print("torch", torch.__version__, "| transformers", transformers.__version__,
      "| bnb", bnb.__version__, "| CUDA", torch.cuda.is_available())
```
> Vì sao KHÔNG `pip install -r requirements-gpu.txt` cứng: pin `transformers==4.46.3` + `bitsandbytes==0.44.1` cũ gây xung đột và lỗi `No module named 'triton.ops'` trên Colab/Kaggle. `requirements-gpu.txt` (dạng range) chỉ để BTC dựng lại offline.

## 4. SMOKE TEST trước (tiết kiệm quota!) — 3–5 file
Đừng chạy thẳng 100 file. Test nhỏ để chắc model + JSON parse OK:
```python
import os, shutil
os.makedirs("smoke/input", exist_ok=True)
for n in [1, 5, 50]:
    shutil.copy(f"data/test/input/{n}.txt", f"smoke/input/{n}.txt")
!python src/pipeline.py --input smoke/input --output smoke/out --backend llm
!cat smoke/out/5.json
```
Xem output có đúng schema (`text/type/position/assertions/candidates`) và không rỗng.
Lần đầu sẽ tải model (~15GB, vài phút).

## 5. Chạy full 100 file
```python
!python src/pipeline.py --input data/test/input --output output --backend llm
```
**Ước lượng thời gian:** HF `generate` tuần tự ~ vài chục giây/file → **~1–3 giờ** cho 100 file.
Muốn nhanh:
- Dùng **Qwen2.5-3B-Instruct** để lặp nhanh (đổi `configs/config.yaml: extract.llm_model`), 7B cho bản cuối.
- Giảm `extract.max_new_tokens` (vd 1024) nếu output ngắn.

## 6. Đóng gói + validate (BẮT BUỘC trước khi nộp)
```python
!python scripts/package_submission.py --output output --input data/test/input --n 100
```
JSON lỗi cú pháp/sai key = **0 điểm file đó** → luôn chạy bước này. File `output.zip` nằm ở
`/kaggle/working/viettel-medreason/output.zip`.

## 7. Đo trên dev gold (để biết điểm trước khi dùng lượt submit)
```python
!python src/eval/scorer.py --pred output --gold data/dev/gold --mode overlap
!python src/eval/scorer.py --pred output --gold data/dev/gold --mode exact
```
So với mốc rule baseline (F1 span+type ~0.34 overlap). Đây là lần đầu **CHẨN_ĐOÁN/THUỐC > 0**.
Đo linking riêng: `!python src/eval/eval_linking.py`.

## 8. Tải `output.zip` về
- Panel **Output** (bên phải) → tải `output.zip`, hoặc
- **Save Version** (Save & Run All) → vào version → Output → Download.

---

## Xử lý sự cố (troubleshooting)
| Triệu chứng | Cách xử lý |
|---|---|
| `CUDA out of memory` | Đảm bảo `load_in_4bit` (mặc định True); giảm `max_chunk_chars`/`max_new_tokens`; T4 x2 sẽ tự shard (`device_map=auto`). |
| Tải model chậm/timeout | Internet phải ON; chạy lại cell (HF cache lại); hoặc thêm Qwen làm Kaggle Dataset để mount offline. |
| `bitsandbytes` import error | `!pip install -q -U bitsandbytes`; kiểm tra CUDA khả dụng. |
| `No module named 'triton.ops'` | bitsandbytes cũ (0.44) vs triton 3.x → `!pip install -q -U bitsandbytes` (đã đưa vào cell cài đặt). |
| `Could not find bitsandbytes CUDA binary ...cuda128.so` | Cùng nguyên nhân → `-U bitsandbytes` để lấy binary khớp CUDA của Colab/Kaggle. |
| JSON rỗng / thiếu concept | Xem raw output 1 chunk; kiểm tra parser (`json_utils`); giảm `max_chunk_chars` để bớt cắt. |
| Quá chậm | Dùng 3B trước; hoặc cân nhắc vLLM (v1) để tăng tốc. |
| Kết quả khác giữa 2 lần chạy | Đảm bảo `temperature=0` (đã đặt); seed cố định trong config. |

## Lưu ý reproducibility (nộp source cho BTC)
- BTC dựng lại & chấm trên private test. Nếu môi trường BTC **không có internet**, phải **kèm model weights**
  (hoặc script tải có checksum) — ghi rõ trong README. Adapter LoRA (sau QLoRA) đóng gói trong `models/`.
- Mọi path tương đối, seed cố định, `temperature=0` → chạy lại cho kết quả nhất quán.
