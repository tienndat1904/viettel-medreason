"""So sánh 2 thư mục output theo METRIC CHÍNH THỨC BTC — dùng để biết LLM có VƯỢT rule chưa.

Chấm cả 2 dir bằng official_scorer trên CÙNG 1 gold (mặc định data/dev/gold — P3 đã chuẩn
hóa granularity WHO/BYT 4 ký tự + điền RxNorm tiered, PR#32; xem docs/LLM_EVAL_HANDOFF.md),
in cạnh nhau + delta + phán quyết "LLM vượt rule?".

LƯU Ý calibration: text_score/WER offline ≈ leaderboard; candidates_score offline LẠC QUAN
(dev gold tự-gán, vòng tròn) -> tin phần SO SÁNH TƯƠNG ĐỐI (A vs B), đừng tin absolute candidate.

Dùng:
  # rule baseline hiện ở output/, LLM output do P1 sinh trên Colab ở output_llm/
  python src/eval/compare_backends.py --a output --a-name rule --b output_llm --b-name llm
"""
from __future__ import annotations
import os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import official_scorer as S


def score_dir(pred_dir, gold_dir):
    gold, pred = S.load(gold_dir), S.load(pred_dir)
    text_sum = assert_sum = 0.0
    cand_num = cand_den = 0.0
    n = 0
    for name, g in gold.items():
        r = S.score_file(g, pred.get(name, []))
        text_sum += r["text"]; assert_sum += r["j_assert"]; n += 1
        cand_num += r["j_cand"] * r["W"]; cand_den += r["W"]
    if not n:
        return None
    ts = text_sum / n
    asrt = assert_sum / n
    cand = cand_num / cand_den if cand_den else 0.0
    return {"text": ts, "assert": asrt, "cand": cand,
            "final": 0.3 * ts + 0.3 * asrt + 0.4 * cand, "n": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="thư mục output A (vd rule baseline)")
    ap.add_argument("--b", required=True, help="thư mục output B (vd LLM)")
    ap.add_argument("--a-name", default="A")
    ap.add_argument("--b-name", default="B")
    ap.add_argument("--gold", default="data/dev/gold")
    args = ap.parse_args()

    a = score_dir(args.a, args.gold)
    b = score_dir(args.b, args.gold)
    if not a or not b:
        print("Thiếu file để chấm."); return

    print(f"\n=== METRIC CHÍNH THỨC BTC (gold={args.gold}, n={a['n']}) ===")
    hdr = f"{'':18}{args.a_name:>12}{args.b_name:>12}{'Δ(B-A)':>12}"
    print(hdr); print("-" * len(hdr))
    for k, lab in [("text", "text_score .3"), ("assert", "assert_score .3"),
                   ("cand", "cand_score .4"), ("final", "FINAL")]:
        d = b[k] - a[k]
        print(f"{lab:18}{a[k]:>12.4f}{b[k]:>12.4f}{d:>+12.4f}")
    verdict = "✅ VƯỢT" if b["final"] > a["final"] else "❌ CHƯA vượt"
    print(f"\n=> {args.b_name} {verdict} {args.a_name} "
          f"(Δfinal={b['final']-a['final']:+.4f}). "
          f"{'Nộp được.' if b['final'] > a['final'] else 'ĐỪNG nộp bản này (rule tốt hơn).'}")
    print("LƯU Ý: candidates offline lạc quan (dev vòng tròn); tin phần so sánh tương đối + text/assert.")


if __name__ == "__main__":
    main()
