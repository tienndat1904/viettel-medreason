"""Khớp THUỐC (đã parse) với RxNorm, trả danh sách RXCUI NGẮN, best-first.

Chiến lược:
  - Index concept theo hoạt chất; khớp cả biến thể muối (vd 'metoprolol' -> 'metoprolol
    tartrate'/'succinate') bằng token-subset.
  - Lọc theo hàm lượng; ưu tiên SCD > SCDC > IN, khớp dạng bào chế, tên gọn.
  - Cắt còn max_return mã (đề muốn candidate ngắn để không tụt precision).
"""
from __future__ import annotations
import re, unicodedata

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = process = None

from drug_parser import parse_drug


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _norm_str(s):
    x = re.sub(r"\s+", "", str(s or "").lower().replace(",", "."))
    x = re.sub(r"(\d)\.0+(?![0-9])", r"\1", x)        # 3.0 -> 3
    x = re.sub(r"(\.\d*?)0+(?![0-9])", r"\1", x)      # 0.40 -> 0.4
    return x


_TTY_RANK = {"SCD": 3, "SCDF": 2, "SCDC": 2, "SBD": 1, "IN": 0, "PIN": 0, "BN": 0}


class RxNormMatcher:
    def __init__(self, df, brand_map=None, fuzzy_threshold=90, max_return=3,
                 return_level="scd"):
        self.brand_map = brand_map or {}
        self.thr = fuzzy_threshold
        self.max_return = max_return
        self.return_level = return_level    # "scd": tầng SCD>SCDC>IN | "in": trả mã hoạt chất (IN)
        self.by_ingredient: dict[str, list[dict]] = {}
        self._in_map: dict[str, str] = {}   # hoạt chất(lower) -> RXCUI của IN
        self._ingredients: list[str] = []
        self._toks: dict[str, set] = {}
        if df is not None and len(df):
            self._index(df)

    def _index(self, df):
        for _, r in df.iterrows():
            ingr = str(r.get("ingredient", "")).strip().lower()
            if not ingr:
                continue
            row = {
                "rxcui": str(r["rxcui"]),
                "tty": str(r.get("tty", "")).upper(),
                "strength": _norm_str(r.get("strength", "")),
                "dose_form": str(r.get("dose_form", "")).lower(),
                "strlen": len(str(r.get("str", ""))),
            }
            for key in {ingr, _strip_accents(ingr)}:      # set -> không append trùng
                self.by_ingredient.setdefault(key, []).append(row)
                if row["tty"] == "IN":                     # map hoạt chất -> mã IN (giữ cái đầu)
                    self._in_map.setdefault(key, row["rxcui"])
        self._ingredients = sorted(self.by_ingredient)
        self._toks = {k: set(k.split()) for k in self._ingredients}

    def _keys_for(self, q: str) -> list[str]:
        """Các khóa hoạt chất phù hợp: khớp đúng, hoặc query là tập con (query + <=1 muối)."""
        if q in self.by_ingredient:
            base = [q]
        else:
            base = []
        qtok = set(q.split())
        subset = [k for k in self._ingredients
                  if qtok <= self._toks[k] and len(self._toks[k]) - len(qtok) <= 1]
        keys = list(dict.fromkeys(base + subset))
        if keys:
            return keys
        if process and self._ingredients:              # cứu bằng fuzzy (typo nặng)
            hit = process.extractOne(q, self._ingredients, scorer=fuzz.WRatio)
            if hit and hit[1] >= self.thr:
                return [hit[0]]
        return []

    def match(self, text: str, context: str = "") -> list[str]:
        if not self.by_ingredient:
            return []
        p = parse_drug(text, self.brand_map)
        q = _strip_accents((p["ingredient"] or "").lower()).strip()
        if not q:
            return []
        keys = self._keys_for(q)
        if not keys:
            return []

        def _in_codes():
            """Mã IN (hoạt chất) — khớp đúng trả 1 mã, tránh phình tập."""
            if q in self._in_map:
                return [self._in_map[q]]
            out = []
            for k in keys:
                if k in self._in_map and self._in_map[k] not in out:
                    out.append(self._in_map[k])
            return out[:self.max_return]

        # trả mã IN (hoạt chất) — tối ưu Jaccard khi gold ở mức hoạt chất
        if self.return_level == "in":
            return _in_codes()

        rows, seen = [], set()
        for k in keys:
            for r in self.by_ingredient[k]:
                if r["rxcui"] not in seen:
                    seen.add(r["rxcui"])
                    rows.append(r)

        want = {_norm_str(s) for s in p["strengths"]}
        form = (p["dose_form"] or "").lower()

        # tiered (P3): mức mã theo thông tin mention hỗ trợ
        #   không hàm lượng -> IN | có hàm lượng + dạng uống -> SCD | dạng tiêm/mơ hồ -> SCDC
        if self.return_level == "tiered":
            if not want:                                   # thuốc trần -> IN
                return _in_codes()
            sr = [r for r in rows if r["strength"] and r["strength"] in want]
            if not sr:                                     # có liều nhưng KB thiếu mã liều -> IN an toàn
                return _in_codes()[:1]
            inj = (form == "injectable solution")
            eff_form = None if inj else (form or "oral tablet")   # uống: mặc định viên nén
            if eff_form:
                scd = [r for r in sr if r["tty"] == "SCD" and eff_form in r["dose_form"]]
                if scd:
                    scd.sort(key=lambda r: r["strlen"])
                    return [scd[0]["rxcui"]]
            scdc = [r for r in sr if r["tty"] == "SCDC"]    # dạng mơ hồ/tiêm -> SCDC
            if scdc:
                scdc.sort(key=lambda r: r["strlen"])
                return [scdc[0]["rxcui"]]
            scd_any = [r for r in sr if r["tty"] == "SCD"]  # có ý định dạng nhưng KB không có SCDC
            if eff_form and scd_any:
                scd_any.sort(key=lambda r: r["strlen"])
                return [scd_any[0]["rxcui"]]
            return _in_codes()[:1]

        scored = []
        for r in rows:
            if want:                                   # có yêu cầu hàm lượng -> phải khớp
                if not r["strength"] or r["strength"] not in want:
                    continue
            score = _TTY_RANK.get(r["tty"], 0) * 10
            if form and form and form in r["dose_form"]:
                score += 20
            elif not form and r["dose_form"] == "oral tablet":
                score += 5                             # dạng phổ biến nhất khi không rõ
            score -= min(r["strlen"], 80) * 0.1        # tên gọn (SCD gốc) ưu tiên
            scored.append((score, r["rxcui"]))

        if not scored:                                 # fallback: trả IN (hoạt chất)
            ins = [r["rxcui"] for r in rows if r["tty"] in ("IN", "PIN")]
            return ins[:1]

        scored.sort(key=lambda x: -x[0])
        out, seen = [], set()
        for _, rx in scored:
            if rx in seen:
                continue
            seen.add(rx)
            out.append(rx)
            if len(out) >= self.max_return:
                break
        return out
