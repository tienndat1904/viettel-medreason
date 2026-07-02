# KẾ HOẠCH TRIỂN KHAI — Viettel AI Race, Bài 2 (Vòng 1)
**Ontological Reasoning in Medical Knowledge Retrieval**
Thời gian: 02/07 → 30/07/2026 (28 ngày) · Nhóm 3 người · GPU: Kaggle/Colab · Top 8 → Vòng 2

---

## 0. Ràng buộc cứng (đọc trước khi làm bất cứ gì)
- **Inference chỉ dùng self-host model ≤ 9B params. CẤM mọi API ngoài** (OpenAI/Anthropic/Google) trong pipeline.
- **Được dùng LLM lớn để SINH synthetic data OFFLINE** (đề cho phép). Data sinh ra được đóng gói nộp → BTC không regenerate, nên hợp lệ. *Nên gửi 1 câu hỏi xác nhận BTC cho chắc.*
- **Reproducibility bắt buộc:** top ~15 đội nộp source + data + weights + README; BTC dựng lại & chấm trên **private test**. ⇒ Cấm hardcode; fix seed; pin deps; Dockerfile; không path tuyệt đối / cloud cá nhân.
- Submission: `output.zip` → `output/N.json` khớp `N.txt`. JSON lỗi cú pháp/sai key = **0 điểm file đó**. Tối đa **5 submit/ngày**.

## 0.1 Giả định đã chốt (không chờ BTC — có thể họ không public)
1. **Chấm điểm:** micro-F1 theo entity, match = **span khớp + type đúng**; trong cặp đã match, assertions chấm **exact-set**, candidates chấm **"gold ∈ predicted list"** (có thể rank-aware).
   → Tối ưu **span chính xác + type**; trả candidate **ngắn, best-first** (ICD 1–3, RxNorm 1–2) để không tụt precision. `scorer.py` hỗ trợ cả `exact` lẫn `overlap` để dò rủi ro.
2. **Synthetic offline: DÙNG** — đề chính đã liệt kê hợp lệ; ship kèm data trong submission.
3. **ICD-10 / RxNorm: tự tải** — ICD-10 tiếng Việt (Bộ Y tế) + RxNorm full release (NLM/RxNav) → lọc & đóng gói snapshot trong `data/kb/`.
4. **Runtime:** thiết kế pipeline chạy 100 doc gọn (~1–2h/GPU), deterministic — an toàn kể cả khi BTC có timeout.

---

## 1. Nhận định dữ liệu (đã phân tích 100 file test)
- Dữ liệu là **bệnh án lâm sàng tiếng Anh (MIMIC/i2b2-style) đã Việt hóa**: cấu trúc PMH→HPI→Hospital course; còn sót `po bid`, `q4h`, `OSH`, `MICU`, tên thuốc Latin; nhiễu dịch máy (dính chữ, `**markdown**`, khoảng trắng lỗi).
- Độ dài: ~300 → ~5700 ký tự. Mỗi file nhiều khái niệm, có lồng/trùng lặp.
- 5 loại: `TRIỆU_CHỨNG`, `TÊN_XÉT_NGHIỆM`, `KẾT_QUẢ_XÉT_NGHIỆM`, `CHẨN_ĐOÁN`, `THUỐC`.
- Assertions: `isHistorical` (mục "Thuốc trước khi nhập viện", "bệnh mạn tính", "tiền sử", "(trước đây)"); `isNegated` ("Không", "Phủ nhận", "không có"); `isFamily` ("Vợ/cháu gái/bố… có triệu chứng").
- Candidates: THUỐC→RxNorm mức **SCD (hoạt chất+hàm lượng+dạng)**, bỏ route/tần suất; CHẨN_ĐOÁN→ICD-10 3–4 ký tự, cho phép **nhiều mã** xếp theo độ tin cậy giảm dần.
- **Cạm bẫy:** tách rõ TÊN_XÉT_NGHIỆM (`wbc`) vs KẾT_QUẢ (`11.6`); `position` là **offset ký tự** → không để LLM tự đếm.

---

