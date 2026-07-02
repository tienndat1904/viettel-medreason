"""Đo riêng LINKING (P2) trên dev gold — độc lập với extraction (P1).

Nạp các mention CHẨN_ĐOÁN/THUỐC trong data/dev/gold → chạy Linker của P2
(link_diagnosis/link_drug) với ngữ cảnh là văn bản gốc → so với candidates gold.

Chỉ số (theo LINKING_PLAN.md §7):
  - hit@k = tỉ lệ 'gold ∈ pred' (trong các mention CÓ mã gold)
  - top1  = tỉ lệ mã đầu tiên pred == 1 mã gold
  - coverage = tỉ lệ mention linker trả về ≥1 mã (kể cả khi gold trống)
Tách riêng ICD (CHẨN_ĐOÁN) và RxNorm (THUỐC); in danh sách MISS để P2 sửa.

Dùng:
  python src/eval/eval_linking.py                      # toàn bộ dev
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


def prf(hit, npred_has, ngold_has):
    """precision = hit / (mention có pred & có gold); recall = hit / (mention có gold)."""
    p = hit / npred_has if npred_has else 0.0
    r = hit / ngold_has if ngold_has else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def _ings(codes, ing_map):
    """Tập hoạt chất (lower) của list mã, bỏ mã không có trong KB."""
    return {ing_map[c] for c in codes if c in ing_map}


def _ing_match(golds, preds, ing_map):
    """True nếu có hoạt chất gold trùng hoạt chất pred (substring 2 chiều)."""
    gi, pi = _ings(golds, ing_map), _ings(preds, ing_map)
    return any(g and p and (g in p or p in g) for g in gi for p in pi)


def eval_group(rows, name, ing_map=None):
    """rows = list dict(file,text,gold(list),pred(list)).
    ing_map != None -> chấm theo HOẠT CHẤT (RxNorm); else exact mã (ICD)."""
    if ing_map is not None:
        def is_hit(g, p):
            return _ing_match(g, p, ing_map)

        def is_top1(g, p):
            return bool(p) and _ing_match(g, p[:1], ing_map)
    else:
        def is_hit(g, p):
            return bool(set(g) & set(p))

        def is_top1(g, p):
            return bool(p) and p[0] in set(g)

    n = len(rows)
    with_gold = [r for r in rows if r["gold"]]
    with_pred = [r for r in rows if r["pred"]]
    hit = sum(1 for r in with_gold if is_hit(r["gold"], r["pred"]))
    top1 = sum(1 for r in with_gold if is_top1(r["gold"], r["pred"]))
    # precision-ish chỉ tính trên mention có cả gold lẫn pred
    both = [r for r in with_gold if r["pred"]]
    p, r_, f = prf(hit, len(both), len(with_gold))
    print(f"\n=== {name} ===")
    print(f"  mention: {n} | có mã gold: {len(with_gold)} | linker trả ≥1 mã: {len(with_pred)} "
          f"(coverage={len(with_pred)/n:.2f})" if n else f"  {name}: 0 mention")
    lvl = "hoạt chất" if ing_map is not None else "gold∈pred"
    if with_gold:
        print(f"  hit@k ({lvl}): {hit}/{len(with_gold)} = {hit/len(with_gold):.3f}")
        print(f"  top1: {top1}/{len(with_gold)} = {top1/len(with_gold):.3f}")
        print(f"  precision(trên mention có pred+gold)={p:.3f} recall={r_:.3f} F1={f:.3f}")
    else:
        print(f"  (chưa có mã gold để chấm — điền candidates vào data/dev/labels/*.json)")
    return with_gold, with_pred


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

    # map rxcui(str) -> ingredient(lower) để chấm RxNorm theo hoạt chất
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
                pred = linker.link_diagnosis(c["text"], ctx)
                icd_rows.append({"file": name, "text": c["text"],
                                 "gold": c.get("candidates", []), "pred": pred})
            elif c["type"] == THUOC:
                pred = linker.link_drug(c["text"], ctx)
                rx_rows.append({"file": name, "text": c["text"],
                                "gold": c.get("candidates", []), "pred": pred})

    icd_g, _ = eval_group(icd_rows, "ICD-10 (CHẨN_ĐOÁN)")
    rx_g, _ = eval_group(rx_rows, "RxNorm (THUỐC) — chấm theo HOẠT CHẤT", ing_map)

    # danh sách MISS (có mã gold nhưng linker không trúng) — để P2 sửa
    misses = []
    for grp, kind, imap in [(icd_g, "ICD", None), (rx_g, "RX", ing_map)]:
        for r in grp:
            miss = (not _ing_match(r["gold"], r["pred"], imap)) if imap is not None \
                else (not set(r["gold"]) & set(r["pred"]))
            if miss:
                misses.append((kind, r["file"], r["text"], ",".join(r["gold"]),
                               ",".join(r["pred"]) or "-"))
    if misses:
        print(f"\n=== MISS ({len(misses)}) — gold có mã nhưng linker không trúng ===")
        for kind, f, t, g, p in misses[:40]:
            print(f"  [{kind}] {f}: {t!r}  gold={g}  pred={p}")
    if args.misses_out and misses:
        with open(args.misses_out, "w", encoding="utf-8") as fo:
            fo.write("kind\tfile\ttext\tgold\tpred\n")
            for row in misses:
                fo.write("\t".join(row) + "\n")
        print(f"\n📝 MISS -> {args.misses_out}")

    # nhắc điền RxNorm gold nếu còn trống
    rx_missing_gold = sum(1 for r in rx_rows if not r["gold"])
    if rx_missing_gold:
        print(f"\n⚠️  {rx_missing_gold}/{len(rx_rows)} mention THUỐC chưa có mã RxNorm gold "
              f"-> chưa chấm được hit RxNorm. Cần điền candidates trong data/dev/labels/*.json.")


if __name__ == "__main__":
    main()
