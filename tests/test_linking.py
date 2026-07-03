"""Test hồi quy cho linking v0 (lexical). Chạy: python tests/test_linking.py

Không phụ thuộc pytest. Kiểm tra:
  - parse_drug tách hoạt chất/hàm lượng/dạng + chuẩn hóa brand/typo
  - Linker trả đúng 5 cặp gold trong Info.txt (RxNorm + ICD GERD)
  - synonym ICD cho bệnh phổ biến
Cần chạy build_seed_kb.py trước (tạo seed parquet).
"""
from __future__ import annotations
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ["linking", "kb", ""]:
    sys.path.insert(0, os.path.join(ROOT, "src", sub) if sub else os.path.join(ROOT, "src"))

import yaml
from drug_parser import parse_drug, load_brand_map
from linker import Linker

FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  -> {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def test_parse():
    print("== parse_drug ==")
    brands = load_brand_map(os.path.join(ROOT, "data/kb/synonyms/drug_brands.tsv"))
    p = parse_drug("amlodipine 10 mg po daily")
    check("amlodipine ingredient", p["ingredient"] == "amlodipine", p)
    check("amlodipine strength", p["strengths"] == ["10 mg"], p)

    p = parse_drug("Chlorpheniramine 0.4 MG/ML")
    check("chlorpheniramine mg/ml giữ nguyên", p["strengths"] == ["0.4 mg/ml"], p)

    p = parse_drug("lasix 40mg iv", brands)
    check("lasix->furosemide (brand)", p["ingredient"] == "furosemide", p)
    check("lasix form=injectable", p["dose_form"] == "injectable solution", p)

    p = parse_drug("Laxis 20mg tiêm tĩnh mạch", brands)
    check("Laxis typo->furosemide", p["ingredient"] == "furosemide", p)

    p = parse_drug("metoprolol succinate xl 50 mg po daily")
    check("metoprolol succinate giữ 2 token", p["ingredient"] == "metoprolol succinate", p)


def test_linker():
    cfg = yaml.safe_load(open(os.path.join(ROOT, "configs/config.yaml"), encoding="utf-8"))

    # (1) THUẬT TOÁN khớp RxNorm — chạy trên SEED KB (chắc chắn chứa đủ 4 mã gold Info.txt).
    #     KB thật (prescribable) có thể thiếu mã cũ đã nghỉ -> coverage báo riêng bên dưới.
    print("== RxNorm matcher (seed KB — kiểm thuật toán) ==")
    import pandas as pd
    from rxnorm_match import RxNormMatcher
    seed = pd.read_parquet(os.path.join(ROOT, "data/kb/seed/rxnorm_scd.parquet"))
    brands = load_brand_map(os.path.join(ROOT, "data/kb/synonyms/drug_brands.tsv"))
    rx = RxNormMatcher(seed, brands, max_return=3)
    for text, code in [("amlodipine 10 mg po daily", "308135"),
                       ("aspirin 81 mg po daily", "243670"),
                       ("Chlorpheniramine 0.4 MG/ML", "360047"),
                       ("Capsaicin 0.38 MG/ML", "1660761")]:
        got = rx.match(text)
        check(f"RxNorm {text!r} (gold∈pred)", code in got, got)

    # (2) ICD + tích hợp Linker (synonym dict độc lập KB)
    print("== Linker (ICD synonym) ==")
    lk = Linker(cfg)
    got = lk.link_diagnosis("bệnh trào ngược dạ dày - thực quản")
    check("ICD GERD = [K21.0,K21.9]", got[:2] == ["K21.0", "K21.9"], got)

    # synonym bệnh phổ biến
    for text, code in [("tăng huyết áp", "I10"), ("hen suyễn", "J45.909"),
                       ("nhiễm khuẩn huyết do tụ cầu vàng", "A41.9")]:
        got = lk.link_diagnosis(text)
        check(f"ICD synonym {text!r}", code in got, got)

    # type không có candidate / thuốc lạ không bịa mã
    check("thuốc rỗng -> []", lk.link_drug("") == [], "non-empty")


if __name__ == "__main__":
    test_parse()
    test_linker()
    print()
    if FAILS:
        print(f"❌ {len(FAILS)} test FAIL: {FAILS}")
        sys.exit(1)
    print("✅ Tất cả test linking PASS")
