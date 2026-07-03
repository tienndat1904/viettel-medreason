"""Suy luận assertion (isNegated / isFamily / isHistorical) cho khái niệm y tế.

Chạy SAU khi đã có offset ký tự [start, end] (không phụ thuộc extractor nào),
nên dùng chung cho cả rule baseline lẫn hậu xử lý output LLM.

Kỹ thuật (ConText-style cho tiếng Việt lâm sàng):
- isHistorical: state-machine theo section (Tiền sử / bệnh mạn tính / Thuốc trước
  khi nhập viện = quá khứ; Bệnh sử hiện tại / Đánh giá tại bệnh viện = hiện tại)
  + cue cục bộ quanh concept ('(trước đây)', 'cũ', 'mạn tính', 'tiền sử').
- isNegated: trigger phủ định trước concept trong cùng dòng, lan qua danh sách
  phân tách bằng dấu phẩy tới khi gặp '.', ';' hoặc 'nhưng'. Loại pseudo-negation
  'không đặc hiệu / không rõ / không xác định'.
- isFamily: danh từ người nhà trước concept (tránh 'ông ấy/bà ấy' = bệnh nhân).

API chính:
    detect(text, start, end, ctype) -> list[str]
    annotate(text, concepts, mode="union") -> concepts (đã điền 'assertions')
"""
from __future__ import annotations
import re
import unicodedata

from schema import ASSERTABLE_TYPES, IS_NEGATED, IS_FAMILY, IS_HISTORICAL

_ORDER = [IS_NEGATED, IS_FAMILY, IS_HISTORICAL]


def _sa(s: str) -> str:
    """strip accents + lower + đ→d — để so cue không lệ thuộc dấu tiếng Việt.
    (đ là CHỮ CÁI, không phải dấu; phải map thủ công, nếu không cue viết 'd' sẽ KHÔNG khớp 'đ'.)"""
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d")


# --- cue phân loại section (đã bỏ dấu) ---
_CUR_CUES = [
    "hien tai", "ly do nhap vien", "ly do kham", "dien bien", "benh su",
    "danh gia tai benh vien", "ket qua", "dac diem trieu chung",
    "dau hieu lam sang", "kham lam sang", "trieu chung khi nhap vien",
    "trieu chung chinh", "su kien truoc khi nhap vien", "cac su kien truoc",
    "tinh trang", "thu thuat da thuc hien", "xu tri", "thoi diem khoi phat",
]
_HIST_CUES = [
    "tien su", "man tinh", "benh ly man", "thuoc truoc khi nhap vien",
    "da dieu tri truoc", "cac benh da dieu tri", "dot tuong tu truoc",
    "cac dot tuong tu truoc", "benh noi khoa",
]

# --- cue phủ định (bỏ dấu) ---
_NEG_TRIGGERS = ["khong", "phu nhan", "am tinh", "loai tru", "chua ghi nhan",
                 "khong ghi nhan", "khong thay", "khong co", "khong con", " ko "]
# pseudo-negation sau 'khong' — KHÔNG phải phủ định concept (khớp cụm chính xác)
# 'khong dap ung/dung nap' = phủ định ĐÁP ỨNG/DUNG NẠP, thuốc phía sau VẪN hiện diện.
_NEG_PSEUDO = re.compile(
    r"khong\s+(thuoc\s+)?can quang|"
    r"khong\s+(dac hieu|ro rang|xac dinh|dang ke|dieu tri|gi bat thuong|"
    r"trieu chung khac|dap ung|dung nap)")
# ranh giới kết thúc scope phủ định. Thêm 'nen/chuyen sang/do' (hệ quả/tương phản)
# để 'không dung nạp X ... chuyển sang Y' KHÔNG lan phủ định tới Y.
_NEG_STOP = re.compile(r"[.;:]|nhung|tuy nhien|\bnen\b|chuyen sang")

# --- danh từ người nhà (GIỮ DẤU — tránh 'còn'->'con', 'bỏ'->'bố'…) ---
_FAMILY = ["vợ", "chồng", "bố", "mẹ", "cha", "con", "cháu", "anh trai",
           "chị gái", "em trai", "em gái", "ông nội", "bà nội", "ông ngoại",
           "bà ngoại", "gia đình", "người nhà", "họ hàng", "bố mẹ", "cha mẹ",
           "mẹ đẻ", "bố đẻ", "anh chị em"]
_FAMILY_RE = re.compile(r"(?<!\w)(" + "|".join(re.escape(f) for f in _FAMILY) + r")(?!\w)")

