"""Baseline trích xuất bằng luật (gazetteer + regex).

MỤC ĐÍCH: có submission HỢP LỆ #1 ngay và kiểm thử toàn bộ đường ống
(offset → linking → validate). Chất lượng thật sẽ do LLM extractor thay thế.
Trả về list {text, type, assertions} — CHƯA có position (offset resolver lo).
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

# cue phủ định / người nhà / tiền sử
NEG_CUES = ["không", "phủ nhận", "âm tính", "chưa"]
FAMILY_CUES = ["vợ", "chồng", "bố", "mẹ", "cha", "con", "cháu", "anh trai",
               "chị gái", "gia đình", "người nhà", "họ hàng"]
HIST_HEADER_CUES = ["tiền sử", "thuốc trước khi nhập viện", "bệnh lý mạn",
                    "bệnh lý mãn", "mạn tính", "mãn tính", "trước đây",
                    "các bệnh đã điều trị"]

_num = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?(?:\s*%|\s*[a-zA-Z/]+)?")


def _historical_regions(text: str) -> list[tuple[int, int]]:
    """Vùng ký tự thuộc mục tiền sử / thuốc trước nhập viện → isHistorical."""
    regions = []
    lines = text.splitlines(keepends=True)
    pos = 0
    active_end = 0
    for ln in lines:
        low = ln.lower()
        start = pos
        pos += len(ln)
        # header lớn (mục 2/3) tắt chế độ historical
        if re.match(r"\s*[23]\s*\.", ln):
            active_end = 0
        if any(cue in low for cue in HIST_HEADER_CUES):
            active_end = max(active_end, pos + 1200)  # áp cho khối kế tiếp
        if start < active_end:
            regions.append((start, pos))
    return regions


def _in_regions(i, regions):
    return any(a <= i < b for a, b in regions)


def _assertions_for(text, start, hist_regions):
    """Suy assertion từ ngữ cảnh cục bộ quanh vị trí start."""
    a = []
    # xét cửa sổ 40 ký tự trước concept trong cùng dòng
    line_start = text.rfind("\n", 0, start) + 1
    ctx = text[max(line_start, start - 40):start].lower()
    if any(c in ctx for c in NEG_CUES):
        a.append("isNegated")
    if any(c in ctx for c in FAMILY_CUES):
        a.append("isFamily")
    if _in_regions(start, hist_regions):
        a.append("isHistorical")
    return a


def extract(text: str) -> list[dict]:
    low = text.lower()
    hist = _historical_regions(text)
    found = []

    # triệu chứng
    for kw in SYMPTOMS:
        for m in re.finditer(re.escape(kw), low):
            found.append({"text": text[m.start():m.end()], "type": "TRIỆU_CHỨNG",
                          "assertions": _assertions_for(text, m.start(), hist)})

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
