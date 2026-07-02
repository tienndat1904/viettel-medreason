"""Tách tên thuốc thành hoạt chất + hàm lượng + dạng, bỏ route/tần suất.

Ví dụ: "metoprolol 25mg po bid" -> ingredient='metoprolol', strength='25 mg'
        "aspirin 325mg x 1"     -> ingredient='aspirin', strength='325 mg'
Mục tiêu khớp RxNorm ở mức SCD (ingredient+strength+doseform).
"""
from __future__ import annotations
import re

# route / tần suất / cách dùng cần loại bỏ
NOISE = {
    "po", "iv", "im", "sc", "sl", "pr", "bid", "tid", "qid", "qd", "od",
    "daily", "prn", "q4h", "q6h", "q8h", "q12h", "nebs", "neb", "xl", "er",
    "sr", "cr", "hằng", "ngày", "uống", "tiêm", "ngậm", "dưới", "lưỡi",
    "mỗi", "lần", "viên", "x",
}
_STRENGTH = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mg|mcg|g|ml|mg/ml|mcg/ml|%|iu|unit|đơn vị)",
    re.IGNORECASE)


def parse_drug(text: str) -> dict:
    t = text.strip()
    strengths = [f"{m.group(1).replace(',', '.')} {m.group(2).lower()}"
                 for m in _STRENGTH.finditer(t)]
    # bỏ phần hàm lượng khỏi chuỗi để lấy tên
    name = _STRENGTH.sub(" ", t)
    tokens = re.split(r"[\s,()/]+", name)
    ingr = [tok for tok in tokens
            if tok and tok.lower() not in NOISE and not tok.isdigit()]
    return {
        "raw": text,
        "ingredient": " ".join(ingr).strip(" -"),
        "strengths": strengths,
    }
