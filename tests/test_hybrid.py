"""Test hybrid extractor: rule floor + LLM vét, lọc span, không phá rule."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "extract"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "offset"))

from hybrid import filter_llm_spans, HybridExtractor
from resolve_spans import resolve_offsets
from schema import CHAN_DOAN, THUOC


def test_filter_drops_long_and_wrong_type():
    spans = [
        {"text": "viêm tụy", "type": CHAN_DOAN},                       # giữ
        {"text": "a b c d e f g h", "type": CHAN_DOAN},                # 8 từ -> bỏ
        {"text": "đau bụng", "type": "TRIỆU_CHỨNG"},                    # khác loại -> bỏ
        {"text": "viêm tụy", "type": CHAN_DOAN},                        # trùng -> bỏ
        {"text": "  ", "type": THUOC},                                 # rỗng -> bỏ
    ]
    out = filter_llm_spans(spans, (CHAN_DOAN, THUOC), max_words=6)
    assert out == [{"text": "viêm tụy", "type": CHAN_DOAN}]


def test_llm_adds_unseen_disease_without_breaking_rule():
    text = "Chẩn đoán: bệnh Kawasaki thể không điển hình. Bệnh nhân sốt."

    def rule(t):
        return [{"text": "sốt", "type": "TRIỆU_CHỨNG"}]

    def llm(t):
        return [{"text": "bệnh Kawasaki", "type": CHAN_DOAN},
                {"text": "cả một câu dài dòng vượt quá sáu từ rõ ràng", "type": CHAN_DOAN}]

    H = HybridExtractor(rule, llm, allowed_types=(CHAN_DOAN,), max_words=6)
    concepts = resolve_offsets(text, H.extract(text))
    texts = {c["text"] for c in concepts}
    assert "bệnh Kawasaki" in texts       # LLM vét bệnh lạ
    assert "sốt" in texts                 # rule floor giữ nguyên
    assert not any(len(c["text"].split()) > 6 for c in concepts)  # không có span cả câu


def test_llm_cannot_override_rule_span():
    text = "viêm phổi nặng"

    def rule(t):
        return [{"text": "viêm phổi", "type": CHAN_DOAN}]

    def llm(t):  # đề xuất cụm đè lên rule -> phải bị bỏ (rule đứng trước)
        return [{"text": "viêm phổi nặng", "type": CHAN_DOAN}]

    H = HybridExtractor(rule, llm, allowed_types=(CHAN_DOAN,), max_words=6)
    concepts = resolve_offsets(text, H.extract(text))
    assert [c["text"] for c in concepts] == ["viêm phổi"]   # rule thắng, không đè


if __name__ == "__main__":
    test_filter_drops_long_and_wrong_type()
    test_llm_adds_unseen_disease_without_breaking_rule()
    test_llm_cannot_override_rule_span()
    print("OK: 3/3 test hybrid pass")