## 2. Kiến trúc tổng thể
```
OFFLINE (được dùng LLM lớn — chỉ để tạo DATA, không nằm trong pipeline nộp):
  (i)  Dịch i2b2/n2c2 → VN + map nhãn về 5 type + assertion   ─┐
  (ii) Sinh synthetic notes VN bắt chước style nhiễu + gold    ─┤→ TRAIN DATA (đóng gói nộp)
  (iii)Tạo DEV set có nhãn (đo offline)                        ─┘

PIPELINE NỘP (self-host ≤9B, deterministic):
  txt ─▶ [A] Extraction+Type+Assertion  (Qwen2.5-7B-Instruct + QLoRA, guided-JSON)
      ─▶ [B] Offset resolver            (code, KHÔNG dùng LLM)
      ─▶ [C] Linking
              ├─ CHẨN_ĐOÁN→ICD-10: bge-m3 (dense+sparse) → bge-reranker-v2-m3 → chọn top-k
              └─ THUỐC→RxNorm:     parse hoạt chất/hàm lượng/dạng → match RxNorm SCD → rerank
      ─▶ [D] Validate + xuất N.json  (schema-check, JSON hợp lệ 100%)
```

**Model (tất cả ≤9B, self-host):**
- Extraction/Assertion: **Qwen2.5-7B-Instruct** (Apache-2.0, đa ngữ mạnh, JSON tốt). Iterate nhanh bằng Qwen2.5-3B; bản final cân nhắc Gemma-2-9B để ensemble.
- Embedding linking: **BAAI/bge-m3** (~560M). Reranker: **BAAI/bge-reranker-v2-m3** (~568M).
- (Tùy chọn) Encoder NER **XLM-R-large** làm nhánh phụ tăng recall span/type + ensemble.

---

## 3. Cấu trúc repo (reproducible từ commit đầu)
```
viettel-medreason/
├── README.md               # cài đặt end-to-end, 1 lệnh chạy
├── Dockerfile              # môi trường cố định
├── requirements.txt        # pin version (==)
├── configs/                # yaml: model id, paths tương đối, seed=42
├── data/
│   ├── kb/                 # icd10_vn.parquet, rxnorm_scd.parquet + faiss index
│   ├── synthetic/          # data tự sinh (ĐƯỢC ship — ta sở hữu)
│   ├── external/           # script tải i2b2/n2c2 (KHÔNG ship — có DUA)
│   └── dev/                # dev set có nhãn để chấm offline
├── src/
│   ├── datagen/            # translate_i2b2.py, gen_synthetic.py, make_dev.py
│   ├── kb/                 # build_icd_index.py, build_rxnorm_index.py
│   ├── extract/            # prompt.py, run_extract.py (guided json)
│   ├── linking/            # retriever.py, reranker.py, drug_parser.py
│   ├── offset/             # resolve_spans.py
│   ├── postprocess/        # validate.py (schema), dedup.py
│   ├── pipeline.py         # đọc input/ → xuất output/
│   └── eval/               # scorer.py (F1 các thành phần)
├── scripts/                # train_qlora.sh, infer.sh, package_submission.sh
├── notebooks/              # kaggle_train.ipynb, colab_infer.ipynb
└── models/                 # LoRA adapter + download_base.py (checksum)
```
**Quy tắc:** seed=42 mọi nơi; `temperature=0` khi inference; paths tương đối; không token/cloud cá nhân; `package_submission.sh` tự validate toàn bộ JSON trước khi zip.

---

