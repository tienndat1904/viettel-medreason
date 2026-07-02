"""Build embedding index cho ICD-10-CM bằng bge-m3 (T2 semantic).

CHẠY TRÊN GPU (Kaggle/Colab) — embed ~98k mô tả nên rất chậm trên CPU.
  pip install FlagEmbedding
  python src/kb/build_icd_index.py            # đọc data/kb/icd10cm.parquet

Sinh (đặt cạnh KB, KHÔNG commit vì lớn ~200MB — rebuild bằng script này):
  data/kb/icd10cm_emb.npy               # ma trận embedding đã chuẩn hóa (float16, NxD)
  data/kb/icd10cm_index_meta.parquet    # code + doc theo ĐÚNG thứ tự hàng của emb

Mỗi mã được embed bằng "name_vi | name_en" (VN neo ngôn ngữ + EN đặc tả) để bge-m3
đa ngữ khớp text tiếng Việt với mã CM.
"""
from __future__ import annotations
import os, argparse
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_doc(vi: str, en: str) -> str:
    parts = [p.strip() for p in (vi, en) if p and str(p).strip()]
    return " | ".join(parts)


def build(kb_path, emb_out, meta_out, model_id="BAAI/bge-m3",
          batch_size=256, max_length=128, use_fp16=True):
    df = pd.read_parquet(kb_path)
    vis = df["name_vi"].astype(str).tolist() if "name_vi" in df.columns else [""] * len(df)
    ens = df["name_en"].astype(str).tolist() if "name_en" in df.columns else [""] * len(df)
    codes = df["code"].astype(str).tolist()
    docs = [make_doc(v, e) for v, e in zip(vis, ens)]

    from FlagEmbedding import BGEM3FlagModel
    model = BGEM3FlagModel(model_id, use_fp16=use_fp16)
    print(f"[icd-index] embed {len(docs)} mã bằng {model_id} ...")
    out = model.encode(docs, batch_size=batch_size, max_length=max_length,
                       return_dense=True, return_sparse=False, return_colbert_vecs=False)
    emb = np.asarray(out["dense_vecs"], dtype=np.float32)
    # chuẩn hóa L2 để cosine = dot
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)

    os.makedirs(os.path.dirname(emb_out), exist_ok=True)
    np.save(emb_out, emb.astype(np.float16))
    pd.DataFrame({"code": codes, "doc": docs}).to_parquet(meta_out, index=False)
    print(f"[icd-index] emb {emb.shape} -> {emb_out}")
    print(f"[icd-index] meta {len(codes)} dòng -> {meta_out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=os.path.join(ROOT, "data/kb/icd10cm.parquet"))
    ap.add_argument("--emb", default=os.path.join(ROOT, "data/kb/icd10cm_emb.npy"))
    ap.add_argument("--meta", default=os.path.join(ROOT, "data/kb/icd10cm_index_meta.parquet"))
    ap.add_argument("--model", default="BAAI/bge-m3")
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--cpu", action="store_true", help="tắt fp16 để chạy CPU (chậm)")
    args = ap.parse_args()
    build(args.kb, args.emb, args.meta, args.model, args.batch_size, use_fp16=not args.cpu)


if __name__ == "__main__":
    main()
