"""Baseline trích xuất bằng luật (gazetteer + regex).

MỤC ĐÍCH: có submission HỢP LỆ #1 ngay và kiểm thử toàn bộ đường ống
(offset → assertion → linking → validate). Chất lượng thật sẽ do LLM extractor thay thế.
Trả về list {text, type} — assertion & position do module chuyên trách xử lý sau.
"""
from __future__ import annotations
import re

# --- Gazetteer tối giản (mở rộng dần) ---
SYMPTOMS = [
    "khó thở", "đau ngực", "đau bụng", "đau đầu", "buồn nôn", "nôn", "sốt",
    "ho", "tiêu chảy", "táo bón", "chóng mặt", "mệt mỏi", "đánh trống ngực",
    "ngất xỉu", "phù", "khò khè", "tiếng rít", "ớn lạnh", "vã mồ hôi",
    "đau thượng vị", "ợ hơi", "khó chịu", "ảo giác", "đờm",
]
LAB_NAMES = [
    "wbc", "ast", "alt", "troponin", "cea", "creatinine", "cr", "bilirubin",
    "spo2", "canxi", "canci", "canx", "hgb", "hct", "plt", "neut", "lyph",
    "bạch cầu", "phosphatase kiềm", "bilirubin toàn phần",
]

_num = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*%|\s*[a-zA-Z/]+)?")


def extract(text: str) -> list[dict]:
    low = text.lower()
    found = []

    # triệu chứng
    for kw in SYMPTOMS:
        for m in re.finditer(re.escape(kw), low):
            found.append({"text": text[m.start():m.end()], "type": "TRIỆU_CHỨNG"})

    # tên xét nghiệm
    for kw in LAB_NAMES:
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", low):
            found.append({"text": text[m.start():m.end()], "type": "TÊN_XÉT_NGHIỆM",
                          "assertions": []})

    # kết quả xét nghiệm (số) — chỉ lấy số đứng gần từ khóa xét nghiệm/kết quả
    for m in _num.finditer(text):
        ctx = low[max(0, m.start() - 25):m.start()]
        if any(k in ctx for k in ["là ", "wbc", "troponin", "canxi", "ast",
                                   "alt", "cr ", "cea", ": ", "spo2", "bilirubin"]):
            found.append({"text": text[m.start():m.end()],
                          "type": "KẾT_QUẢ_XÉT_NGHIỆM", "assertions": []})

    return found
