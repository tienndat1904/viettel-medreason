"""Kiểm tra & làm sạch output đúng schema. File JSON sai = 0 điểm nên PHẢI chặn ở đây."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import LABELS, ASSERTIONS, ASSERTABLE_TYPES, CANDIDATE_TYPES


def clean_concept(c: dict, text_len: int) -> dict | None:
    """Chuẩn hóa 1 concept; trả None nếu không cứu được."""
    if not isinstance(c, dict):
        return None
    ctype = c.get("type")
    if ctype not in LABELS:
        return None
    pos = c.get("position")
    if (not isinstance(pos, (list, tuple)) or len(pos) != 2
            or not all(isinstance(x, int) for x in pos)):
        return None
    s, e = int(pos[0]), int(pos[1])
    if not (0 <= s < e <= text_len):
        return None

    out = {"text": str(c.get("text", "")), "type": ctype, "position": [s, e]}

    # assertions chỉ cho type được phép, chỉ nhận 3 giá trị hợp lệ
    asserts = c.get("assertions", []) or []
    if ctype in ASSERTABLE_TYPES:
        out["assertions"] = [a for a in asserts if a in ASSERTIONS]
    else:
        out["assertions"] = []

    # candidates chỉ cho CHẨN_ĐOÁN / THUỐC
    if ctype in CANDIDATE_TYPES:
        cands = c.get("candidates", []) or []
        out["candidates"] = [str(x) for x in cands]
    return out


def clean_file(concepts: list, text: str) -> list:
    """Làm sạch toàn bộ concept của 1 file + loại trùng (cùng position+type)."""
    seen = set()
    cleaned = []
    for c in concepts:
        cc = clean_concept(c, len(text))
        if cc is None:
            continue
        key = (cc["position"][0], cc["position"][1], cc["type"])
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(cc)
    return cleaned


def assert_valid(concepts: list, text_len: int) -> None:
    """Raise nếu có gì sai — gọi trước khi ghi file/zip."""
    import json
    json.dumps(concepts, ensure_ascii=False)  # phải serialize được
    for c in concepts:
        assert c["type"] in LABELS, f"type sai: {c.get('type')}"
        s, e = c["position"]
        assert 0 <= s < e <= text_len, f"position sai: {c['position']}"
        for a in c.get("assertions", []):
            assert a in ASSERTIONS, f"assertion sai: {a}"
