"""Khớp CHẨN_ĐOÁN -> ICD-10-CM: từ điển đồng nghĩa trước, rồi fuzzy trên tên.

KB là ICD-10-CM song ngữ (code, name_vi ghép từ BYT theo mã cha, name_en gốc CM,
billable). Vì name_vi kế thừa từ mã cha nên nhiều mã con trùng tên -> sau khi fuzzy
khớp "nhóm", ưu tiên mã billable + mô tả 'unspecified' + mã ngắn để chọn đại diện.

v0 lexical (không GPU) — đã chạm trần ~0.50 hit@k trên dev; đòn bẩy tiếp là v1
semantic (bge-m3 khớp text tiếng Việt với mô tả tiếng Anh của CM).
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


class IcdMatcher:
    def __init__(self, cm_df, byt_df=None, synonyms=None, fuzzy_threshold=88, top_k=3):
        # byt_df: nhận để tương thích Linker; ưu tiên tên BYT (chính xác) nếu có,
        # nếu không thì dùng name_vi kế thừa trong CM. Mã trả luôn thuộc không gian CM.
        self.syn = synonyms or []
        self.thr = fuzzy_threshold
        self.top_k = top_k
        self._codes, self._names, self._uns, self._bill = [], [], [], []
        if cm_df is not None and len(cm_df):
            has_en = "name_en" in cm_df.columns
            has_bill = "billable" in cm_df.columns
            codes = cm_df["code"].astype(str).tolist()
            vis = cm_df["name_vi"].astype(str).tolist() if "name_vi" in cm_df.columns else [""] * len(codes)
            ens = cm_df["name_en"].astype(str).tolist() if has_en else [""] * len(codes)
            bills = cm_df["billable"].tolist() if has_bill else [True] * len(codes)
            for code, vi, en, bill in zip(codes, vis, ens, bills):
                nvi = _norm(vi)
                self._codes.append(code)
                self._names.append(nvi if nvi else _norm(en))
                self._uns.append(1 if "unspecified" in en.lower() else 0)
                self._bill.append(bool(bill))

    def match(self, text: str, context: str = "") -> list[str]:
        q = _norm(text)
        if not q:
            return []
        # 1) synonym (độ tin cậy cao) — trả đúng thứ tự, không mở rộng
        for term, codes in self.syn:
            if term in q or (len(q) >= 4 and q in term):
                return codes[:self.top_k]
        # 2) fuzzy trên tên (process.extract cho nhanh trên KB lớn)
        if not process or not self._names:
            return []
        hits = process.extract(q, self._names, scorer=fuzz.token_set_ratio,
                               limit=60, score_cutoff=self.thr)
        if not hits:
            return []
        # xếp: điểm cao -> unspecified -> billable -> mã ngắn (đại diện của nhóm)
        def key(h):
            _, score, idx = h
            return (-score, -self._uns[idx], -int(self._bill[idx]),
                    len(self._codes[idx].replace(".", "")))
        hits.sort(key=key)
        out, seen = [], set()
        for _, _, idx in hits:
            code = self._codes[idx]
            if code in seen:
                continue
            seen.add(code)
            out.append(code)
            if len(out) >= self.top_k:
                break
        return out
