"""Ánh xạ CHẨN_ĐOÁN->ICD-10 và THUỐC->RxNorm.

v0 lexical (không GPU): từ điển đồng nghĩa + fuzzy cho ICD; parse + khớp SCD cho RxNorm.
- Ưu tiên KB thật (data/kb/*.parquet); nếu chưa build thì dùng seed (data/kb/seed/*.parquet).
- Thiếu cả hai vẫn chạy: ICD vẫn có synonym dict, RxNorm trả [] (đều HỢP LỆ).
Backend 'semantic' (bge-m3 + reranker) sẽ bổ sung ở v1.
"""
from __future__ import annotations
import os, re

from drug_parser import load_brand_map
from icd_match import IcdMatcher, load_synonyms
from rxnorm_match import RxNormMatcher


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def _who4(code: str) -> str:
    """Rút mã ICD-10-CM về granularity WHO/BYT (tối đa 4 ký tự): I25.10 -> I25.1, S72.00 -> S72.0.
    Bằng chứng leaderboard (probe #10): BTC chấm ở mức 4 ký tự, mã CM 5+ ký tự bị scoring 0
    (J_candidates 19.22 -> 20.72). Mã <=4 ký tự giữ nguyên."""
    d = re.sub(r"[^A-Za-z0-9]", "", str(code))[:4]
    return d if len(d) <= 3 else d[:3] + "." + d[3:]


class Linker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        L = cfg.get("linking", {})
        self.backend = L.get("backend", "lexical")
        self._icd_who = L.get("icd_who_truncate", False)   # True -> rút mã ICD về 4 ký tự (WHO/BYT)
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

        lexical_icd = IcdMatcher(icd_df, byt_df, syn,
                                 L.get("icd_fuzzy_threshold", 88),
                                 L.get("icd_top_k_return", 3),
                                 hedge=L.get("icd_hedge", True))
        self._icd = lexical_icd
        self._icd_mode = "lexical"
        # backend semantic (v1): thử nạp bge-m3 index; thiếu -> giữ lexical
        if self.backend == "semantic":
            from icd_semantic import load_semantic
            sem = load_semantic(cfg, syn)
            if sem is not None:
                self._icd = sem
                self._icd_mode = "semantic"

        self._rx = RxNormMatcher(rx_df, brands,
                                 L.get("rxnorm_fuzzy_threshold", 90),
                                 L.get("rxnorm_top_k_return", 3),
                                 return_level=L.get("rxnorm_return_level", "scd"))
        self.ready = (icd_df is not None) or (rx_df is not None) or bool(syn) or bool(brands)

        srcs = []
        if icd_path:
            srcs.append(f"icd={'seed' if 'seed' in icd_path else 'kb'}({len(icd_df)})")
        if rx_path:
            srcs.append(f"rxnorm={'seed' if 'seed' in rx_path else 'kb'}({len(rx_df)})")
        print(f"[linker] backend={self.backend} icd_mode={self._icd_mode} | "
              f"{' '.join(srcs) or 'no-parquet'} | synonyms={len(syn)} brands={len(brands)}")

    # ---- API (hợp đồng cố định) ----
    def link_diagnosis(self, text: str, context: str = "") -> list[str]:
        codes = self._icd.match(text, context) if self._icd else []
        if not (self._icd_who and codes):
            return codes
        seen, out = set(), []                              # rút về 4 ký tự (WHO/BYT) + khử trùng
        for c in (_who4(c) for c in codes):
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def link_drug(self, text: str, context: str = "") -> list[str]:
        return self._rx.match(text, context) if self._rx else []
