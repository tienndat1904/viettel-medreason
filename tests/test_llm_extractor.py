"""Test logic LLM extractor (chunking + parse + gộp) và tích hợp pipeline —
dùng MOCK generate_fn nên KHÔNG cần GPU/model.

Chạy: python tests/test_llm_extractor.py  (hoặc pytest)
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ["", "extract", "linking", "offset", "postprocess"]:
    sys.path.insert(0, os.path.join(ROOT, "src", sub))

from llm_extractor import LLMExtractor  # noqa
from chunking import chunk_document      # noqa


# --- MOCK: trả JSON dựa trên vài từ khóa có trong chunk (giả lập LLM) ---
GAZ = [("ho", "TRIỆU_CHỨNG"), ("sốt", "TRIỆU_CHỨNG"), ("khó thở", "TRIỆU_CHỨNG"),
       ("viêm phổi", "CHẨN_ĐOÁN"), ("wbc", "TÊN_XÉT_NGHIỆM"), ("aspirin", "THUỐC")]


def mock_generate(chunk_text: str) -> str:
    low = chunk_text.lower()
    items = [{"text": kw, "type": t} for kw, t in GAZ if kw in low]
    # cố tình bọc thinking + code fence để thử parser bền vững
    return "<think>ok</think>\n```json\n" + json.dumps(items, ensure_ascii=False) + "\n```"


def test_chunking():
    text = "".join(f"dòng {i} nội dung y khoa\n" for i in range(200))
    chunks = chunk_document(text, max_chars=500)
    assert len(chunks) > 1, "phải chia thành nhiều chunk"
    # offset đầu chunk phải khớp vị trí thật trong text
    for off, ch in chunks:
        assert text[off:off + len(ch)] == ch, "offset chunk sai"
    # ghép lại đủ, không mất ký tự
    assert sum(len(c) for _, c in chunks) == len(text)
    print(f"  [PASS] chunking: {len(chunks)} chunk, offset khớp, không mất ký tự")


def test_extract_mock():
    ex = LLMExtractor(generate_fn=mock_generate, max_chunk_chars=60)
    text = ("Bệnh nhân ho và sốt, được chẩn đoán viêm phổi.\n"
            "Xét nghiệm wbc tăng.\nĐiều trị aspirin.\n")
    spans = ex.extract(text)
    got = {(s["text"], s["type"]) for s in spans}
    for kw, t in [("ho", "TRIỆU_CHỨNG"), ("sốt", "TRIỆU_CHỨNG"),
                  ("viêm phổi", "CHẨN_ĐOÁN"), ("wbc", "TÊN_XÉT_NGHIỆM"),
                  ("aspirin", "THUỐC")]:
        assert (kw, t) in got, f"thiếu {kw}"
    assert all("assertions" not in s and "position" not in s for s in spans), \
        "extractor chỉ trả text+type"
    print(f"  [PASS] extract mock: {len(spans)} span, đúng text+type")


def test_pipeline_integration():
    """Chạy process_file với extractor mock: offset + assertion + validate."""
    import pipeline
    cfg = pipeline.load_cfg(os.path.join(ROOT, "configs", "config.yaml"))

    class _NoLink:
        def link_diagnosis(self, *a): return []
        def link_drug(self, *a): return []

    ex = LLMExtractor(generate_fn=mock_generate, max_chunk_chars=200)
    text = "Tiền sử bệnh\n- viêm phổi\n2. Bệnh sử hiện tại\nKhông có ho, sốt.\n"
    concepts = pipeline.process_file(text, ex.extract, _NoLink(), assertion_mode="union")
    # mọi concept phải có position hợp lệ + JSON serialize được
    for c in concepts:
        s, e = c["position"]
        assert 0 <= s < e <= len(text) and text[s:e] == c["text"]
    json.dumps(concepts, ensure_ascii=False)
    by = {c["text"]: c for c in concepts}
    assert "isHistorical" in by["viêm phổi"]["assertions"], "viêm phổi phải isHistorical"
    assert "isNegated" in by["ho"]["assertions"], "ho phải isNegated"
    assert "isNegated" in by["sốt"]["assertions"], "sốt phải isNegated"
    print(f"  [PASS] pipeline tích hợp: {len(concepts)} concept, offset+assertion đúng")


def run():
    print("== LLM extractor (mock, không cần GPU) ==")
    test_chunking()
    test_extract_mock()
    test_pipeline_integration()
    print("\n✅ Tất cả test LLM extractor PASS")


if __name__ == "__main__":
    run()
