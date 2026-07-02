"""Pipeline end-to-end: đọc thư mục input/*.txt -> ghi output/*.json đúng schema.

Cách chạy:
  python src/pipeline.py --input data/test/input --output output --backend rule
  python src/pipeline.py --input <BTC_private_test> --output output --backend llm

Deterministic: seed cố định, temperature=0.
"""
from __future__ import annotations
import os, sys, json, argparse, glob, random

SRC = os.path.dirname(os.path.abspath(__file__))
for sub in ["", "extract", "linking", "offset", "postprocess", "eval", "kb", "datagen"]:
    p = os.path.join(SRC, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import yaml
from resolve_spans import resolve_offsets
from validate import clean_file
from assertions import annotate as annotate_assertions
from schema import CHAN_DOAN, THUOC


def load_cfg(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_extractor(backend, cfg):
    if backend == "rule":
        import rules_baseline
        return rules_baseline.extract
    elif backend == "llm":
        from llm_extractor import LLMExtractor
        ex = LLMExtractor(
            model_id=cfg["extract"]["llm_model"],
            lora_adapter=cfg["extract"].get("lora_adapter", ""),
            max_new_tokens=cfg["extract"]["max_new_tokens"],
            temperature=cfg["extract"]["temperature"],
            max_chunk_chars=cfg["extract"].get("max_chunk_chars", 1800),
            seed=cfg["seed"])
        return ex.extract
    raise ValueError(f"backend không hợp lệ: {backend}")


def process_file(text, extract_fn, linker, assertion_mode="union"):
    spans = extract_fn(text)                 # [{text,type,(assertions)}]
    concepts = resolve_offsets(text, spans)  # + position
    concepts = annotate_assertions(text, concepts, mode=assertion_mode)  # assertion theo ngữ cảnh
    concepts = clean_file(concepts, text)    # làm sạch + loại trùng
    # linking
    for c in concepts:
        if c["type"] == CHAN_DOAN:
            c["candidates"] = linker.link_diagnosis(c["text"], text)
        elif c["type"] == THUOC:
            c["candidates"] = linker.link_drug(c["text"], text)
    return concepts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--input", default=None)
    ap.add_argument("--output", default=None)
    ap.add_argument("--backend", default=None, choices=["rule", "llm"])
    ap.add_argument("--resume", action="store_true",
                    help="bỏ qua file N.json đã có & hợp lệ (chạy tiếp sau khi Colab ngắt)")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    random.seed(cfg["seed"])
    input_dir = args.input or cfg["paths"]["test_input"]
    output_dir = args.output or cfg["paths"]["output"]
    backend = args.backend or cfg["extract"]["backend"]
    assertion_mode = cfg["extract"].get("assertion_mode", "union")
    os.makedirs(output_dir, exist_ok=True)

    extract_fn = get_extractor(backend, cfg)
    from linker import Linker
    linker = Linker(cfg)

    files = sorted(glob.glob(os.path.join(input_dir, "*.txt")),
                   key=lambda p: int(os.path.splitext(os.path.basename(p))[0])
                   if os.path.splitext(os.path.basename(p))[0].isdigit() else 0)
    print(f"[pipeline] backend={backend} | {len(files)} file | out={output_dir}"
          f"{' | resume' if args.resume else ''}")

    def _done(path):
        """File đã xuất & parse được JSON -> coi như hoàn tất (dùng cho --resume)."""
        if not os.path.exists(path):
            return False
        try:
            with open(path, encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, OSError):
            return False

    skipped = 0
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        outpath = os.path.join(output_dir, f"{name}.json")
        if args.resume and _done(outpath):
            skipped += 1
            continue
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()
        concepts = process_file(text, extract_fn, linker, assertion_mode)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(concepts, f, ensure_ascii=False, indent=2)
    print(f"[pipeline] xong.{f' Bỏ qua {skipped} file đã có.' if skipped else ''}")


if __name__ == "__main__":
    main()
