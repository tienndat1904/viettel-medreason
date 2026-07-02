"""Dựng DEV SET có nhãn (gold) từ các file "label spec" do người/LLM soạn.

Ý tưởng: người gán nhãn CHỈ cần cung cấp `text` (copy nguyên văn), `type`,
`assertions`, `candidates` — KHÔNG phải đếm offset ký tự (rất dễ sai).
Module này TỰ dò offset ký tự trong input gốc một cách xác định (deterministic),
validate theo schema, rồi xuất `data/dev/gold/N.json` đúng format nộp.

Định dạng label spec  (data/dev/labels/N.json) — list các object:
  {
    "text": "metoprolol 25mg po bid",   # BẮT BUỘC, copy nguyên văn từ N.txt
    "type": "THUỐC",                     # BẮT BUỘC, 1 trong 5 nhãn
    "assertions": ["isHistorical"],       # tùy chọn (mặc định [])
    "candidates": [],                     # tùy chọn (ICD-10 / RxNorm)
    "occ": 1,                             # tùy chọn: chọn lần xuất hiện thứ mấy (1-index)
    "pos": [58, 80],                      # tùy chọn: ép offset thủ công (ghi đè dò tự động)
    "note": "RxNorm TODO"                 # tùy chọn: ghi chú cho người review (KHÔNG vào gold)
  }

Dùng:
  python src/datagen/make_dev.py                 # build tất cả labels -> gold + review HTML
  python src/datagen/make_dev.py --files 1,2,3   # chỉ build vài file
  python src/datagen/make_dev.py --fuzzy         # cho phép khớp linh hoạt (ws/hoa-thường/**)

Nguyên tắc: nếu 1 `text` KHÔNG dò được offset -> BÁO LỖI TO và dừng (gold không
được phép âm thầm mất nhãn). Chạy lại sau khi sửa spec.
"""
from __future__ import annotations
import os, sys, json, argparse, glob, re

