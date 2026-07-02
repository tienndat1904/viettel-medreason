"""Ánh xạ CHẨN_ĐOÁN->ICD-10 và THUỐC->RxNorm.

v0 lexical (không GPU): từ điển đồng nghĩa + fuzzy cho ICD; parse + khớp SCD cho RxNorm.
- Ưu tiên KB thật (data/kb/*.parquet); nếu chưa build thì dùng seed (data/kb/seed/*.parquet).
- Thiếu cả hai vẫn chạy: ICD vẫn có synonym dict, RxNorm trả [] (đều HỢP LỆ).
Backend 'semantic' (bge-m3 + reranker) sẽ bổ sung ở v1.
"""
from __future__ import annotations
import os

from drug_parser import load_brand_map
from icd_match import IcdMatcher, load_synonyms
from rxnorm_match import RxNormMatcher


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


class Linker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        L = cfg.get("linking", {})
        self.backend = L.get("backend", "lexical")
        self._icd = None
        self._rx = None
        self.ready = False
        self._load(cfg, L)

    def _load(self, cfg, L):
        import pandas as pd
        paths = cfg["paths"]
        icd_path = _first_existing(paths.get("kb_icd"), paths.get("kb_icd_seed"))
        byt_path = _first_existing(paths.get("kb_icd_byt"))
        rx_path = _first_existing(paths.get("kb_rxnorm"), paths.get("kb_rxnorm_seed"))
        icd_df = pd.read_parquet(icd_path) if icd_path else None
        byt_df = pd.read_parquet(byt_path) if byt_path else None
        rx_df = pd.read_parquet(rx_path) if rx_path else None

        syn = load_synonyms(L.get("icd_synonyms", "data/kb/synonyms/icd_synonyms.tsv"))
        # brand map: auto (từ RRF) làm nền, dict thủ công đè lên (ưu tiên hơn)
        brands = load_brand_map(L.get("drug_brands_auto", "data/kb/synonyms/drug_brands_auto.tsv"))
        brands.update(load_brand_map(L.get("drug_brands", "data/kb/synonyms/drug_brands.tsv")))

        self._icd = IcdMatcher(icd_df, byt_df, syn,
                               L.get("icd_fuzzy_threshold", 88),
                               L.get("icd_top_k_return", 3))
        self._rx = RxNormMatcher(rx_df, brands,
                                 L.get("rxnorm_fuzzy_threshold", 90),
                                 L.get("rxnorm_top_k_return", 3))
        self.ready = (icd_df is not None) or (rx_df is not None) or bool(syn) or bool(brands)

        srcs = []
        if icd_path:
            srcs.append(f"icd={'seed' if 'seed' in icd_path else 'kb'}({len(icd_df)})")
        if rx_path:
            srcs.append(f"rxnorm={'seed' if 'seed' in rx_path else 'kb'}({len(rx_df)})")
        print(f"[linker] backend={self.backend} | {' '.join(srcs) or 'no-parquet'} "
              f"| synonyms={len(syn)} brands={len(brands)}")
        if self.backend == "semantic":
            print("[linker] backend=semantic chưa triển khai (v1) — tạm dùng lexical.")

    # ---- API (hợp đồng cố định) ----
    def link_diagnosis(self, text: str, context: str = "") -> list[str]:
        return self._icd.match(text, context) if self._icd else []

    def link_drug(self, text: str, context: str = "") -> list[str]:
        return self._rx.match(text, context) if self._rx else []
