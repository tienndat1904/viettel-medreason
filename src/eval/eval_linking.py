"""Đo riêng LINKING (P2) trên dev gold — độc lập với extraction (P1).

Nạp các mention CHẨN_ĐOÁN/THUỐC trong data/dev/gold → chạy Linker của P2
(link_diagnosis/link_drug) với ngữ cảnh là văn bản gốc → so với candidates gold.

Chấm (theo LINKING_PLAN.md §7):
  - RxNorm: theo HOẠT CHẤT (map pred SCD→ingredient) — lenient, đúng tinh thần "tìm đúng thuốc".
  - ICD: PHÂN CẤP (issue #13) — in cả 3 mức để thấy trần điểm & mức "đúng nhóm bệnh":
      exact = trùng mã đầy đủ | cat4 = trùng 4 ký tự đầu | cat3 = trùng nhóm 3 ký tự (I48, K72…)
    Gold ICD trộn độ sâu (3/4/5 ký tự) là bình thường — chấm tiền tố tránh phạt oan khác độ sâu.
  - hit@k = tỉ lệ gold khớp pred (trong mention CÓ mã gold); top1 = chỉ xét mã pred đầu.

Dùng:
  python src/eval/eval_linking.py                          # in ICD cả 3 mức + RxNorm
  python src/eval/eval_linking.py --icd-level cat3         # MISS list chấm theo nhóm 3 ký tự
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

_ICD_LEVELS = {"exact": 99, "cat4": 4, "cat3": 3}


def load_cfg(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def prf(hit, npred_has, ngold_has):
    """precision = hit / (mention có pred & có gold); recall = hit / (mention có gold)."""
    p = hit / npred_has if npred_has else 0.0
    r = hit / ngold_has if ngold_has else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


# ---- RxNorm: khớp theo hoạt chất ----
def _ings(codes, ing_map):
    return {ing_map[c] for c in codes if c in ing_map}


def _ing_match(golds, preds, ing_map):
    gi, pi = _ings(golds, ing_map), _ings(preds, ing_map)
    return any(g and p and (g in p or p in g) for g in gi for p in pi)


# ---- ICD: khớp theo tiền tố (issue #13) ----
def _icd_norm(code: str) -> str:
    """'I48.91' -> 'I4891' (bỏ dấu chấm/space, in hoa)."""
    return "".join(ch for ch in str(code).upper() if ch.isalnum())


def _icd_prefixes(codes, n):
    return {_icd_norm(c)[:n] for c in codes if _icd_norm(c)}


def _icd_match(golds, preds, n):
    return bool(_icd_prefixes(golds, n) & _icd_prefixes(preds, n))


def _counts(rows):
    n = len(rows)
    with_gold = [r for r in rows if r["gold"]]
    with_pred = [r for r in rows if r["pred"]]
    return n, with_gold, with_pred


def eval_rxnorm(rows, ing_map):
    n, with_gold, with_pred = _counts(rows)
    print("\n=== RxNorm (THUỐC) — chấm theo HOẠT CHẤT ===")
    print(f"  mention: {n} | có mã gold: {len(with_gold)} | linker trả ≥1 mã: {len(with_pred)}"
          + (f" (coverage={len(with_pred)/n:.2f})" if n else ""))
    if not with_gold:
        print("  (chưa có mã gold — điền candidates vào data/dev/labels/*.json)")
        return
    hit = sum(1 for r in with_gold if _ing_match(r["gold"], r["pred"], ing_map))
    top1 = sum(1 for r in with_gold if r["pred"] and _ing_match(r["gold"], r["pred"][:1], ing_map))
    both = sum(1 for r in with_gold if r["pred"])
    p, r_, f = prf(hit, both, len(with_gold))
    print(f"  hit@k (hoạt chất): {hit}/{len(with_gold)} = {hit/len(with_gold):.3f}")
    print(f"  top1: {top1}/{len(with_gold)} = {top1/len(with_gold):.3f}")
    print(f"  precision(mention có pred+gold)={p:.3f} recall={r_:.3f} F1={f:.3f}")


def eval_icd(rows):
    """In hit@k/top1 ở cả 3 mức exact/cat4/cat3."""
    n, with_gold, with_pred = _counts(rows)
    print("\n=== ICD-10 (CHẨN_ĐOÁN) — chấm phân cấp ===")
    print(f"  mention: {n} | có mã gold: {len(with_gold)} | linker trả ≥1 mã: {len(with_pred)}"
          + (f" (coverage={len(with_pred)/n:.2f})" if n else ""))
    if not with_gold:
        print("  (chưa có mã gold để chấm)")
        return
    ng = len(with_gold)
    for lvl, nn in _ICD_LEVELS.items():
        hit = sum(1 for r in with_gold if _icd_match(r["gold"], r["pred"], nn))
        top1 = sum(1 for r in with_gold if r["pred"] and _icd_match(r["gold"], r["pred"][:1], nn))
        tag = {"exact": "trùng mã đầy đủ", "cat4": "4 ký tự", "cat3": "nhóm 3 ký tự"}[lvl]
        print(f"  [{lvl:5}] hit@k={hit}/{ng}={hit/ng:.3f}  top1={top1/ng:.3f}   ({tag})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--gold", default="data/dev/gold")
    ap.add_argument("--input", default="data/test/input")
    ap.add_argument("--icd-level", default="exact", choices=list(_ICD_LEVELS),
                    help="mức chấm ICD dùng cho danh sách MISS (exact|cat4|cat3)")
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

    eval_icd(icd_rows)
    eval_rxnorm(rx_rows, ing_map)

    # danh sách MISS — ICD theo --icd-level, RxNorm theo hoạt chất
    nn = _ICD_LEVELS[args.icd_level]
    misses = []
    for r in icd_rows:
        if r["gold"] and not _icd_match(r["gold"], r["pred"], nn):
            misses.append(("ICD", r["file"], r["text"], ",".join(r["gold"]),
                           ",".join(r["pred"]) or "-"))
    for r in rx_rows:
        if r["gold"] and not _ing_match(r["gold"], r["pred"], ing_map):
            misses.append(("RX", r["file"], r["text"], ",".join(r["gold"]),
                           ",".join(r["pred"]) or "-"))
    if misses:
        print(f"\n=== MISS ({len(misses)}) — ICD@{args.icd_level} + RxNorm@hoạt chất ===")
        for kind, f, t, g, p in misses[:40]:
            print(f"  [{kind}] {f}: {t!r}  gold={g}  pred={p}")
    if args.misses_out and misses:
        with open(args.misses_out, "w", encoding="utf-8") as fo:
            fo.write("kind\tfile\ttext\tgold\tpred\n")
            for row in misses:
                fo.write("\t".join(row) + "\n")
        print(f"\n📝 MISS -> {args.misses_out}")

    rx_missing_gold = sum(1 for r in rx_rows if not r["gold"])
    if rx_missing_gold:
        print(f"\n⚠️  {rx_missing_gold}/{len(rx_rows)} mention THUỐC chưa có mã RxNorm gold.")


if __name__ == "__main__":
    main()
