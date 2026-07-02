"""Khớp CHẨN_ĐOÁN -> ICD-10: từ điển đồng nghĩa trước, rồi fuzzy token_set_ratio.

v0 lexical (không GPU). Bản semantic (bge-m3 + reranker) sẽ bổ sung ở v1.
"""
from __future__ import annotations
import os, re, unicodedata

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_synonyms(path: str) -> list[tuple[str, list[str]]]:
    """Đọc icd_synonyms.tsv -> [(term_norm, [codes])], sắp term dài trước."""
    syn = []
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.rstrip("\n")
                if not ln or ln.startswith("#") or ln.lower().startswith("term"):
                    continue
                parts = ln.split("\t")
                if len(parts) >= 2:
                    codes = [c.strip() for c in parts[1].split(",") if c.strip()]
                    t = _norm(parts[0])
                    if t and codes:
                        syn.append((t, codes))
    syn.sort(key=lambda x: -len(x[0]))    # ưu tiên cụm dài, cụ thể hơn
    return syn


class IcdMatcher:
    def __init__(self, df, synonyms=None, fuzzy_threshold=88, top_k=3):
        self.syn = synonyms or []
        self.thr = fuzzy_threshold
        self.top_k = top_k
        self._names = []
        if df is not None and len(df):
            self._names = [(_norm(n), str(c))
                           for n, c in zip(df["name_vi"], df["code"])]

    def match(self, text: str, context: str = "") -> list[str]:
        q = _norm(text)
        if not q:
            return []
        # 1) synonym: term nằm trong câu (hoặc câu là 1 phần của term)
        for term, codes in self.syn:
            if term in q or (len(q) >= 4 and q in term):
                return codes[:self.top_k]
        # 2) fuzzy trên tên ICD
        if not fuzz or not self._names:
            return []
        scored = [(fuzz.token_set_ratio(q, n), code)
                  for n, code in self._names]
        scored = [x for x in scored if x[0] >= self.thr]
        if not scored:
            return []
        scored.sort(key=lambda x: -x[0])
        out, seen = [], set()
        for _, code in scored:
            if code in seen:
                continue
            seen.add(code)
            out.append(code)
            if len(out) >= self.top_k:
                break
        return out