# cue lịch sử cục bộ quanh concept (bỏ dấu) — chỉ cue "quá khứ" rõ, KHÔNG dùng 'mạn tính'
# ('mạn tính' đã xử ở cấp section; dùng cục bộ gây FP với chẩn đoán hiện tại)
# 'tien su' có (?!...hien tai) để KHÔNG khớp header "Tiền sử bệnh HIỆN TẠI" (= mục hiện tại).
_LOCAL_HIST = re.compile(
    r"\(?\s*truoc day\s*\)?|\btien su\b(?!\s*(benh\s*)?hien tai)|\bcu\b|\btruoc kia\b")


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    ls = text.rfind("\n", 0, pos) + 1
    le = text.find("\n", pos)
    return ls, (le if le >= 0 else len(text))


def historical_intervals(text: str) -> list[tuple[int, int]]:
    """Trả các khoảng [s,e) thuộc ngữ cảnh quá khứ theo state-machine section."""
    intervals: list[tuple[int, int]] = []
    state = False           # mặc định: hiện tại
    off = 0
    for raw in text.splitlines(keepends=True):
        ls, le = off, off + len(raw)
        off = le
        stripped = raw.strip()
        low = _sa(stripped)
        is_bullet = stripped.startswith("-") or stripped.startswith("*")
        # dòng header (không phải bullet) mang tín hiệu section → đổi state
        if not is_bullet and low:
            if any(c in low for c in _CUR_CUES):
                state = False
            elif any(c in low for c in _HIST_CUES):
                state = True
        if state:
            intervals.append((ls, le))
    # gộp khoảng liền nhau
    merged: list[list[int]] = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


class AssertionTagger:
    """Gom tiền xử lý theo document (historical intervals) để tái dùng cho mọi concept."""

    def __init__(self, text: str):
        self.text = text
        self._hist = historical_intervals(text)

    def _in_hist_section(self, start: int) -> bool:
        return any(a <= start < b for a, b in self._hist)

    def detect(self, start: int, end: int, ctype: str) -> list[str]:
        if ctype not in ASSERTABLE_TYPES:
            return []
        text = self.text
        ls, le = _line_bounds(text, start)
        line = text[ls:le]
        rel = start - ls                      # vị trí concept trong dòng
        pre = _sa(line[:rel])                 # phần trước concept (bỏ dấu) — cho neg/hist
        pre_acc = line[:rel].lower()          # giữ dấu — cho family
        out = set()

        # --- isNegated ---
        trig_pos = -1
        for trig in _NEG_TRIGGERS:
            j = pre.rfind(trig.strip() if trig != " ko " else "ko")
            if j > trig_pos:
                # loại pseudo-negation (khớp cụm chính xác để không nuốt 'không rối loạn'):
                # 'không (thuốc) cản quang', 'không đặc hiệu/rõ ràng/xác định/đáng kể...'
                if trig.strip() == "khong" and _NEG_PSEUDO.match(pre[j:]):
                    continue
                trig_pos = j
        if trig_pos >= 0:
            between = pre[trig_pos:]
            if not _NEG_STOP.search(between):
                out.add(IS_NEGATED)

        # --- isFamily ---
        if _FAMILY_RE.search(pre_acc):
            out.add(IS_FAMILY)

        # --- isHistorical ---
        if self._in_hist_section(start):
            out.add(IS_HISTORICAL)
        else:
            window = _sa(text[max(0, start - 45):min(len(text), end + 15)])
            if _LOCAL_HIST.search(window):
                out.add(IS_HISTORICAL)

        return [a for a in _ORDER if a in out]


def detect(text: str, start: int, end: int, ctype: str) -> list[str]:
    """Tiện ích 1 concept (tạo tagger tạm)."""
    return AssertionTagger(text).detect(start, end, ctype)


def annotate(text: str, concepts: list[dict], mode: str = "union") -> list[dict]:
    """Điền 'assertions' cho list concept (đã có position).

    mode: 'replace' (ghi đè bằng luật) | 'union' (hợp luật + có sẵn) | 'fill' (chỉ điền khi trống).
    """
    tagger = AssertionTagger(text)
    for c in concepts:
        if c.get("type") not in ASSERTABLE_TYPES:
            c["assertions"] = []
            continue
        s, e = c["position"]
        rule = tagger.detect(s, e, c["type"])
        cur = [a for a in (c.get("assertions") or []) if a in _ORDER]
        if mode == "replace":
            merged = rule
        elif mode == "fill":
            merged = cur if cur else rule
        else:  # union
            merged = list(set(cur) | set(rule))
        c["assertions"] = [a for a in _ORDER if a in merged]
    return concepts
