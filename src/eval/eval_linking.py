"""Đo riêng LINKING (P2) trên dev gold — độc lập extraction (P1).

Nạp mention CHẨN_ĐOÁN/THUỐC trong data/dev/gold → chạy Linker → so candidates gold.

Chấm theo **JACCARD** (đúng metric BTC: candidates = |gt∩pred|/|gt∪pred|):
  → tối ưu = trả ĐÚNG tập mã, KHÔNG thừa (trả nhiều mã sai làm union to → Jaccard giảm).

Gold RxNorm theo nguyên tắc "mã ở mức cụ thể nhất mention hỗ trợ":
  SCD (hoạt chất+hàm lượng+dạng) · SCDC (hoạt chất+hàm lượng, dạng mơ hồ) · IN (thuốc trần).
Quy tắc cho linker: trả mã ĐÚNG MỨC mention hỗ trợ (thuốc trần → IN; có liều+dạng → SCD).

In 2 cột mỗi loại:
  - exact  = Jaccard mã đầy đủ  → CHÍNH LÀ điểm candidates đóng góp.
  - chuẩn hóa = ICD nhóm 3 ký tự / RxNorm hoạt chất → "trần" nếu chỉ lệch độ sâu/mức mã.

Dùng:
  python src/eval/eval_linking.py
  python src/eval/eval_linking.py --misses-out data/dev/linking_misses.tsv
"""
from __future__ import annotations
import os, sys, json, glob, argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ["", "linking", "eval"]:
    p = os.path.join(SRC, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import yaml
from schema import CHAN_DOAN, THUOC


def load_cfg(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def jaccard(a: set, b: set) -> float:
    """Đúng metric BTC: cả 2 rỗng -> 1; đúng 1 rỗng -> 0; còn lại |∩|/|∪|."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _icd_pref(codes, n=3):
    def norm(c):
        return "".join(ch for ch in str(c).upper() if ch.isalnum())[:n]
    return {norm(c) for c in codes if norm(c)}


def _ings(codes, ing_map):
    return {ing_map[c] for c in codes if c in ing_map}


def eval_group(rows, name, norm_label, norm_fn):
    """In Jaccard exact + Jaccard chuẩn hóa (norm_fn: (gold,pred)->(setG,setP))."""
    n = len(rows)
    with_gold = [r for r in rows if r["gold"]]
    with_pred = [r for r in rows if r["pred"]]
    print(f"\n=== {name} ===")
    print(f"  mention: {n} | có mã gold: {len(with_gold)} | linker trả ≥1 mã: {len(with_pred)}"
          + (f" (coverage={len(with_pred)/n:.2f})" if n else ""))
    if not with_gold:
        print("  (chưa có mã gold để chấm)")
        return with_gold
    je = sum(jaccard(set(r["gold"]), set(r["pred"])) for r in with_gold) / len(with_gold)
    jn = sum(jaccard(*norm_fn(r["gold"], r["pred"])) for r in with_gold) / len(with_gold)
    print(f"  Jaccard exact       = {je:.3f}   (= điểm candidates đóng góp)")
    print(f"  Jaccard {norm_label:11}= {jn:.3f}   (trần nếu chỉ lệch độ sâu/mức mã)")
    return with_gold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--gold", default="data/dev/gold")
    ap.add_argument("--input", default="data/test/input")
    ap.add_argument("--misses-out", default="")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    from linker import Linker
    linker = Linker(cfg)

    ing_map = {}
    try:
        import pandas as pd
        p = cfg["paths"].get("kb_rxnorm") or cfg["paths"].get("kb_rxnorm_seed")
        if p and os.path.exists(p):
            kb = pd.read_parquet(p)
            for rc, ing in zip(kb["rxcui"].astype(str), kb["ingredient"].astype(str)):
                if ing:
                    ing_map[rc] = ing.lower()
    except Exception as e:  # noqa
        print(f"(không nạp được ingredient map: {e})")

    icd_rows, rx_rows = [], []
    for fp in sorted(glob.glob(os.path.join(args.gold, "*.json"))):
        name = os.path.splitext(os.path.basename(fp))[0]
        gold = json.load(open(fp, encoding="utf-8"))
        tp = os.path.join(args.input, f"{name}.txt")
        ctx = open(tp, encoding="utf-8").read() if os.path.exists(tp) else ""
        for c in gold:
            if c["type"] == CHAN_DOAN:
                icd_rows.append({"file": name, "text": c["text"],
                                 "gold": c.get("candidates", []),
                                 "pred": linker.link_diagnosis(c["text"], ctx)})
            elif c["type"] == THUOC:
                rx_rows.append({"file": name, "text": c["text"],
                                "gold": c.get("candidates", []),
                                "pred": linker.link_drug(c["text"], ctx)})

    eval_group(icd_rows, "ICD-10 (CHẨN_ĐOÁN)", "nhóm3",
               lambda g, p: (_icd_pref(g), _icd_pref(p)))
    eval_group(rx_rows, "RxNorm (THUỐC)", "hoạt chất",
               lambda g, p: (_ings(g, ing_map), _ings(p, ing_map)))

    misses = []
    for kind, rows in [("ICD", icd_rows), ("RX", rx_rows)]:
        for r in rows:
            if r["gold"] and jaccard(set(r["gold"]), set(r["pred"])) < 1.0:
                misses.append((kind, r["file"], r["text"], ",".join(r["gold"]),
                               ",".join(r["pred"]) or "-"))
    if misses:
        print(f"\n=== MISS ({len(misses)}) — Jaccard exact < 1 (thiếu mã đúng hoặc trả thừa) ===")
        for kind, f, t, g, p in misses[:40]:
            print(f"  [{kind}] {f}: {t!r}  gold={g}  pred={p}")
    if args.misses_out and misses:
        with open(args.misses_out, "w", encoding="utf-8") as fo:
            fo.write("kind\tfile\ttext\tgold\tpred\n")
            for row in misses:
                fo.write("\t".join(row) + "\n")
        print(f"\n📝 MISS -> {args.misses_out}")

    rx_missing = sum(1 for r in rx_rows if not r["gold"])
    if rx_missing:
        print(f"\n⚠️  {rx_missing}/{len(rx_rows)} mention THUỐC để [] "
              "(combo / có liều nhưng không có mã sạch / hoạt chất mơ hồ).")
    print("Gold RxNorm mức 'cụ thể nhất mention hỗ trợ' (SCD/SCDC/IN). Linker nên trả ĐÚNG mức đó: "
          "thuốc trần → IN, có liều+dạng → SCD. 'hoạt chất' = chẩn đoán sai-thực-thể.")


if __name__ == "__main__":
    main()
