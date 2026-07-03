"""Test module assertion (isNegated / isFamily / isHistorical).

Chạy: python tests/test_assertions.py   (hoặc pytest)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "extract"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from assertions import AssertionTagger  # noqa


def _assert(text, needle, ctype, expected, occ=0):
    i = -1
    for _ in range(occ + 1):
        i = text.find(needle, i + 1)
    assert i >= 0, f"không thấy {needle!r}"
    got = set(AssertionTagger(text).detect(i, i + len(needle), ctype))
    assert got == set(expected), f"{needle!r}: got={sorted(got)} expected={sorted(expected)}"
    print(f"  [PASS] {needle!r:34} -> {sorted(got)}")


def run():
    print("== isNegated ==")
    _assert("Các triệu chứng liên quan: Không có sốt, ớn lạnh, nôn, ho",
            "ho", "TRIỆU_CHỨNG", ["isNegated"])
    _assert("Phủ nhận đau ngực và khó thở", "đau ngực", "TRIỆU_CHỨNG", ["isNegated"])
    _assert("chụp ct ngực không thuốc cản quang cho thấy tim to, tràn dịch màng tim",
            "tràn dịch màng tim", "CHẨN_ĐOÁN", [])   # pseudo: 'không ... cản quang'
    _assert("tăng lipid máu, không đặc hiệu", "tăng lipid máu", "CHẨN_ĐOÁN", [])
    # issue #37: 'không đáp ứng với X' / 'không dung nạp ... chuyển sang Y' -> thuốc KHÔNG bị negate
    _assert("Sốt cao nhất là 102.9 không đáp ứng với tylenol và advil", "tylenol", "THUỐC", [])
    _assert("bệnh nhân không dung nạp amoxicillin nên được chuyển sang azithromycin",
            "azithromycin", "THUỐC", [])

    print("== isFamily ==")
    _assert("Vợ có các triệu chứng tương tự, được chẩn đoán là giãn phế quản",
            "giãn phế quản", "CHẨN_ĐOÁN", ["isFamily"])
    _assert("bệnh nhân còn cảm giác đánh trống ngực",   # 'còn' KHÔNG phải 'con'
            "đánh trống ngực", "TRIỆU_CHỨNG", [])

    print("== isHistorical ==")
    _assert("1. Tiền sử bệnh\n   Các bệnh lý mạn tính\n   - hen suyễn",
            "hen suyễn", "CHẨN_ĐOÁN", ["isHistorical"])
    _assert("2. Bệnh sử hiện tại\n   Triệu chứng hiện tại\n   - ho",
            "ho", "TRIỆU_CHỨNG", [])
    # issue #37: "Tiền sử bệnh HIỆN TẠI" là mục hiện tại -> KHÔNG historical
    _assert("2.  Tiền sử bệnh hiện tại\n    Lý do nhập viện: đau bụng",
            "đau bụng", "TRIỆU_CHỨNG", [])
    _assert("nhồi máu cơ tim vùng dưới cũ", "nhồi máu cơ tim vùng dưới cũ",
            "CHẨN_ĐOÁN", ["isHistorical"])

    print("== type không nhận assertion ==")
    _assert("wbc 11.6", "11.6", "KẾT_QUẢ_XÉT_NGHIỆM", [])

    print("\n✅ Tất cả test assertion PASS")


if __name__ == "__main__":
    run()
