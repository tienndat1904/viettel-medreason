"""Bộ chấm theo METRIC CHÍNH THỨC của BTC (thay cho span-F1).

final_score = 0.3*text_score + 0.3*assertions_score + 0.4*candidates_score

- text_score       = mean_i (1 - WER(i))        # WER trên trường text của sample i
- assertions_score = mean_i J_assert(i)          # trung bình Jaccard assertion mỗi concept
- candidates_score = (∑_i J_cand(i)*W_i) / (∑_i W_i),  W_i = ∑_{k gold} (len(gt_cand(k))+1)
- Jaccard: both empty -> 1 ; gt rỗng & pred khác rỗng -> 0 ; còn lại |∩|/|∪|
- Sai TYPE (text đúng, type sai): concept bị đếm 2 lần (1 gold + 1 pred), mỗi lần 0 điểm.

GIẢ ĐỊNH (BTC chưa cho script chấm — có thể lệch, chỉnh khi có bản chính thức):
1. Match concept pred<->gold theo (text_chuẩn_hóa, type), greedy theo thứ tự position;
   text_chuẩn_hóa = gộp khoảng trắng + casefold. Concept không match -> tính là 1 đơn vị điểm 0.
2. WER(i): ref = nối text các concept GOLD (thứ tự position), hyp = nối text PRED; WER theo TỪ.
3. J_assert = trung bình Jaccard trên concept loại {bệnh,thuốc,triệu chứng};
   J_cand = trung bình trên {bệnh,thuốc} (matched: Jaccard; unmatched: 0).
   Concept loại khác bị LOẠI khỏi trung bình (không có 2 trường này) — nếu tính sẽ
   cho Jaccard(∅,∅)=1 và thổi phồng điểm. *Giả định; chỉnh nếu bản BTC tính khác.*

Dùng: python src/eval/official_scorer.py --pred <dir> --gold <dir>
"""
from __future__ import annotations
import os, sys, json, argparse, glob
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schema import ASSERTABLE_TYPES, CANDIDATE_TYPES  # noqa


def _norm(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def load(d):
    out = {}
    for fp in glob.glob(os.path.join(d, "*.json")):
        name = os.path.splitext(os.path.basename(fp))[0]
        try:
            out[name] = json.load(open(fp, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            out[name] = []      # JSON hỏng -> coi như rỗng (đúng tinh thần "0 điểm")
    return out


def wer(ref: list[str], hyp: list[str]) -> float:
    """Word Error Rate = (S+D+I)/len(ref). ref rỗng: 0 nếu hyp rỗng, else 1."""
    if not ref:
        return 0.0 if not hyp else 1.0
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, m + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1,          # deletion
                        dp[j - 1] + 1,      # insertion
                        prev + (ref[i - 1] != hyp[j - 1]))  # sub/match
            prev = cur
    return dp[m] / n


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _order(concepts):
    return sorted(concepts, key=lambda c: (c.get("position") or [0])[0])


def match(gold, pred):
    """Greedy match theo (norm text, type). Trả list đơn vị: (g_concept|None, p_concept|None)."""
    units = []
    used = set()
    pred_ord = _order(pred)
    for g in _order(gold):
        key = (_norm(g.get("text", "")), g.get("type"))
        hit = None
        for idx, p in enumerate(pred_ord):
            if idx in used:
                continue
            if (_norm(p.get("text", "")), p.get("type")) == key:
                hit = idx; used.add(idx); break
        units.append((g, pred_ord[hit] if hit is not None else None))
    for idx, p in enumerate(pred_ord):   # pred thừa (không match gold)
        if idx not in used:
            units.append((None, p))
    return units


def score_file(gold, pred):
    # --- text WER ---
    ref_words, hyp_words = [], []
    for c in _order(gold):
        ref_words += (c.get("text", "")).split()
    for c in _order(pred):
        hyp_words += (c.get("text", "")).split()
    w = wer([x.casefold() for x in ref_words], [x.casefold() for x in hyp_words])

    # --- assertion / candidate Jaccard theo đơn vị concept ---
    # CHỈ tính assertions cho {bệnh, thuốc, triệu chứng}; candidates cho {bệnh, thuốc}
    # (theo metric BTC). Concept loại khác KHÔNG có 2 trường này -> loại khỏi trung bình,
    # nếu không sẽ cho Jaccard(∅,∅)=1 -> thổi phồng điểm (nhất là candidates).
    units = match(gold, pred)
    a_vals, c_vals = [], []
    W = 0
    for g, p in units:
        typ = (g or p).get("type")
        if typ in ASSERTABLE_TYPES:
            if g is None or p is None:  # concept không khớp -> 0 điểm
                a_vals.append(0.0)
            else:
                a_vals.append(jaccard(set(g.get("assertions", []) or []),
                                      set(p.get("assertions", []) or [])))
        if typ in CANDIDATE_TYPES:
            gC = set(g.get("candidates", []) or []) if g else set()
            pC = set(p.get("candidates", []) or []) if p else set()
            if g is None or p is None:
                c_vals.append(0.0)
            else:
                c_vals.append(jaccard(gC, pC))
            if g is not None:
                W += len(gC) + 1        # trọng số = ∑ (len(gt_cand)+1) trên gold DX/THUỐC
    j_assert = sum(a_vals) / len(a_vals) if a_vals else 1.0
    j_cand = sum(c_vals) / len(c_vals) if c_vals else 1.0
    return {"wer": w, "text": 1 - w, "j_assert": j_assert, "j_cand": j_cand, "W": W}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    gold, pred = load(args.gold), load(args.pred)

    text_sum, assert_sum, n = 0.0, 0.0, 0
    cand_num, cand_den = 0.0, 0.0
    for name, g in gold.items():
        r = score_file(g, pred.get(name, []))
        text_sum += r["text"]; assert_sum += r["j_assert"]; n += 1
        cand_num += r["j_cand"] * r["W"]; cand_den += r["W"]
        if args.verbose:
            print(f"{name}: text={r['text']:.3f} J_assert={r['j_assert']:.3f} "
                  f"J_cand={r['j_cand']:.3f} W={r['W']}")

    text_score = text_sum / n if n else 0.0
    assertions_score = assert_sum / n if n else 0.0
    candidates_score = cand_num / cand_den if cand_den else 0.0
    final = 0.3 * text_score + 0.3 * assertions_score + 0.4 * candidates_score

    print(f"\n=== METRIC CHÍNH THỨC (n={n} file) ===")
    print(f"  text_score       (0.3) = {text_score:.4f}")
    print(f"  assertions_score (0.3) = {assertions_score:.4f}")
    print(f"  candidates_score (0.4) = {candidates_score:.4f}")
    print(f"  ---------------------------------")
    print(f"  FINAL            = {final:.4f}")


if __name__ == "__main__":
    main()
