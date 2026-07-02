"""Test logic semantic ICD (T2) KHÔNG cần GPU — bơm embed_fn/rerank_fn giả.

Kiểm tra: retrieve (cosine) + rerank + lọc ngưỡng + synonym-first, và Linker
tự fallback lexical khi chưa có embedding index.
Chạy: python tests/test_icd_semantic.py
"""
from __future__ import annotations
import os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ["linking", "kb", ""]:
    sys.path.insert(0, os.path.join(ROOT, "src", sub) if sub else os.path.join(ROOT, "src"))

import yaml
from icd_semantic import SemanticIcdMatcher
from icd_match import _norm

FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -> {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


# --- fixture KB nhỏ + embedder/reranker giả dựa trên trùng token ---
CODES = ["K85.9", "L73.2", "I10"]
DOCS = ["viem tuy cap | acute pancreatitis",
        "viem tuyen mo hoi | hidradenitis suppurativa",
        "tang huyet ap | hypertension"]
EMB = np.eye(len(CODES), dtype=np.float32)      # mỗi doc 1 vector one-hot trực giao


def _overlap(q, doc):
    qs, ds = set(_norm(q).split()), set(_norm(doc).split())
    return len(qs & ds) / (len(qs) or 1)


def fake_embed(text):
    # trả one-hot của doc trùng token nhiều nhất -> cosine retrieve chọn đúng doc
    best = int(np.argmax([_overlap(text, d) for d in DOCS]))
    return EMB[best]


def fake_rerank(query, docs):
    return np.array([_overlap(query, d) for d in docs], dtype=np.float32)


def test_semantic_logic():
    print("== SemanticIcdMatcher (stub embed/rerank) ==")
    m = SemanticIcdMatcher(EMB, CODES, DOCS, fake_embed, fake_rerank,
                           synonyms=[("viem phoi", ["J18.9"])],
                           top_k_retrieve=3, top_k_return=2, min_confidence=0.3)
    check("viêm tụy -> K85.9", m.match("viêm tụy")[:1] == ["K85.9"], m.match("viêm tụy"))
    check("tăng huyết áp -> I10", "I10" in m.match("tăng huyết áp"), m.match("tăng huyết áp"))
    check("synonym 'viêm phổi' -> J18.9", m.match("viêm phổi") == ["J18.9"], m.match("viêm phổi"))
    # ngưỡng cao + query không liên quan -> rỗng
    hi = SemanticIcdMatcher(EMB, CODES, DOCS, fake_embed, fake_rerank,
                            top_k_retrieve=3, top_k_return=2, min_confidence=0.99)
    check("ngưỡng cao lọc hết -> []", hi.match("xyz không liên quan") == [], hi.match("xyz"))


def test_linker_fallback():
    print("== Linker backend=semantic khi CHƯA có index -> fallback lexical ==")
    from linker import Linker
    cfg = yaml.safe_load(open(os.path.join(ROOT, "configs/config.yaml"), encoding="utf-8"))
    cfg["linking"]["backend"] = "semantic"
    lk = Linker(cfg)
    check("fallback về lexical", lk._icd_mode == "lexical", lk._icd_mode)
    check("vẫn link được (synonym)", lk.link_diagnosis("tăng huyết áp") == ["I10"],
          lk.link_diagnosis("tăng huyết áp"))


if __name__ == "__main__":
    test_semantic_logic()
    test_linker_fallback()
    print()
    if FAILS:
        print(f"❌ {len(FAILS)} FAIL: {FAILS}")
        sys.exit(1)
    print("✅ Tất cả test semantic PASS")
