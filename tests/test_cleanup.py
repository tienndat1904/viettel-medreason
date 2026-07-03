"""Test resolve_type_conflicts: cùng text khác type -> giữ 1 type; cùng type nhiều occ -> giữ."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "postprocess"))
from cleanup import resolve_type_conflicts  # noqa


def run():
    # 'đau hạ vị' bị gán 2 type -> giữ type ưu thế (TRIỆU_CHỨNG, 2 vs 1)
    cs = [
        {"text": "đau hạ vị", "type": "TRIỆU_CHỨNG", "position": [10, 19]},
        {"text": "Đau hạ vị", "type": "TRIỆU_CHỨNG", "position": [50, 59]},
        {"text": "đau hạ vị", "type": "CHẨN_ĐOÁN", "position": [80, 89]},
        {"text": "sốt", "type": "TRIỆU_CHỨNG", "position": [5, 8]},
        {"text": "sốt", "type": "TRIỆU_CHỨNG", "position": [30, 33]},  # 2 occ cùng type -> giữ cả 2
        {"text": "viêm phổi", "type": "CHẨN_ĐOÁN", "position": [100, 109]},
    ]
    out = resolve_type_conflicts(cs)
    types_dhv = [c["type"] for c in out if c["text"].casefold() == "đau hạ vị"]
    assert types_dhv == ["TRIỆU_CHỨNG", "TRIỆU_CHỨNG"], types_dhv  # bỏ bản CHẨN_ĐOÁN
    assert sum(1 for c in out if c["text"] == "sốt") == 2, "phải giữ 2 occ 'sốt'"
    assert any(c["text"] == "viêm phổi" for c in out)
    assert out == sorted(out, key=lambda c: c["position"][0]), "phải sắp theo position"
    print("  [PASS] type-conflict: bỏ CHẨN_ĐOÁN của 'đau hạ vị', giữ 2 'sốt', giữ 'viêm phổi'")

    # hoà số lượng -> lấy type của occurrence sớm nhất
    cs2 = [
        {"text": "x", "type": "CHẨN_ĐOÁN", "position": [5, 6]},
        {"text": "x", "type": "TRIỆU_CHỨNG", "position": [20, 21]},
    ]
    out2 = resolve_type_conflicts(cs2)
    assert {c["type"] for c in out2} == {"CHẨN_ĐOÁN"}, out2  # sớm nhất = CHẨN_ĐOÁN
    print("  [PASS] hoà -> lấy type occurrence sớm nhất")
    print("\n✅ Tất cả test cleanup PASS")


if __name__ == "__main__":
    run()