# stdout/stderr UTF-8 để in được tiếng Việt trên Windows console (cp1252) — reproducible
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
for p in (SRC, os.path.join(SRC, "postprocess"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from schema import (LABELS, ASSERTIONS, ASSERTABLE_TYPES, CANDIDATE_TYPES,
                    make_concept)  # noqa
from validate import assert_valid  # noqa


class SpecError(Exception):
    pass


def _flexible_pattern(span: str) -> re.Pattern:
    """Regex khớp span cho phép khác biệt whitespace và ký tự '*' markdown."""
    span = span.strip().strip("*").strip()
    tokens = [re.escape(t) for t in span.split()]
    if not tokens:
        return re.compile(r"(?!x)x")
    return re.compile(r"\**\s*".join(tokens), re.IGNORECASE)


def _all_exact(text: str, sub: str) -> list[tuple[int, int]]:
    out, i = [], 0
    while True:
        j = text.find(sub, i)
        if j < 0:
            break
        out.append((j, j + len(sub)))
        i = j + 1
    return out


def _pick_offset(text, spec, used, fuzzy, idx):
    """Trả (start, end, matched_text) cho 1 concept spec. Raise SpecError nếu bí."""
    raw = spec.get("text")
    if not isinstance(raw, str) or not raw:
        raise SpecError(f"[#{idx}] thiếu 'text'")

    # 0) ép offset thủ công
    if "pos" in spec and spec["pos"] is not None:
        s, e = spec["pos"]
        s, e = int(s), int(e)
        got = text[s:e]
        if got != raw:
            raise SpecError(f"[#{idx}] pos {[s, e]} -> '{got}' KHÁC text '{raw}'")
        return s, e, got

    occs = _all_exact(text, raw)

    # 1) chọn occurrence cụ thể
    if "occ" in spec and spec["occ"] is not None:
        k = int(spec["occ"])
        if not (1 <= k <= len(occs)):
            raise SpecError(f"[#{idx}] 'occ'={k} nhưng '{raw}' xuất hiện {len(occs)} lần")
        return (*occs[k - 1], raw)

    # 2) occurrence đầu tiên chưa bị dùng bởi concept trước (cùng span)
    for s, e in occs:
        if (s, e) not in used:
            return s, e, raw

    # 3) fallback linh hoạt (chỉ khi --fuzzy) — rewrite text về đúng chuỗi gốc
    if fuzzy:
        for m in _flexible_pattern(raw).finditer(text):
            if (m.start(), m.end()) not in used:
                return m.start(), m.end(), text[m.start():m.end()]

    if occs:
        raise SpecError(f"[#{idx}] '{raw}' xuất hiện {len(occs)} lần nhưng đều đã bị dùng "
                        f"(thêm 'occ' để chỉ định)")
    raise SpecError(f"[#{idx}] KHÔNG tìm thấy '{raw}' trong input"
                    + ("" if fuzzy else " (thử --fuzzy hoặc sửa lại cho khớp nguyên văn)"))


def build_gold(text: str, specs: list[dict], fuzzy: bool = False) -> list[dict]:
    """Chuyển label spec -> list concept đúng schema (đã có position)."""
    used: set[tuple[int, int]] = set()
    concepts = []
    for idx, spec in enumerate(specs):
        ctype = spec.get("type")
        if ctype not in LABELS:
            raise SpecError(f"[#{idx}] type sai: {ctype!r}")
        for a in spec.get("assertions", []) or []:
            if a not in ASSERTIONS:
                raise SpecError(f"[#{idx}] assertion sai: {a!r}")
            if ctype not in ASSERTABLE_TYPES:
                raise SpecError(f"[#{idx}] type {ctype} KHÔNG được có assertions")
        if spec.get("candidates") and ctype not in CANDIDATE_TYPES:
            raise SpecError(f"[#{idx}] type {ctype} KHÔNG được có candidates")

        s, e, matched = _pick_offset(text, spec, used, fuzzy, idx)
        used.add((s, e))
        concepts.append(make_concept(matched, ctype, [s, e],
                                     spec.get("assertions"), spec.get("candidates")))
    concepts.sort(key=lambda c: (c["position"][0], c["position"][1]))
    assert_valid(concepts, len(text))
    return concepts


def _load_specs(fp: str) -> list[dict]:
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SpecError("label spec phải là list")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default="data/dev/labels")
    ap.add_argument("--input", default="data/test/input")
    ap.add_argument("--gold", default="data/dev/gold")
    ap.add_argument("--html", default="data/dev/review",
                    help="thư mục xuất HTML review (rỗng = bỏ qua)")
    ap.add_argument("--files", default="", help="danh sách N (vd 1,2,3); rỗng = tất cả")
    ap.add_argument("--fuzzy", action="store_true")
    ap.add_argument("--keep-going", action="store_true",
                    help="không dừng khi 1 file lỗi (mặc định dừng)")
    args = ap.parse_args()

    os.makedirs(args.gold, exist_ok=True)
    only = {x.strip() for x in args.files.split(",") if x.strip()} if args.files else None

    label_files = sorted(glob.glob(os.path.join(args.labels, "*.json")),
                         key=lambda p: int(re.sub(r"\D", "", os.path.basename(p)) or 0))
    if not label_files:
        print(f"⚠️  Không thấy label spec trong {args.labels}")
        return

    ok, errs = 0, []
    type_tot = {}
    built = []  # (name, text, concepts)
    for lf in label_files:
        name = os.path.splitext(os.path.basename(lf))[0]
        if only and name not in only:
            continue
        txt_path = os.path.join(args.input, f"{name}.txt")
        if not os.path.exists(txt_path):
            errs.append(f"{name}: thiếu input {txt_path}")
            if not args.keep_going:
                break
            continue
        text = open(txt_path, encoding="utf-8").read()
        try:
            specs = _load_specs(lf)
            gold = build_gold(text, specs, args.fuzzy)
        except (SpecError, Exception) as e:
            errs.append(f"{name}: {e}")
            if not args.keep_going:
                break
            continue
        with open(os.path.join(args.gold, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(gold, f, ensure_ascii=False, indent=2)
        for c in gold:
            type_tot[c["type"]] = type_tot.get(c["type"], 0) + 1
        built.append((name, text, gold))
        ok += 1

    # review HTML
    if args.html and built:
        try:
            from build_review_html import write_review
            write_review(args.html, built)
            print(f"📝 Review HTML -> {args.html}/index.html")
        except Exception as e:  # noqa
            print(f"(bỏ qua review HTML: {e})")

    print(f"\n✅ Dựng gold: {ok} file  ->  {args.gold}")
    if type_tot:
        total = sum(type_tot.values())
        print(f"   Tổng {total} concept:  " +
              "  ".join(f"{t}={n}" for t, n in sorted(type_tot.items())))
    if errs:
        print(f"\n❌ {len(errs)} file LỖI:")
        for e in errs[:50]:
            print("  -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
