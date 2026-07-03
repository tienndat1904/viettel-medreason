"""Dọn output sau khi đã có position — giảm concept rác làm hại metric.

Trọng tâm: 1 cụm text KHÔNG được gán 2 type khác nhau (metric phạt KÉP:
đoán đúng text nhưng sai type -> tạo concept thừa, 0 điểm cả 3 metric).
=> Với các concept CÙNG text (chuẩn hoá) nhưng KHÁC type, chỉ giữ MỘT type
(type xuất hiện nhiều nhất; hoà thì lấy type của occurrence sớm nhất).
Giữ nguyên nhiều occurrence CÙNG type (hợp lệ: 'sốt' xuất hiện 2 lần).
"""
from __future__ import annotations
from collections import defaultdict


def _norm(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def resolve_type_conflicts(concepts: list[dict]) -> list[dict]:
    """Trả list concept đã bỏ các bản gán sai type cho cùng 1 cụm."""
    by_text: dict[str, list[dict]] = defaultdict(list)
    for c in concepts:
        by_text[_norm(c.get("text", ""))].append(c)

    keep = []
    for _, group in by_text.items():
        types = {c["type"] for c in group}
        if len(types) <= 1:
            keep.extend(group)
            continue
        # có xung đột type -> chọn type ưu thế
        cnt = defaultdict(int)
        for c in group:
            cnt[c["type"]] += 1
        earliest = min(group, key=lambda c: (c.get("position") or [0])[0])["type"]
        best = max(types, key=lambda t: (cnt[t], t == earliest))
        keep.extend(c for c in group if c["type"] == best)
    keep.sort(key=lambda c: (c.get("position") or [0])[0])
    return keep