## 4. Xây dựng dữ liệu huấn luyện (mảng quyết định thắng thua)
### 4.1 Nguồn
- **i2b2 2010** (concepts problem/test/treatment + assertions) → map: problem→TRIỆU_CHỨNG/CHẨN_ĐOÁN (phân tách bằng ngữ cảnh), test→TÊN_XÉT_NGHIỆM(+KẾT_QUẢ), treatment→THUỐC. Assertion i2b2 (present/absent/possible/family/history…) → map isNegated/isFamily/isHistorical.
- **n2c2 2019** (normalization) để học linking.
- **Synthetic**: dùng LLM lớn sinh bệnh án VN **bắt chước đúng style** (3 mục, `po bid`/`q4h`, thuốc Latin, chèn nhiễu dịch: dính chữ, `**`, double-space) kèm gold labels đầy đủ (text/type/assertions/candidates + vị trí char).
### 4.2 Quy trình dịch có kiểm soát offset
- Dịch **câu-theo-câu** giữ nguyên tên thuốc/viết tắt; sau dịch, **tự tính lại offset** bằng string-match (không tin offset từ LLM).
### 4.3 Khối lượng mục tiêu
- ~3–5k notes tổng (≈70% synthetic + 30% i2b2 dịch). Dev set ~150–200 notes có nhãn (đa dạng độ khó) để chấm offline.
### 4.4 Lưu ý bản quyền (ảnh hưởng reproducibility)
- i2b2/n2c2 có **DUA, KHÔNG được redistribute** → **KHÔNG ship** trong submission. Train data chính để nộp = **synthetic ta tự sinh** (ship được). i2b2 để dạng *script tải + hướng dẫn DUA* (tùy chọn, nêu rõ trong README). ⇒ Đảm bảo pipeline reproducible **chỉ với synthetic data**.

---

## 5. Thành phần model — công thức cụ thể
### 5.1 [A] Extraction + Type + Assertion (LLM)
- Base **Qwen2.5-7B-Instruct**, **QLoRA** (4-bit nf4, double-quant, bf16), dùng **Unsloth** (tiết kiệm VRAM, chạy được Kaggle T4/Colab L4).
- LoRA r=16, alpha=32, dropout=0.05, target = tất cả linear; lr=1e-4 cosine, warmup 3%, epochs 2–3, max_seq_len 4096, grad-checkpoint, eff batch 16–32 (grad accum), seed 42.
- Output = **JSON list** `{text,type,assertions}` (KHÔNG có position). Ép JSON hợp lệ bằng **guided decoding** (vLLM `guided_json` / outlines / xgrammar).
- Prompt few-shot có ví dụ nhiễu thật + quy tắc tách TÊN vs KẾT_QUẢ và quy tắc assertion theo mục.
### 5.2 [B] Offset resolver (code)
- Với mỗi `text` do LLM trả: tìm mọi occurrence trong input (exact → nếu fail thì normalize whitespace/lowercase/bỏ `**` rồi map ngược về offset gốc). Trùng nhiều lần: gán trái-sang-phải theo thứ tự LLM liệt kê, không cho đè span.
### 5.3 [C] Linking
- **ICD-10:** index danh mục ICD-10 **tiếng Việt** (bge-m3 dense + BM25 sparse) → lấy top-30 → **bge-reranker-v2-m3** với ngữ cảnh câu → chọn 1–3 mã theo ngưỡng confidence.
- **RxNorm:** `drug_parser` tách hoạt chất + hàm lượng + dạng (loại `po/bid/daily/prn`) → khớp RxNorm **SCD** (dùng RxNav/RRF); fallback embedding-match; trả mã tin cậy nhất trước.
### 5.4 [D] Post-process & validate
- Schema-check từng object (type hợp lệ, assertions ⊆ {isNegated,isFamily,isHistorical} & chỉ cho CHẨN_ĐOÁN/THUỐC/TRIỆU_CHỨNG, candidates chỉ cho CHẨN_ĐOÁN/THUỐC, position là 2 int). Loại trùng. `json.loads` lại toàn bộ trước khi zip.

---

## 6. Bộ chấm offline (bắt buộc có sớm)
- `src/eval/scorer.py`: tính **F1 theo entity** ghép theo (span match) rồi cộng điểm type/assertion/candidate; hỗ trợ cả exact & overlap để dò theo rubric BTC. Báo cáo tách theo từng type & từng thành phần để biết cải cái gì.
- Mọi thay đổi phải tăng điểm trên dev set **trước khi** dùng 1 lượt submit.

---

## 7. Chiến lược GPU (Kaggle/Colab)
- **Train** QLoRA 7B trên Kaggle (2×T4, 30h/tuần) hoặc Colab (L4 24GB / A100 40GB) bằng Unsloth. 3B để iterate nhanh, 7B cho bản final.
- **Inference** 100 doc rất nhẹ: chạy 4-bit trên T4/L4 (transformers/vLLM). Đóng gói adapter + script tải base (checksum) cho BTC.

