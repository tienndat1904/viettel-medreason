"""Semantic ICD linking (T2): bge-m3 retrieve + bge-reranker-v2-m3 rerank.

Thiết kế tách rời để test không cần GPU:
  - SemanticIcdMatcher nhận `embed_fn` (text -> vector) và `rerank_fn` (query, docs -> điểm 0..1)
    qua tham số → test bơm hàm giả.
  - `load_semantic(cfg, syn)` nạp embedding (build_icd_index.py) + tạo hàm bge THẬT (lazy).

Luồng match: synonym trước → embed query → cosine top-k retrieve (numpy) →
rerank cặp (query, doc) → lọc theo min_confidence → trả top_k mã, best-first.
"""
from __future__ import annotations
import os
import numpy as np

from icd_match import load_synonyms, _norm   # tái dùng chuẩn hóa + synonym


class SemanticIcdMatcher:
    def __init__(self, emb, codes, docs, embed_fn, rerank_fn, synonyms=None,
                 top_k_retrieve=30, top_k_return=3, min_confidence=0.30):
        self.emb = np.ascontiguousarray(emb, dtype=np.float32)   # (N,D) đã chuẩn hóa L2
        self.codes = list(codes)
        self.docs = list(docs)
        self.embed_fn = embed_fn
        self.rerank_fn = rerank_fn
        self.syn = synonyms or []
        self.kr = top_k_retrieve
        self.kk = top_k_return
        self.thr = min_confidence

    def match(self, text: str, context: str = "") -> list[str]:
        if not text or not text.strip():
            return []
        # 1) synonym (độ tin cậy cao) — như lexical
        nq = _norm(text)
        for term, codes in self.syn:
            if term in nq or (len(nq) >= 4 and nq in term):
                return codes[:self.kk]
        if self.emb.size == 0:
            return []
        # 2) retrieve top-k bằng cosine (emb đã chuẩn hóa)
        v = np.asarray(self.embed_fn(text), dtype=np.float32).ravel()
        n = np.linalg.norm(v)
        if n > 0:
            v = v / n
        scores = self.emb @ v
        kr = min(self.kr, len(scores))
        idx = np.argpartition(-scores, kr - 1)[:kr]
        idx = idx[np.argsort(-scores[idx])]
        cand_docs = [self.docs[i] for i in idx]
        # 3) rerank + lọc ngưỡng
        rr = np.asarray(self.rerank_fn(text, cand_docs), dtype=np.float32).ravel()
        order = np.argsort(-rr)
        out, seen = [], set()
        for j in order:
            if rr[j] < self.thr:
                break
            code = self.codes[idx[j]]
            if code not in seen:
                seen.add(code)
                out.append(code)
                if len(out) >= self.kk:
                    break
        return out


def build_bge_functions(cfg):
    """Trả (embed_fn, rerank_fn) dùng bge-m3 + bge-reranker THẬT, lazy-load model."""
    L = cfg.get("linking", {})
    embed_model = L.get("embed_model", "BAAI/bge-m3")
    rerank_model = L.get("reranker_model", "BAAI/bge-reranker-v2-m3")
    use_fp16 = bool(L.get("use_fp16", True))
    state = {}

    def _ensure():
        if "emb" not in state:
            from FlagEmbedding import BGEM3FlagModel, FlagReranker
            state["emb"] = BGEM3FlagModel(embed_model, use_fp16=use_fp16)
            state["rr"] = FlagReranker(rerank_model, use_fp16=use_fp16)

    def embed_fn(text):
        _ensure()
        out = state["emb"].encode([text], return_dense=True,
                                  return_sparse=False, return_colbert_vecs=False)
        return np.asarray(out["dense_vecs"][0], dtype=np.float32)

    def rerank_fn(query, docs):
        _ensure()
        if not docs:
            return np.zeros(0, dtype=np.float32)
        scores = state["rr"].compute_score([[query, d] for d in docs], normalize=True)
        if not isinstance(scores, (list, tuple, np.ndarray)):
            scores = [scores]
        return np.asarray(scores, dtype=np.float32)

    return embed_fn, rerank_fn


def load_semantic(cfg, synonyms=None):
    """Nạp SemanticIcdMatcher từ config; trả None nếu thiếu embedding/model (để fallback lexical)."""
    L = cfg.get("linking", {})
    paths = cfg.get("paths", {})
    emb_path = paths.get("icd_emb", "data/kb/icd10cm_emb.npy")
    meta_path = paths.get("icd_index_meta", "data/kb/icd10cm_index_meta.parquet")
    if not (os.path.exists(emb_path) and os.path.exists(meta_path)):
        print(f"[linker] semantic: thiếu index ({emb_path} / {meta_path}) "
              f"— chạy build_icd_index.py trên GPU. Tạm fallback lexical.")
        return None
    try:
        import pandas as pd
        emb = np.load(emb_path).astype(np.float32)
        meta = pd.read_parquet(meta_path)
        embed_fn, rerank_fn = build_bge_functions(cfg)
        return SemanticIcdMatcher(
            emb, meta["code"].astype(str).tolist(), meta["doc"].astype(str).tolist(),
            embed_fn, rerank_fn, synonyms=synonyms,
            top_k_retrieve=L.get("icd_top_k_retrieve", 30),
            top_k_return=L.get("icd_top_k_return", 3),
            min_confidence=L.get("min_confidence", 0.30))
    except Exception as e:  # noqa
        print(f"[linker] semantic không nạp được ({e}); fallback lexical.")
        return None
