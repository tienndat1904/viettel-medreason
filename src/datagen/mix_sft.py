"""Trộn SFT: distill frontier (nhãn thật, phân phối test) + synthetic (phủ format).

Vì T4 rất chậm (~0.05 mẫu/s -> ~2h/500 mẫu), KHÔNG train nổi 1872 mẫu × 2 epoch trong
12h. Script này dựng 1 file gọn, DISTILL-NẶNG: oversample distill (tín hiệu chính, đường
+9đ) + 1 tập con synthetic (mỏ neo cấu trúc JSON/nhãn). Mặc định ~670 mẫu -> 2 epoch ~8-9h.

Thứ tự trong file KHÔNG quan trọng (Trainer shuffle train). KHÔNG dùng --max-samples của
train_qlora (nó cắt theo THỨ TỰ file trước shuffle -> có thể cắt trúng distill); thay vào đó
file này đã đúng kích cỡ cần train.

Dùng:
  python src/datagen/mix_sft.py                      # 124 distill x3 + 300 synthetic = 672
  python src/datagen/mix_sft.py --distill-repeat 4 --synthetic 200 --out ...
"""
from __future__ import annotations
import os, sys, json, random, argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(path):
    with open(path, encoding="utf-8") as f:
        return [l for l in f.read().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--distill", default="data/silver/frontier_ref/train_sft_distill.jsonl")
    ap.add_argument("--synthetic", type=int, default=300,
                    help="số mẫu synthetic lấy ngẫu nhiên (seed cố định)")
    ap.add_argument("--synthetic-file", default="data/synthetic/train_sft.jsonl")
    ap.add_argument("--distill-repeat", type=int, default=3,
                    help="oversample distill (mặc định x3)")
    ap.add_argument("--out", default="data/silver/frontier_ref/train_sft_mixed_t4.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    def _abs(p):
        return p if os.path.isabs(p) else os.path.join(ROOT, p)

    distill = _read(_abs(args.distill))
    synth_all = _read(_abs(args.synthetic_file))
    rng = random.Random(args.seed)
    n_syn = min(args.synthetic, len(synth_all))
    synth = rng.sample(synth_all, n_syn)

    mixed = distill * args.distill_repeat + synth
    rng.shuffle(mixed)                       # trộn để ghi ra không gom cụm (Trainer cũng shuffle)
    out = _abs(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for l in mixed:
            f.write(l + "\n")

    n_dis = len(distill) * args.distill_repeat
    print(f"✅ {len(mixed)} mẫu -> {out}")
    print(f"   distill {len(distill)} x{args.distill_repeat} = {n_dis} "
          f"({100*n_dis/len(mixed):.0f}%) | synthetic {n_syn} ({100*n_syn/len(mixed):.0f}%)")


if __name__ == "__main__":
    main()
