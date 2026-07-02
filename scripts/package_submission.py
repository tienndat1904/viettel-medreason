"""Validate toàn bộ output/*.json rồi đóng gói output.zip đúng cấu trúc nộp.

Cấu trúc zip: output/1.json, output/2.json, ...
Dùng: python scripts/package_submission.py --output output --n 100
"""
from __future__ import annotations
import os, sys, json, argparse, zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, os.path.join(SRC, "postprocess"))
sys.path.insert(0, SRC)
from validate import assert_valid  # noqa
from schema import LABELS, ASSERTIONS  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="output")
    ap.add_argument("--input", default="data/test/input",
                    help="để đối chiếu độ dài text khi validate position")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--zip", default="output.zip")
    args = ap.parse_args()

    problems = []
    for i in range(1, args.n + 1):
        fp = os.path.join(args.output, f"{i}.json")
        if not os.path.exists(fp):
            problems.append(f"THIẾU {i}.json")
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list), "không phải list"
            txt_path = os.path.join(args.input, f"{i}.txt")
            tlen = len(open(txt_path, encoding="utf-8").read()) if os.path.exists(txt_path) else 10**9
            assert_valid(data, tlen)
        except Exception as e:
            problems.append(f"LỖI {i}.json: {e}")

    if problems:
        print("❌ KHÔNG đóng gói — có lỗi:")
        for p in problems[:50]:
            print("  -", p)
        sys.exit(1)

    with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
        for i in range(1, args.n + 1):
            z.write(os.path.join(args.output, f"{i}.json"), f"output/{i}.json")
    print(f"✅ Đã tạo {args.zip} ({args.n} file hợp lệ).")


if __name__ == "__main__":
    main()
