"""T4 — Ma trận quyết định cho tuning linking (thr × k) trên dev gold.

Vì chưa biết BTC chấm candidate kiểu gì, script này in ĐỒNG THỜI:
  - hit@k  : tỉ lệ gold nằm trong pred (recall — có lợi khi trả nhiều mã)
  - avg_len: số mã trung bình trả về/mention (proxy precision — càng thấp càng "sạch")
để khi có điểm leaderboard chỉ việc tra bảng chọn cấu hình.

ICD in cả 3 mức exact/cat4/cat3 (khớp cách chấm phân cấp của eval_linking).
RxNorm chấm theo hoạt chất.

Dùng:
  python src/eval/sweep_linking.py                       # full grid mặc định
  python src/eval/sweep_linking.py --icd-thr 85,88,92 --icd-k 3,4,5
  python src/eval/sweep_linking.py --rx-thr 85,90,95 --rx-k 1,2,3
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

# helper tự chứa (không phụ thuộc internals của eval_linking để khỏi vỡ khi P3 đổi file)
_ICD_LEVELS = {"exact": 99, "cat4": 4, "cat3": 3}


def _icd_norm(code: str) -> str:
    return "".join(ch for ch in str(code).upper() if ch.isalnum())


def _icd_prefixes(codes, n):
    return {_icd_norm(c)[:n] for c in codes if _icd_norm(c)}


def _icd_match(golds, preds, n):
    return bool(_icd_prefixes(golds, n) & _icd_prefixes(preds, n))


def _ings(codes, ing_map):
    return {ing_map[c] for c in codes if c in ing_map}


def _ing_match(golds, preds, ing_map):
    gi, pi = _ings(golds, ing_map), _ings(preds, ing_map)
    return any(g and p and (g in p or p in g) for g in gi for p in pi)


def _jaccard(gold, pred, norm=lambda x: x):
    """Jaccard tập mã ĐẦY ĐỦ — đúng metric candidate của BTC (New_info.md §Metric)."""
    g = {norm(c) for c in gold if norm(c)}
    p = {norm(c) for c in pred if norm(c)}
    if not g and not p:
        return 1.0
    if not g or not p:
        return 0.0
    return len(g & p) / len(g | p)


def load_cfg(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _first_existing(*paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


def load_gold_mentions(gold_dir, input_dir):
    """-> (icd_mentions, rx_mentions): mỗi item = {text, context, gold}."""
    icd, rx = [], []
    for fp in sorted(glob.glob(os.path.join(gold_dir, "*.json"))):
        name = os.path.splitext(os.path.basename(fp))[0]
        gold = json.load(open(fp, encoding="utf-8"))
        tp = os.path.join(input_dir, f"{name}.txt")
        ctx = open(tp, encoding="utf-8").read() if os.path.exists(tp) else ""
        for c in gold:
            item = {"text": c["text"], "context": ctx, "gold": c.get("candidates", [])}
            if c["type"] == CHAN_DOAN:
                icd.append(item)
            elif c["type"] == THUOC:
                rx.append(item)
    return icd, rx


def _parse_list(s, cast):
    return [cast(x) for x in s.split(",") if x.strip()]


def sweep_icd(mentions, cm_df, byt_df, syn, thrs, ks):
    from icd_match import IcdMatcher
    with_gold = [m for m in mentions if m["gold"]]
    ng = len(with_gold)
    n_multi = sum(1 for m in with_gold if len(set(m["gold"])) > 1)
    print(f"\n=== ICD (CHẨN_ĐOÁN, n_gold={ng}; {n_multi} có >1 mã gold) ===")
    print("  Jaccard = metric BTC (mã đầy đủ). hit@k/exact chỉ để tham khảo.")
    print(f"  {'hedge':>5} {'thr':>4} {'k':>2} | {'JACCARD':>8} | {'exact':>6} {'cat3':>6} | {'avg_len':>7}")
    for hedge in (False, True):
        for thr in thrs:
            matcher = IcdMatcher(cm_df, byt_df, syn, thr, max(ks), hedge=hedge)
            preds = [matcher.match(m["text"], m["context"]) for m in with_gold]
            for k in ks:
                pk = [p[:k] for p in preds]
                jac = sum(_jaccard(m["gold"], p, _icd_norm) for m, p in zip(with_gold, pk)) / ng
                ex = sum(1 for m, p in zip(with_gold, pk) if _icd_match(m["gold"], p, 99)) / ng
                c3 = sum(1 for m, p in zip(with_gold, pk) if _icd_match(m["gold"], p, 3)) / ng
                avg_len = sum(len(p) for p in pk) / ng
                print(f"  {str(hedge):>5} {thr:>4} {k:>2} | {jac:>8.3f} | "
                      f"{ex:>6.3f} {c3:>6.3f} | {avg_len:>7.2f}")


def sweep_rxnorm(mentions, rx_df, brands, ing_map, thrs, ks):
    from rxnorm_match import RxNormMatcher
    with_gold = [m for m in mentions if m["gold"]]
    ng = len(with_gold)
    print(f"\n=== RxNorm (THUỐC, n_gold={ng}) ===")
    print("  JACCARD = metric BTC (mã RxNorm đầy đủ). hit_ing = hit theo hoạt chất (lenient, tham khảo).")
    print(f"  {'thr':>4} {'k':>2} | {'JACCARD':>8} | {'hit_ing':>7} | {'avg_len':>7}")
    for thr in thrs:
        matcher = RxNormMatcher(rx_df, brands, thr, max(ks))
        preds = [matcher.match(m["text"], m["context"]) for m in with_gold]
        for k in ks:
            pk = [p[:k] for p in preds]
            jac = sum(_jaccard(m["gold"], p, lambda x: str(x).strip())
                      for m, p in zip(with_gold, pk)) / ng
            hit = sum(1 for m, p in zip(with_gold, pk) if _ing_match(m["gold"], p, ing_map)) / ng
            avg_len = sum(len(p) for p in pk) / ng
            print(f"  {thr:>4} {k:>2} | {jac:>8.3f} | {hit:>7.3f} | {avg_len:>7.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--gold", default="data/dev/gold")
    ap.add_argument("--input", default="data/test/input")
    ap.add_argument("--icd-thr", default="85,88,92")
    ap.add_argument("--icd-k", default="3,4,5")
    ap.add_argument("--rx-thr", default="85,90,95")
    ap.add_argument("--rx-k", default="1,2,3")
    ap.add_argument("--skip-icd", action="store_true")
    ap.add_argument("--skip-rx", action="store_true")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    import pandas as pd
    from icd_match import load_synonyms
    from drug_parser import load_brand_map
    paths = cfg["paths"]
    L = cfg.get("linking", {})

    icd_mentions, rx_mentions = load_gold_mentions(args.gold, args.input)

    if not args.skip_icd:
        cm_df = pd.read_parquet(_first_existing(paths.get("kb_icd"), paths.get("kb_icd_seed")))
        byt_p = _first_existing(paths.get("kb_icd_byt"))
        byt_df = pd.read_parquet(byt_p) if byt_p else None
        syn = load_synonyms(L.get("icd_synonyms", "data/kb/synonyms/icd_synonyms.tsv"))
        sweep_icd(icd_mentions, cm_df, byt_df, syn,
                  _parse_list(args.icd_thr, int), _parse_list(args.icd_k, int))

    if not args.skip_rx:
        rx_p = _first_existing(paths.get("kb_rxnorm"), paths.get("kb_rxnorm_seed"))
        rx_df = pd.read_parquet(rx_p)
        brands = load_brand_map(L.get("drug_brands_auto", "data/kb/synonyms/drug_brands_auto.tsv"))
        brands.update(load_brand_map(L.get("drug_brands", "data/kb/synonyms/drug_brands.tsv")))
        ing_map = {}
        for rc, ing in zip(rx_df["rxcui"].astype(str), rx_df["ingredient"].astype(str)):
            if ing:
                ing_map[rc] = ing.lower()
        sweep_rxnorm(rx_mentions, rx_df, brands, ing_map,
                     _parse_list(args.rx_thr, int), _parse_list(args.rx_k, int))


if __name__ == "__main__":
    main()
