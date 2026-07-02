"""Định nghĩa nhãn, schema khái niệm y tế và tiện ích chung."""
from __future__ import annotations

# 5 loại khái niệm hợp lệ
TRIEU_CHUNG = "TRIỆU_CHỨNG"
TEN_XET_NGHIEM = "TÊN_XÉT_NGHIỆM"
KET_QUA_XET_NGHIEM = "KẾT_QUẢ_XÉT_NGHIỆM"
CHAN_DOAN = "CHẨN_ĐOÁN"
THUOC = "THUỐC"

LABELS = {TRIEU_CHUNG, TEN_XET_NGHIEM, KET_QUA_XET_NGHIEM, CHAN_DOAN, THUOC}

# assertions hợp lệ
IS_NEGATED = "isNegated"
IS_FAMILY = "isFamily"
IS_HISTORICAL = "isHistorical"
ASSERTIONS = {IS_NEGATED, IS_FAMILY, IS_HISTORICAL}

# type nào được phép có assertions / candidates
ASSERTABLE_TYPES = {CHAN_DOAN, THUOC, TRIEU_CHUNG}
CANDIDATE_TYPES = {CHAN_DOAN, THUOC}  # CHẨN_ĐOÁN→ICD-10, THUỐC→RxNorm


def make_concept(text, ctype, position, assertions=None, candidates=None):
    """Tạo 1 dict khái niệm đúng schema output."""
    obj = {
        "text": text,
        "type": ctype,
        "position": list(position),
    }
    if ctype in ASSERTABLE_TYPES:
        obj["assertions"] = list(assertions or [])
    else:
        obj["assertions"] = []
    if ctype in CANDIDATE_TYPES:
        obj["candidates"] = list(candidates or [])
    return obj
