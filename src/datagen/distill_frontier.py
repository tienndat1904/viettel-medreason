"""Distill nhãn bạc FRONTIER -> SFT data (chunk-aligned) cho QLoRA.

Khác gen_synthetic.py (note tổng hợp, offset tự đặt), script này lấy NHÃN THẬT trên
phân phối test: input `data/test/input/*.txt` + concept do LLM frontier trích
(`data/silver/frontier_ref/raw_extract/N.json`, chỉ {text,type}).

QUAN TRỌNG — chunk-aligned: lúc inference LLMExtractor CHIA input thành chunk theo
`chunk_document(text, max_chunk_chars)` rồi trích từng chunk. Nếu train trên CẢ file mà
inference lại thấy CHUNK -> lệch phân phối. Nên ở đây mỗi CHUNK là 1 mẫu SFT, concept gán
vào chunk chứa nó (substring, casefold). Mẫu dùng ĐÚNG to_sft_example(fewshot=False) như
gen_synthetic -> messages [system, user(chunk), assistant(JSON {text,type})].

Chunk không chứa concept nào -> mẫu target `[]` (dạy model im lặng ở dòng hành chính/không
phải khái niệm) — mặc định GIỮ; --drop-empty để bỏ.

Dùng:
  python src/datagen/distill_frontier.py            # -> data/silver/frontier_ref/train_sft_distill.jsonl
  python src/datagen/distill_frontier.py --max-chunk-chars 1800 --drop-empty
"""
from __future__ import annotations
import os, sys, json, glob, argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
ROOT = os.path.dirname(SRC)
for p in (SRC, HERE, os.path.join(SRC, "extract")):
    if p not in sys.path:
        sys.path.insert(0, p)

from chunking import chunk_document           # noqa: E402
from gen_synthetic import to_sft_example       # noqa: E402  (khớp prompt.py, fewshot=False)


def _assign(concepts, chunk_text):
    """Concept nào (casefold substring) nằm trong chunk -> gán vào chunk. Dedup (text,type)."""
    low = chunk_text.casefold()
    out, seen = [], set()
    for c in concepts:
        t, typ = c.get("text"), c.get("type")
        if not isinstance(t, str) or not t.strip() or not typ:
            continue
        if t.casefold() not in low:
            continue
        key = (t, typ)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": t, "type": typ})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="data/test/input")
    ap.add_argument("--raw-dir", default="data/silver/frontier_ref/raw_extract")
    ap.add_argument("--out", default="data/silver/frontier_ref/train_sft_distill.jsonl")
    ap.add_argument("--max-chunk-chars", type=int, default=1800,
                    help="phải KHỚP configs extract.max_chunk_chars lúc inference")
    ap.add_argument("--drop-empty", action="store_true",
                    help="bỏ chunk không có concept (mặc định giữ để dạy target [])")
    args = ap.parse_args()

    def _abs(p):
        return p if os.path.isabs(p) else os.path.join(ROOT, p)

    in_dir, raw_dir, out_path = _abs(args.input_dir), _abs(args.raw_dir), _abs(args.out)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    files = sorted(glob.glob(os.path.join(in_dir, "*.txt")),
                   key=lambda p: int(os.path.splitext(os.path.basename(p))[0])
                   if os.path.splitext(os.path.basename(p))[0].isdigit() else 0)

    n_files = n_chunks = n_empty = n_assigned = n_unmatched = 0
    n_concepts_total = 0
    with open(out_path, "w", encoding="utf-8") as jf:
        for fp in files:
            name = os.path.splitext(os.path.basename(fp))[0]
            raw_fp = os.path.join(raw_dir, name + ".json")
            if not os.path.exists(raw_fp):
                continue
            with open(fp, encoding="utf-8") as f:
                text = f.read()
            with open(raw_fp, encoding="utf-8") as f:
                concepts = json.load(f)
            n_files += 1
            n_concepts_total += len(concepts)

            chunks = chunk_document(text, args.max_chunk_chars)
            matched_keys = set()
            for _, chunk in chunks:
                ch_concepts = _assign(concepts, chunk)
                for c in ch_concepts:
                    matched_keys.add((c["text"], c["type"]))
                if not ch_concepts:
                    n_empty += 1
                    if args.drop_empty:
                        continue
                ex = to_sft_example(chunk, ch_concepts, fewshot=False)
                jf.write(json.dumps(ex, ensure_ascii=False) + "\n")
                n_chunks += 1
                n_assigned += len(ch_concepts)
            # concept không khớp chunk nào (frontier chuẩn hoá/diễn giải khác input gốc)
            for c in concepts:
                if (c.get("text"), c.get("type")) not in matched_keys:
                    n_unmatched += 1

    print(f"✅ {n_files} file -> {n_chunks} mẫu SFT (chunk-aligned) tại {out_path}")
    print(f"   concept frontier: {n_concepts_total} | gán vào chunk: {n_assigned} "
          f"| KHÔNG khớp chunk nào: {n_unmatched}")
    print(f"   chunk rỗng (target []): {n_empty}"
          + (" (đã bỏ)" if args.drop_empty else " (đã giữ)"))
    if n_unmatched:
        print(f"   ⚠️ {n_unmatched} concept frontier không phải substring của input "
              f"(diễn giải/chuẩn hoá) -> mất khỏi SFT; chấp nhận được nếu nhỏ.")


if __name__ == "__main__":
    main()
