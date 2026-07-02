"""Chấm offline trên dev set có nhãn. In F1 span+type, và độ chính xác assertion/candidate.

Dùng: python src/eval/scorer.py --pred output --gold data/dev/gold
(mỗi thư mục chứa N.json cùng tên file)

LƯU Ý: công thức chấm chính thức của BTC chưa rõ — scorer hỗ trợ 2 chế độ match
span (exact | overlap) để dò gần đúng. Cập nhật khi có rubric.
"""
from __future__ import annotations
import os, sys, json, argparse, glob
from collections import defaultdict

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load(d):
    out = {}
    for fp in glob.glob(os.path.join(d, "*.json")):
        name = os.path.splitext(os.path.basename(fp))[0]
        with open(fp, "r", encoding="utf-8") as f:
            out[name] = json.load(f)
    return out


def span_match(p, g, mode):
    if p["type"] != g["type"]:
        return False
    ps, pe = p["position"]; gs, ge = g["position"]
    if mode == "exact":
        return ps == gs and pe == ge
    return not (pe <= gs or ps >= ge)  # overlap


def match_file(preds, golds, mode):
    """Greedy match; trả (tp, matched_pairs, n_pred, n_gold)."""
    used = set()
    pairs = []
    for gi, g in enumerate(golds):
        for pi, p in enumerate(preds):
            if pi in used:
                continue
            if span_match(p, g, mode):
                used.add(pi); pairs.append((p, g)); break
    return len(pairs), pairs, len(preds), len(golds)


def prf(tp, npred, ngold):
    p = tp / npred if npred else 0.0
    r = tp / ngold if ngold else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--mode", default="overlap", choices=["exact", "overlap"])
    args = ap.parse_args()

    preds, golds = load(args.pred), load(args.gold)
    TP = NP = NG = 0
    a_ok = a_tot = c_ok = c_tot = 0
    per_type = defaultdict(lambda: [0, 0, 0])  # tp, npred, ngold

    for name, gold in golds.items():
        pred = preds.get(name, [])
        tp, pairs, npred, ngold = match_file(pred, gold, args.mode)
        TP += tp; NP += npred; NG += ngold
        for g in gold:
            per_type[g["type"]][2] += 1
        for p in pred:
            per_type[p["type"]][1] += 1
        for p, g in pairs:
            per_type[g["type"]][0] += 1
            # assertion: khớp tập
            if g["type"] in {"CHẨN_ĐOÁN", "THUỐC", "TRIỆU_CHỨNG"}:
                a_tot += 1
                if set(p.get("assertions", [])) == set(g.get("assertions", [])):
                    a_ok += 1
            # candidate: gold code nằm trong pred list (recall@k)
            if g["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
                c_tot += 1
                gc = set(g.get("candidates", []))
                pc = set(p.get("candidates", []))
                if gc and gc & pc:
                    c_ok += 1

    p, r, f = prf(TP, NP, NG)
    print(f"\n=== SPAN+TYPE (mode={args.mode}) ===")
    print(f"P={p:.3f}  R={r:.3f}  F1={f:.3f}   (TP={TP} nPred={NP} nGold={NG})")
    print("\n=== theo type (F1) ===")
    for t, (tp, np_, ng) in sorted(per_type.items()):
        _, _, ff = prf(tp, np_, ng)
        print(f"  {t:<20} F1={ff:.3f}  (tp={tp} pred={np_} gold={ng})")
    if a_tot:
        print(f"\nAssertion exact-set acc = {a_ok/a_tot:.3f} ({a_ok}/{a_tot})")
    if c_tot:
        print(f"Candidate hit (gold∈pred) = {c_ok/c_tot:.3f} ({c_ok}/{c_tot})")


if __name__ == "__main__":
    main()