---

## 8. Timeline 28 ngày & phân công
**Vai trò:** P1=Extraction/Assertion · P2=Linking (ICD+RxNorm) · P3=Data/Eval/Packaging.

| Ngày | Việc | Chính |
|---|---|---|
| **02–04/07** | Dựng repo reproducible + skeleton pipeline; hỏi BTC (mục 0.1); tải/chuẩn hóa ICD-10 VN + RxNorm | cả nhóm |
| **05–08/07** | **Baseline chạy được**: few-shot Qwen2.5-7B (chưa train) + offset + linking thô → submission hợp lệ #1. Dựng scorer + dev set nhỏ | P1+P3 |
| **09–12/07** | Sinh synthetic v1 (~1.5k) + dịch i2b2 v1; QLoRA 7B lần 1 | P3 train-data, P1 train |
| **13–15/07** | Tách TÊN vs KẾT_QUẢ; luật assertion theo mục; đánh giá dev | P1 |
| **16–19/07** | Linking ICD hybrid + rerank; RxNorm SCD parser | P2 |
| **20–22/07** | Mở rộng synthetic (~4–5k), retrain; xử lý nhiễu (dính chữ, `**`, viết tắt) | P1+P3 |
| **23–26/07** | Ensemble (LLM + XLM-R), error analysis theo leaderboard, tối ưu candidates ordering | cả nhóm |
| **27–29/07** | **Đóng gói reproducible**: Docker + weights + README + test dựng lại từ đầu trên máy sạch | P3 |
| **30/07** | Chốt submit tốt nhất; dự phòng | cả nhóm |

## 9. Rủi ro & giảm thiểu
- *Sai offset* → resolver bằng code + test tự động trên dev.
- *Linking ICD tiếng Việt yếu* → hybrid + rerank + từ điển đồng nghĩa thủ công cho bệnh phổ biến.
- *Reproducibility hỏng* → CI dựng Docker sạch định kỳ; chỉ phụ thuộc synthetic data ship được.
- *Chấm sai giả định rubric* → hỏi BTC sớm; scorer hỗ trợ nhiều biến thể matching.
- *Cạn giờ GPU Kaggle* → dùng 3B iterate, 7B chỉ train bản final; log checkpoint.

## 11. Kiến thức tái dùng từ dự án Sphinx OCR (D:\Sphinx-JSC\Sphinx2)
Dự án OCR/RAG nội bộ, self-host model qua vLLM — nhiều pattern áp dụng trực tiếp:
- **Parse JSON bền vững** (`strip_thinking` + code-fence + balanced-bracket): đã port vào `src/extract/json_utils.py`. Xử lý Qwen thinking mode.
- **Serve Qwen qua vLLM OpenAI-compatible** (temperature=0; logits: `no_repeat_ngram`, whitelist token) — cân nhắc thay `transformers.generate` để nhanh & ổn định hơn; đã thêm `no_repeat_ngram_size=30` chống lặp.
- **Batching tránh truncation** (họ dùng PAGE_BATCH_SIZE=3): note dài ~5700 ký tự + nhiều entity dễ bị cắt → **chia theo mục 1/2/3** khi trích xuất rồi gộp + tính lại offset.
- **LightRAG entity + RELATIONSHIP extraction**: mẫu cho phần suy luận quan hệ khái niệm (ontological reasoning).
- **Qdrant hybrid + filter / parent-child chunking**: lựa chọn cho KB linking (thay/bổ sung FAISS); embed ngắn + rerank kèm context.
- **Normalize NFKD→ascii + stable sha256 ID**: khóa dedup & linking cho ICD/RxNorm.

## 10. Hành động ngay (48h tới)
1. Khởi tạo repo + skeleton + configs (seed, paths tương đối). 
2. Viết `pipeline.py` đọc `input/*.txt` → xuất `output/*.json` (ban đầu rule/few-shot) để có **submission hợp lệ #1**.
3. Chuẩn hóa **ICD-10 VN** + **RxNorm SCD** thành bảng + index.
4. Viết `scorer.py` + tạo dev set gán nhãn tay ~30 file để đo.
5. Gửi 4 câu hỏi BTC (mục 0.1).
