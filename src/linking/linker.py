"""Ánh xạ CHẨN_ĐOÁN→ICD-10 và THUỐC→RxNorm.

Skeleton: nếu chưa có KB index thì trả candidates rỗng (vẫn HỢP LỆ).
Khi đã build index (src/kb/*), Linker dùng bge-m3 retrieve + bge-reranker rerank.
"""
from __future__ import annotations
import os
from drug_parser import parse_drug


class Linker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.ready = False
        self._embedder = None
        self._reranker = None
        self._icd = None      # DataFrame: code, name, ... + faiss
        self._rxnorm = None
        self._try_load()

    def _try_load(self):
        icd_path = self.cfg["paths"]["kb_icd"]
        rx_path = self.cfg["paths"]["kb_rxnorm"]
        if not (os.path.exists(icd_path) and os.path.exists(rx_path)):
            return  # chưa build KB → no-op linker
        try:
            import pandas as pd
            self._icd = pd.read_parquet(icd_path)
            self._rxnorm = pd.read_parquet(rx_path)
            from FlagEmbedding import BGEM3FlagModel, FlagReranker
            self._embedder = BGEM3FlagModel(self.cfg["linking"]["embed_model"],
                                            use_fp16=True)
            self._reranker = FlagReranker(self.cfg["linking"]["reranker_model"],
                                          use_fp16=True)
            self.ready = True
        except Exception as e:  # thiếu package / index → no-op
            print(f"[linker] chưa sẵn sàng ({e}); trả candidates rỗng.")

    # ---- API ----
    def link_diagnosis(self, text: str, context: str = "") -> list[str]:
        if not self.ready:
            return []
        return self._link_icd(text, context)

    def link_drug(self, text: str, context: str = "") -> list[str]:
        if not self.ready:
            return []
        return self._link_rxnorm(text)

    # ---- nội bộ (điền khi có KB) ----
    def _link_icd(self, text, context):
        # TODO: bge-m3 retrieve top_k → rerank → lọc theo min_confidence
        raise NotImplementedError

    def _link_rxnorm(self, text):
        # TODO: parse hoạt chất+hàm lượng+dạng → khớp RxNorm SCD
        _ = parse_drug(text)
        raise NotImplementedError
