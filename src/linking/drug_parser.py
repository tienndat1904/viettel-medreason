"""Tách tên thuốc thành hoạt chất + hàm lượng + dạng bào chế, bỏ route/tần suất.

Ví dụ:
  "metoprolol 25mg po bid"       -> ingredient='metoprolol', strengths=['25 mg']
  "amlodipine 10 mg po daily"    -> ingredient='amlodipine', strengths=['10 mg'], form='oral tablet'?
  "Chlorpheniramine 0.4 MG/ML"   -> ingredient='chlorpheniramine', strengths=['0.4 mg/ml'], form='oral solution'
  "lasix 40mg iv" (+brand map)   -> ingredient='furosemide', strengths=['40 mg'], form='injectable solution'
Mục tiêu khớp RxNorm ở mức SCD (ingredient + strength + dose form).
"""
from __future__ import annotations
import os, re, unicodedata

# route / tần suất / cách dùng / dạng — loại khỏi phần tên hoạt chất
NOISE = {
    # route
    "po", "iv", "im", "sc", "sq", "sl", "pr", "ng", "inh", "top", "oral",
    # tần suất
    "bid", "tid", "qid", "qd", "qhs", "qam", "qpm", "od", "daily", "prn",
    "once", "q4h", "q6h", "q8h", "q12h", "q24h", "qod", "hs",
    # dạng / hậu tố
    "nebs", "neb", "nebulizer", "susp", "suspension", "soln", "solution",
    "tab", "tabs", "tablet", "cap", "caps", "capsule", "xl", "er", "sr",
    "cr", "dr", "ec", "la", "patch",
    # tiếng Việt
    "hằng", "hàng", "ngày", "uống", "tiêm", "ngậm", "dưới", "lưỡi", "mỗi",
    "lần", "viên", "khí", "dung", "truyền", "đường", "tĩnh", "mạch", "bôi",
    "nhỏ", "giọt", "ống", "gói", "x", "và", "của", "cho",
}

# đơn vị hàm lượng — SẮP DÀI TRƯỚC NGẮN để 'mg/ml' không bị nuốt thành 'mg' + '/ml'
_UNIT = (r"(mg/ml|mcg/ml|g/ml|meq/ml|units?/ml|mg/actuation|mcg/actuation|"
         r"mg|mcg|g|ml|meq|iu|units?|đơn\s*vị|%)")
_STRENGTH = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + _UNIT, re.IGNORECASE)

# cue suy ra dạng bào chế (khớp trên chuỗi gốc)
_FORM_CUES = [
    (re.compile(r"\b(neb|nebs|nebulizer)\b|khí\s*dung", re.I), "inhalant solution"),
    (re.compile(r"\b(susp|suspension)\b|hỗn\s*dịch", re.I), "oral suspension"),
    (re.compile(r"\b(soln|solution|elixir|syrup)\b|dung\s*dịch|si\s*rô|siro", re.I), "oral solution"),
    (re.compile(r"\b(cap|caps|capsule)\b|viên\s*nang", re.I), "oral capsule"),
    (re.compile(r"\b(xl|er|sr|cr|la)\b", re.I), "extended release oral tablet"),
    (re.compile(r"\b(tab|tabs|tablet)\b|viên\s*nén", re.I), "oral tablet"),
    (re.compile(r"\b(iv|im|inj|injection)\b|tiêm|truyền|tĩnh\s*mạch", re.I), "injectable solution"),
    (re.compile(r"\b(patch)\b|miếng\s*dán|cao\s*dán", re.I), "patch"),
    (re.compile(r"\b(cream|ointment|gel|lotion)\b|kem|thuốc\s*mỡ", re.I), "topical"),
]


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _norm_key(s: str) -> str:
    """Chuẩn hóa key alias/ingredient: bỏ ký tự không phải chữ-số, gộp khoảng trắng."""
    s = _strip_accents((s or "").lower())
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_brand_map(path: str) -> dict:
    """Đọc drug_brands.tsv -> {alias_norm: ingredient_lower}."""
    m = {}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.rstrip("\n")
                if not ln or ln.startswith("#") or ln.lower().startswith("alias"):
                    continue
                parts = ln.split("\t")
                if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                    m[_norm_key(parts[0])] = parts[1].strip().lower()
    return m


def infer_form(text: str) -> str | None:
    for pat, form in _FORM_CUES:
        if pat.search(text):
            return form
    if re.search(r"/\s*ml\b", text, re.I):   # nồng độ MG/ML -> thường dạng dung dịch
        return "oral solution"
    return None


def parse_drug(text: str, brand_map: dict | None = None) -> dict:
    t = (text or "").strip()
    strengths = [f"{m.group(1).replace(',', '.')} {m.group(2).lower().replace(' ', '')}"
                 for m in _STRENGTH.finditer(t)]
    form = infer_form(t)

    name = _STRENGTH.sub(" ", t)                      # bỏ phần hàm lượng khỏi chuỗi
    tokens = re.split(r"[\s,()/\-]+", name)
    ingr_tokens = []
    for tok in tokens:
        low = _strip_accents(tok.lower())
        low = re.sub(r"\d+$", "", low)                # bỏ số dính đuôi kiểu 'asa81'
        if not low or low in NOISE:
            continue
        ingr_tokens.append(low)
    ingredient = " ".join(ingr_tokens).strip(" -")

    # chuẩn hóa biệt dược / typo -> hoạt chất
    if brand_map:
        key = _norm_key(ingredient)
        if key in brand_map:
            ingredient = brand_map[key]
        else:                                         # thử khớp token đầu (vd 'toprol xl')
            first = _norm_key(ingr_tokens[0]) if ingr_tokens else ""
            if first in brand_map:
                ingredient = brand_map[first]

    return {
        "raw": text,
        "ingredient": ingredient,
        "strengths": strengths,
        "dose_form": form,
    }
