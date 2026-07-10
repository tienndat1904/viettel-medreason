"""Gán vị trí ký tự [start, end] cho các span do extractor trả về.

QUAN TRỌNG: KHÔNG bao giờ tin offset do LLM sinh ra. LLM chỉ trả `text`,
module này tự dò offset trong input gốc:
  1) khớp exact, MỌI occurrence chưa dùng, quét trái→phải theo thứ tự;
  2) fallback: khớp linh hoạt (bỏ qua khác biệt khoảng trắng / hoa-thường / '**').

MỖI occurrence (mỗi lần xuất hiện) sinh 1 concept riêng với position riêng —
BTC yêu cầu trích MỌI lần xuất hiện. Đường LLM dedup {text,type} về 1 mention;
expand ở đây để không mất occurrence lặp. Đường rule vốn emit N span cho N
occurrence: span đầu đã "nuốt" hết occurrence, các span sau tìm thấy đều 'used'
-> KHÔNG nhân đôi. Assertion tính lại per-position ở annotate() nên vẫn đúng.

Chỉ nhận match có RANH GIỚI TỪ (ký tự kề không phải chữ-số) để span ngắn
('ho', 'sốt') không nổ substring ('hoặc', 'sốt ruột'...).
"""
from __future__ import annotations
import re

_MAX_OCC = 100   # cap occurrence/1 span: concept thật lặp 2-5 lần; cap chống file bệnh lý (16k từ 1 dòng)


def _flexible_pattern(span: str) -> re.Pattern:
    """Regex khớp span cho phép khác biệt whitespace và ký tự '*' markdown."""
    span = span.strip().strip("*").strip()
    tokens = [re.escape(t) for t in span.split()]
    if not tokens:
        return re.compile(r"(?!x)x")  # không khớp gì
    pat = r"\**\s*".join(tokens)
    return re.compile(pat, re.IGNORECASE)


def _word_bounded(text: str, s: int, e: int) -> bool:
    """True nếu [s,e] không dính vào chữ-số kề bên (tránh khớp substring giữa từ)."""
    before_ok = s == 0 or not text[s - 1].isalnum()
    after_ok = e >= len(text) or not text[e].isalnum()
    return before_ok and after_ok


def resolve_offsets(text: str, spans: list[dict]) -> list[dict]:
    """Trả về danh sách concept có thêm khóa 'position'; bỏ span không tìm thấy.

    Mỗi occurrence chưa dùng của một span -> 1 concept (giữ MỌI lần xuất hiện)."""
    used: list[tuple[int, int]] = []

    def overlaps(s, e):
        return any(not (e <= us or s >= ue) for us, ue in used)

    def _emit(sp, out, s, e):
        used.append((s, e))
        concept = dict(sp)
        concept["text"] = text[s:e]
        concept["position"] = [s, e]
        out.append(concept)

    # DEDUP span theo (text_chuẩn, type) trước khi expand: extractor rule emit N span
    # trùng text cho N occurrence; nếu xử lý từng span sẽ quét lại toàn bộ occurrence
    # N lần -> O(n^3), treo trên file bất thường. Expand đã lấy MỌI occurrence rồi nên
    # xử lý 1 lần/text là đủ và cho kết quả y hệt.
    seen_key = set()
    uniq = []
    for sp in spans:
        raw = (sp.get("text") or "").strip()
        if not raw:
            continue
        key = (raw, sp.get("type"))   # case-SENSITIVE: exact find bên dưới cũng phân biệt hoa/thường
        #                               (dedup casefold sẽ nuốt mất occurrence khác hoa/thường)
        if key in seen_key:
            continue
        seen_key.add(key)
        uniq.append(sp)

    # LONGEST-MATCH cross-type: span DÀI chiếm vị trí trước (stable theo thứ tự emit khi
    # bằng độ dài) -> cụm bệnh dài ("tăng kali máu") thắng term ngắn chồng vị trí ("kali"
    # =TÊN_XÉT_NGHIỆM), sửa lỗi sai-type/sai-biên mà emit-order không xử được.
    uniq.sort(key=lambda sp: len((sp.get("text") or "").strip()), reverse=True)

    out = []
    for sp in uniq:
        raw = (sp.get("text") or "").strip()

        # 1) exact match — MỌI occurrence chưa dùng, có ranh giới từ (cap chống file bệnh lý)
        n = 0
        idx = 0
        while n < _MAX_OCC:
            i = text.find(raw, idx)
            if i < 0:
                break
            j = i + len(raw)
            if _word_bounded(text, i, j) and not overlaps(i, j):
                _emit(sp, out, i, j)
                n += 1
            idx = i + 1

        # 2) fallback linh hoạt — chỉ khi KHÔNG có exact nào; cũng lấy mọi occurrence
        if n == 0:
            for m in _flexible_pattern(raw).finditer(text):
                if n >= _MAX_OCC:
                    break
                if _word_bounded(text, m.start(), m.end()) and not overlaps(m.start(), m.end()):
                    _emit(sp, out, m.start(), m.end())
                    n += 1

        # không định vị được -> bỏ (validator sẽ không nhận span thiếu vị trí)

    # sắp theo vị trí xuất hiện cho gọn
    out.sort(key=lambda c: c["position"][0])
    return out
