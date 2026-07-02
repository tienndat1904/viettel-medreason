"""Chuyển seed TSV -> parquet để Linker chạy v0 ngay (trước khi có KB thật).

Đầu ra (được commit, dung lượng nhỏ):
  data/kb/seed/icd10_vn.parquet     <- data/kb/seed/icd10_seed.tsv
  data/kb/seed/rxnorm_scd.parquet   <- data/kb/seed/rxnorm_seed.tsv

Chạy: python src/kb/build_seed_kb.py
"""
from __future__ import annotations
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEED = os.path.join(ROOT, "data", "kb", "seed")


def _read_tsv(path):
    return pd.read_csv(path, sep="\t", dtype=str, comment="#").fillna("")


def main():
    icd = _read_tsv(os.path.join(SEED, "icd10_seed.tsv"))
    rx = _read_tsv(os.path.join(SEED, "rxnorm_seed.tsv"))

    assert list(icd.columns[:2]) == ["code", "name_vi"], f"ICD cột lạ: {list(icd.columns)}"
    assert {"rxcui", "ingredient", "strength"} <= set(rx.columns), f"RxNorm cột lạ: {list(rx.columns)}"

    icd_out = os.path.join(SEED, "icd10_vn.parquet")
    rx_out = os.path.join(SEED, "rxnorm_scd.parquet")
    icd.to_parquet(icd_out, index=False)
    rx.to_parquet(rx_out, index=False)
    print(f"[seed] ICD-10: {len(icd)} mã -> {icd_out}")
    print(f"[seed] RxNorm: {len(rx)} dòng -> {rx_out}")


if __name__ == "__main__":
    main()
