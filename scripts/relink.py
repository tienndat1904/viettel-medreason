"""Re-link output đã có (giữ nguyên extraction/assertion) bằng backend linking khác.

Dùng để so lexical vs semantic mà KHÔNG chạy lại LLM extraction (đắt):
  python scripts/relink.py --pred dev_B --input devset/input --link-backend semantic --out dev_C

Đọc mỗi output/*.json, nạp lại note gốc làm context, tính lại 'candidates' cho
CHẨN_ĐOÁN/THUỐC theo linker mới; các trường khác giữ nguyên.
"""
from __future__ import annotations
import os, sys, json, argparse, glob

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
for sub in ["", "linking", "postprocess"]:
    sys.path.insert(0, os.path.join(SRC, sub))
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8")
    except Exception: pass

import yaml
from schema import CHAN_DOAN, THUOC


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True, help="thư mục output đã có (concepts)")
    ap.add_argument("--input", required=True, help="thư mục note gốc (.txt) làm context")
    ap.add_argument("--link-backend", required=True, choices=["lexical", "semantic"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    cfg["linking"]["backend"] = args.link_backend
    from linker import Linker
    linker = Linker(cfg)
    os.makedirs(args.out, exist_ok=True)

    n = 0
    for fp in glob.glob(os.path.join(args.pred, "*.json")):
        name = os.path.splitext(os.path.basename(fp))[0]
        concepts = json.load(open(fp, encoding="utf-8"))
        note_fp = os.path.join(args.input, f"{name}.txt")
        text = open(note_fp, encoding="utf-8").read() if os.path.exists(note_fp) else ""
        for c in concepts:
            if c.get("type") == CHAN_DOAN:
                c["candidates"] = linker.link_diagnosis(c.get("text", ""), text)
            elif c.get("type") == THUOC:
                c["candidates"] = linker.link_drug(c.get("text", ""), text)
        json.dump(concepts, open(os.path.join(args.out, f"{name}.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        n += 1
    print(f"[relink] {n} file -> {args.out} (linking={args.link_backend})")


if __name__ == "__main__":
    main()
