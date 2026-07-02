# T2 — Semantic ICD linking (bge-m3 + reranker)

Nâng ICD linking vượt trần lexical (~0.50) bằng khớp ngữ nghĩa: bge-m3 embed mô tả
ICD-10-CM (song ngữ VN|EN) → retrieve top-k (cosine) → **bge-reranker-v2-m3** rerank →
lọc theo `min_confidence` → trả 1–3 mã. Xử lý các ca lexical sai ngữ nghĩa
(vd "viêm tụy" → K85.x thay vì L73.2).

## Kiến trúc
```
build (GPU, 1 lần):  icd10cm.parquet ──bge-m3──> icd10cm_emb.npy (+ index_meta.parquet)
inference:  text VN ─embed─> cosine top-30 ─rerank(query,doc)─> lọc ngưỡng ─> top 1-3 mã
```
- `src/kb/build_icd_index.py` — tạo embedding (chạy GPU).
- `src/linking/icd_semantic.py` — `SemanticIcdMatcher` (retrieve+rerank+lọc), lazy-load model.
- `configs/config.yaml` → `linking.backend: semantic` để bật.
- Thiếu index/model → Linker **tự fallback lexical** (pipeline luôn chạy).

## Chạy trên Kaggle/Colab (GPU)
```bash
pip install FlagEmbedding
# tại thư mục repo (đã có data/kb/icd10cm.parquet):
python src/kb/build_icd_index.py            # GPU T4/L4: ~vài phút cho 98k mã
# -> sinh data/kb/icd10cm_emb.npy (~200MB) + data/kb/icd10cm_index_meta.parquet
```
Tải 2 file này về đặt vào `data/kb/` của repo local (chúng bị .gitignore vì lớn —
rebuild bằng script, không commit).

## Bật & đo
```bash
# đặt linking.backend: semantic trong config (hoặc sửa tạm)
python src/eval/eval_linking.py             # cần GPU cho embed query + rerank
```
So sánh hit@k ICD với bản lexical (0.495). Tinh chỉnh `icd_top_k_retrieve`,
`icd_top_k_return`, `min_confidence` theo dev.

## Lưu ý
- **Inference cũng cần model** (embed query + rerank) → chạy `eval_linking`/`pipeline`
  với `backend: semantic` nên ở nơi có GPU; CPU chạy được nhưng chậm.
- Embedding & meta **không commit** (lớn) → reproducible bằng cách chạy lại script.
- Test logic không cần GPU: `python tests/test_icd_semantic.py` (dùng embedder giả).
