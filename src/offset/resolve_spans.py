"""Gán vị trí ký tự [start, end] cho các span do extractor trả về.

QUAN TRỌNG: KHÔNG bao giờ tin offset do LLM sinh ra. LLM chỉ trả `text`,
module này tự dò offset trong input gốc:
  1) khớp exact, ưu tiên occurrence chưa dùng, quét trái→phải theo thứ tự;
  2) fallback: khớp linh hoạt (bỏ qua khác biệt khoảng trắng / hoa-thường / '**').
"""
from __future__ import annotations
import re


def _flexible_pattern(span: str) -> re.Pattern:
    """Regex khớp span cho phép khác biệt whitespace và ký tự '*' markdown."""
    span = span.strip().strip("*").strip()
    tokens = [re.escape(t) for t in span.split()]
    if not tokens:
        return re.compile(r"(?!x)x")  # không khớp gì
    pat = r"\**\s*".join(tokens)
    return re.compile(pat, re.IGNORECASE)


def resolve_offsets(text: str, spans: list[dict]) -> list[dict]:
    """Trả về danh sách concept có thêm khóa 'position'; bỏ span không tìm thấy."""
    used: list[tuple[int, int]] = []

    def overlaps(s, e):
        return any(not (e <= us or s >= ue) for us, ue in used)

    out = []
    for sp in spans:
        raw = (sp.get("text") or "").strip()
        if not raw:
            continue
        start = end = None

        # 1) exact match, occurrence chưa dùng, tính từ trái
        idx = 0
        while True:
            i = text.find(raw, idx)
            if i < 0:
                break
            if not overlaps(i, i + len(raw)):
                start, end = i, i + len(raw)
                break
            idx = i + 1

        # 2) fallback linh hoạt
        if start is None:
            pat = _flexible_pattern(raw)
            for m in pat.finditer(text):
                if not overlaps(m.start(), m.end()):
                    start, end = m.start(), m.end()
                    # cập nhật text về đúng chuỗi gốc trong input
                    raw = text[start:end]
                    break

        if start is None:
            continue  # không định vị được → bỏ (validator sẽ không nhận span thiếu vị trí)

        used.append((start, end))
        concept = dict(sp)
        concept["text"] = text[start:end]
        concept["position"] = [start, end]
        out.append(concept)

    # sắp theo vị trí xuất hiện cho gọn
    out.sort(key=lambda c: c["position"][0])
    return out
