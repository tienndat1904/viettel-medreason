"""Hybrid extractor: rule (nền, precision) + LLM (vét bệnh/thuốc LẠ, recall).

Vì sao thiết kế thế này (rút từ 2 lần LLM thua rule):
- LLM sinh tự do SAI BIÊN (chép cả câu/mệnh đề) -> phá WER. Nên LLM ở đây CHỈ được
  GỢI Ý cụm {text,type}; span cuối do resolve_offsets snap về đúng chữ trong văn bản.
- LLM chỉ bổ sung loại MANG CANDIDATE (CHẨN_ĐOÁN/THUỐC, trọng số 0.4) — nơi recall
  quý nhất và rule bó tay với bệnh lạ chưa có trong gazetteer.
- Rule đặt TRƯỚC trong list -> resolve_offsets đặt rule trước, span LLM nào ĐÈ rule
  sẽ tự bị bỏ (nền rule là floor, LLM không phá được).
- Lọc độ dài: bệnh/thuốc thật hiếm khi > ~6 từ -> chặn "chép cả câu".

Kết quả: rule giữ nguyên điểm sàn; LLM chỉ THÊM concept mới không đè -> cùng lắm
là nhiễu (đo A/B trên dev), không xoá được cái rule đã đúng.
"""
from __future__ import annotations

from schema import CHAN_DOAN, THUOC


def filter_llm_spans(llm_spans, allowed_types, max_words: int) -> list[dict]:
    """Giữ span LLM: đúng loại cho phép, không rỗng, ≤ max_words từ (chặn span cả câu)."""
    out, seen = [], set()
    for s in llm_spans:
        t = (s.get("text") or "").strip()
        typ = s.get("type")
        if typ not in allowed_types or not t:
            continue
        if len(t.split()) > max_words:
            continue
        key = (t.casefold(), typ)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": t, "type": typ})
    return out


class HybridExtractor:
    """extract(text) -> [{text,type}]: rule_spans + span LLM đã lọc (rule đứng trước)."""

    def __init__(self, rule_extract, llm_extract,
                 allowed_types=(CHAN_DOAN, THUOC), max_words: int = 6):
        self.rule_extract = rule_extract
        self.llm_extract = llm_extract
        self.allowed_types = tuple(allowed_types)
        self.max_words = max_words

    def extract(self, text: str) -> list[dict]:
        rule_spans = list(self.rule_extract(text))
        llm_spans = filter_llm_spans(self.llm_extract(text), self.allowed_types, self.max_words)
        return rule_spans + llm_spans      # rule TRƯỚC -> resolve_offsets ưu tiên rule
