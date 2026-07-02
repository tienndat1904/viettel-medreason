"""Khớp CHẨN_ĐOÁN -> ICD-10-CM: synonym trước, rồi fuzzy trên tên + depth-hedge.

KB là ICD-10-CM song ngữ (code, name_vi ghép từ BYT, name_en gốc CM, billable).
Gold dev không nhất quán độ sâu mã (lúc 3, 4, 5 ký tự; hay dùng bản 'unspecified').
=> Với nhóm bệnh khớp tốt nhất, trả kèm: mã unspecified của nhóm + mã cha (4 ký tự)
   + mã gốc (3 ký tự), best-first, cắt top_k. Tối đa hoá 'gold ∈ pred' bất kể độ sâu.

v0 lexical (không GPU). Bản semantic (bge-m3) là tuỳ chọn, hiện không vượt lexical.
"""
from __future__ import annotations
import os, re, unicodedata

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = process = None


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_synonyms(path: str):
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
    syn.sort(key=lambda x: -len(x[0]))
    return syn


def _dotless(c):
    return c.replace(".", "")


def _dot(d):
    return f"{d[:3]}.{d[3:]}" if len(d) > 3 else d


class IcdMatcher:
    def __init__(self, cm_df, byt_df=None, synonyms=None, fuzzy_threshold=88, top_k=3,
                 hedge=True):
        self.syn = synonyms or []
        self.thr = fuzzy_threshold
        self.top_k = top_k
        self.hedge = hedge          # False -> trả tập tối thiểu (tối ưu Jaccard, không hit@k)
        self._codes, self._names, self._uns, self._bill = [], [], [], []
        self._uns_rep = {}          # prefix dotless (3/4) -> mã unspecified đại diện
        _rep_score = {}
        if cm_df is not None and len(cm_df):
            has_en = "name_en" in cm_df.columns
            has_bill = "billable" in cm_df.columns
            codes = cm_df["code"].astype(str).tolist()
            vis = cm_df["name_vi"].astype(str).tolist() if "name_vi" in cm_df.columns else [""] * len(codes)
            ens = cm_df["name_en"].astype(str).tolist() if has_en else [""] * len(codes)
            bills = cm_df["billable"].tolist() if has_bill else [True] * len(codes)
            for code, vi, en, bill in zip(codes, vis, ens, bills):
                nvi = _norm(vi)
                uns = 1 if "unspecified" in en.lower() else 0
                self._codes.append(code)
                self._names.append(nvi if nvi else _norm(en))
                self._uns.append(uns)
                self._bill.append(bool(bill))
                d = _dotless(code)
                prefixes = {d[:3]} | ({d[:4]} if len(d) >= 4 else set())
                sc = (uns, 1 if bill else 0, -len(d))   # ưu tiên: unspecified, billable, ngắn
                for p in prefixes:
                    if p not in _rep_score or sc > _rep_score[p]:
                        _rep_score[p] = sc
                        self._uns_rep[p] = code
        self._code_set = set(self._codes)

    def _hedge(self, code):
        """Trả code + mã unspecified/cha cùng nhóm để phủ nhiều độ sâu, best-first.
        hedge=False -> chỉ trả chính mã (tối ưu Jaccard: mỗi mã thừa kéo tụt điểm)."""
        if not self.hedge:
            return [code]
        d = _dotless(code)
        out = [code]
        rep4 = self._uns_rep.get(d[:4]) if len(d) >= 4 else None
        rep3 = self._uns_rep.get(d[:3])
        if rep4:
            out.append(rep4)
        if len(d) >= 5:
            out.append(_dot(d[:4]))          # mã cha 4 ký tự (vd K72.90 -> K72.9)
        if rep3:
            out.append(rep3)
        if len(d) >= 4:
            out.append(d[:3])                # mã gốc 3 ký tự
        seen, res = set(), []
        for c in out:
            if c and c not in seen:
                seen.add(c)
                res.append(c)
        return res

    def _cap(self, codes):
        seen, out = set(), []
        for c in codes:
            if c and c not in seen:
                seen.add(c)
                out.append(c)
                if len(out) >= self.top_k:
                    break
        return out

    def match(self, text: str, context: str = "") -> list[str]:
        q = _norm(text)
        if not q:
            return []
        # 1) synonym: giữ mã synonym trước, rồi hedge để phủ độ sâu
        for term, codes in self.syn:
            if term in q or (len(q) >= 4 and q in term):
                out = list(codes)
                for c in codes:
                    out += self._hedge(c)
                return self._cap(out)
        # 2) fuzzy trên tên
        if not process or not self._names:
            return []
        hits = process.extract(q, self._names, scorer=fuzz.token_set_ratio,
                               limit=60, score_cutoff=self.thr)
        if not hits:
            return []

        def key(h):
            _, score, idx = h
            return (-score, -self._uns[idx], -int(self._bill[idx]),
                    len(self._codes[idx].replace(".", "")))
        hits.sort(key=key)
        best = self._codes[hits[0][2]]
        out = self._hedge(best)                      # nhóm tốt nhất: phủ nhiều độ sâu
        if self.hedge:
            for _, _, idx in hits[1:]:                # thêm nhóm khác (breadth) để dự phòng
                out.append(self._codes[idx])
        return self._cap(out)
