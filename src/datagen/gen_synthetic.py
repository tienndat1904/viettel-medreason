"""Sinh SYNTHETIC bệnh án VN + gold labels đầy đủ (offline, KHÔNG API — reproducible).

Cách tiếp cận tổ hợp: lắp ghép note từ pools (pools.py) theo cấu trúc 3 mục giống
bệnh án test, tự đặt span nên offset + gold CHÍNH XÁC 100%. Inject nhiễu dịch máy
(dính chữ, **markdown**, double-space, po bid/q4h). Ánh xạ:
  - vị trí trong mục 'Tiền sử / Thuốc trước khi nhập viện / bệnh mạn' -> isHistorical
  - tiền tố phủ định -> isNegated ; người nhà -> isFamily
  - CHẨN_ĐOÁN -> mã ICD (pools) ; THUỐC -> RxNorm ingredient rxcui (pools)

Xuất:
  data/synthetic/notes/*.txt        văn bản (để soi)
  data/synthetic/gold/*.json        full gold (text/type/position/assertions/candidates)
  data/synthetic/train_sft.jsonl    SFT cho QLoRA — chat format khớp prompt.py, target=[{text,type}]

Dùng:
  python src/datagen/gen_synthetic.py --n 1500 --seed 42
  python src/datagen/gen_synthetic.py --n 50 --out-dir data/synthetic_smoke   # thử nhanh
"""
from __future__ import annotations
import os, sys, json, argparse, random

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.dirname(HERE)
for p in (SRC, HERE, os.path.join(SRC, "extract")):
    if p not in sys.path:
        sys.path.insert(0, p)

import pools
from schema import (TRIEU_CHUNG, TEN_XET_NGHIEM, KET_QUA_XET_NGHIEM,
                    CHAN_DOAN, THUOC, make_concept)


class NoteBuilder:
    """Ghép chuỗi trái→phải, ghi offset ký tự chính xác cho mỗi concept đã emit."""

    def __init__(self):
        self._parts: list[str] = []
        self._len = 0
        self.concepts: list[dict] = []

    def add(self, s: str):
        if s:
            self._parts.append(s)
            self._len += len(s)

    def emit(self, text, ctype, assertions=None, candidates=None):
        """Chèn `text` vào note tại vị trí hiện tại + ghi concept gold."""
        start = self._len
        self.add(text)
        self.concepts.append(make_concept(text, ctype, [start, start + len(text)],
                                          assertions, candidates))

    def text(self) -> str:
        return "".join(self._parts)


# ---------- nhiễu ----------
def _noisy_space(rng) -> str:
    r = rng.random()
    if r < 0.08:
        return "  "      # double space
    if r < 0.11:
        return ""        # dính chữ
    return " "


def _maybe_bold(rng, s: str) -> tuple[str, str]:
    """Trả (prefix, suffix) markdown ** quanh 1 cụm (không tính vào span)."""
    if rng.random() < 0.06:
        return "**", "**"
    return "", ""


# ---------- các khối mục ----------
def _emit_line_item(nb: NoteBuilder, rng, text, ctype, assertions, candidates=None,
                    neg=False, fam=False, narrative=False):
    """Emit 1 gạch đầu dòng '- <prefix><concept>' với assertion theo prefix.

    narrative=True: bọc thêm ngữ cảnh tường thuật (add, KHÔNG emit) sau concept ->
    giống note thật ("- đau ngực khi thay đổi tư thế, kéo dài vài ngày nay") mà span
    concept vẫn SẠCH đúng gold.
    """
    nb.add("- ")
    a = list(assertions)
    if fam:
        nb.add(rng.choice(pools.FAMILY_PREFIX))
        if "isFamily" not in a:
            a.append("isFamily")
    elif neg:
        nb.add(rng.choice(pools.NEG_PREFIX))
        if "isNegated" not in a:
            a.append("isNegated")
    pre, suf = _maybe_bold(rng, text)
    nb.add(pre)
    nb.emit(text, ctype, a, candidates)
    nb.add(suf)
    if narrative and not neg and rng.random() < 0.5:
        nb.add(" " + rng.choice(pools.SYMPTOM_NARRATIVE))
        if rng.random() < 0.35:
            nb.add(", " + rng.choice(pools.SYMPTOM_NARRATIVE))   # run-on kiểu MT
    nb.add("\n")


def _symptom_char_block(nb: NoteBuilder, rng):
    """Khối 'Đặc điểm triệu chứng' đa số N/A — nhiễu KHÔNG trích, rất hay gặp ở note test."""
    nb.add("    Đặc điểm triệu chứng\n")
    for f in rng.sample(pools.SYMPTOM_CHAR_FIELDS, rng.randint(4, 7)):
        nb.add(f"    - {f}: {rng.choice(pools.SYMPTOM_CHAR_VALS)}\n")


def _history_section(nb: NoteBuilder, rng, density=1.0):
    nb.add(rng.choice(pools.HDR_HISTORY) + "\n")
    # bệnh mạn tính -> isHistorical
    if rng.random() < 0.9:
        nb.add("    " + rng.choice(pools.HDR_CHRONIC) + "\n")
        for name, code in rng.sample(pools.DIAGNOSES, max(1, round(rng.randint(2, 4) * density))):
            nb.add("    ")
            _emit_line_item(nb, rng, name, CHAN_DOAN, ["isHistorical"], [code])
    # thuốc trước khi nhập viện -> isHistorical (đôi khi ghi "không tuân thủ" -> bỏ qua)
    if rng.random() < 0.85:
        nb.add("    " + rng.choice(pools.HDR_PREMED))
        if rng.random() < 0.12:
            nb.add(": không tuân thủ điều trị bằng thuốc\n")     # ca không có thuốc
        else:
            nb.add("\n")
            for ingr, rxcui, strengths in rng.sample(pools.DRUGS, max(1, round(rng.randint(2, 4) * density))):
                txt = ingr
                if rng.random() < 0.8:
                    txt += " " + rng.choice(strengths)
                if rng.random() < 0.5:
                    txt += " " + rng.choice(pools.DRUG_SUFFIX)
                nb.add("    ")
                _emit_line_item(nb, rng, txt, THUOC, ["isHistorical"], [rxcui])
    # yếu tố nguy cơ (KHÔNG trích) — rất hay gặp ở note thật
    if rng.random() < 0.45:
        nb.add("    Các yếu tố nguy cơ liên quan: " + rng.choice(pools.RISK_FACTORS) + "\n")
    # thỉnh thoảng tiền sử gia đình
    if rng.random() < 0.35:
        nb.add("    Tiền sử gia đình\n")
        name, code = rng.choice(pools.DIAGNOSES)
        nb.add("    ")
        _emit_line_item(nb, rng, name, CHAN_DOAN, ["isHistorical"], [code], fam=True)
    if rng.random() < 0.4:
        nb.add("    " + rng.choice(pools.ADMIN_LINES) + "\n")


def _present_section(nb: NoteBuilder, rng, density=1.0):
    nb.add("\n" + rng.choice(pools.HDR_PRESENT) + "\n")
    nb.add("    Lý do nhập viện: ")
    s0 = rng.choice(pools.SYMPTOMS)
    nb.emit(s0, TRIEU_CHUNG, [])
    nb.add("\n")
    if rng.random() < 0.5:
        nb.add("    " + rng.choice(pools.ADMIN_LINES) + "\n")
    nb.add("    " + rng.choice(pools.HDR_SYMPTOM) + "\n")
    for s in rng.sample(pools.SYMPTOMS, max(2, round(rng.randint(3, 6) * density))):
        nb.add("    ")
        _emit_line_item(nb, rng, s, TRIEU_CHUNG, [], narrative=True)
    # khối "Đặc điểm triệu chứng" N/A (nhiễu không trích) — đặc trưng note test
    if rng.random() < 0.5:
        _symptom_char_block(nb, rng)
    # triệu chứng phủ định
    nb.add("    " + rng.choice(pools.HDR_RELATED) + "\n")
    for s in rng.sample(pools.SYMPTOMS, rng.randint(2, 4)):
        nb.add("    ")
        _emit_line_item(nb, rng, s, TRIEU_CHUNG, [], neg=True)
    # đôi khi chẩn đoán hiện tại
    if rng.random() < 0.7:
        name, code = rng.choice(pools.DIAGNOSES)
        nb.add("    Chẩn đoán sơ bộ: ")
        pre, suf = _maybe_bold(rng, name)
        nb.add(pre); nb.emit(name, CHAN_DOAN, [], [code]); nb.add(suf); nb.add("\n")
    if rng.random() < 0.4:
        nb.add("    " + rng.choice(pools.FILLER) + "\n")


def _eval_section(nb: NoteBuilder, rng, density=1.0):
    nb.add("\n" + rng.choice(pools.HDR_EVAL) + "\n")
    nb.add("    " + rng.choice(pools.HDR_LAB) + "\n")
    for name, unit, lo, hi, dec in rng.sample(pools.LABS, max(2, round(rng.randint(4, 8) * density))):
        val = round(rng.uniform(lo, hi), dec)
        vs = (f"{val:.{dec}f}" if dec else str(int(val)))
        if rng.random() < 0.25:
            vs = vs.replace(".", ",")     # dấu phẩy thập phân kiểu VN
        nb.add("    - ")
        pre, suf = _maybe_bold(rng, name)
        nb.add(pre); nb.emit(name, TEN_XET_NGHIEM, []); nb.add(suf)
        nb.add(_noisy_space(rng) if rng.random() < 0.5 else ": ")
        nb.emit(vs + (f" {unit}" if unit and rng.random() < 0.5 else ""),
                KET_QUA_XET_NGHIEM, [])
        nb.add("\n")
    # xét nghiệm cho KẾT_QUẢ dạng CHỮ (định tính) — dạy model lấy "âm tính/dương tính/bình thường"
    if rng.random() < 0.55:
        for name, results in rng.sample(pools.LABS_TEXT, rng.randint(1, 2)):
            nb.add("    - ")
            pre, suf = _maybe_bold(rng, name)
            nb.add(pre); nb.emit(name, TEN_XET_NGHIEM, []); nb.add(suf)
            nb.add(rng.choice([": ", " "]))
            nb.emit(rng.choice(results), KET_QUA_XET_NGHIEM, [])
            nb.add("\n")
    # hình ảnh / thăm dò — kèm mô tả kết quả (KQXN dạng chữ, cụm dài) theo BTC forum;
    # đôi khi để trống -> giữ ca "chỉ có tên xét nghiệm" (HHM #1: tên không cần kết quả).
    if rng.random() < 0.85:
        nb.add("    " + rng.choice(pools.HDR_IMAGING) + "\n")
        for im in rng.sample(pools.IMAGING, rng.randint(1, 3)):
            nb.add("    - ")
            nb.emit(im, TEN_XET_NGHIEM, [])
            finds = pools.IMAGING_FINDINGS.get(im)
            if finds and rng.random() < 0.6:
                nb.add(rng.choice([": ", " cho thấy ", " ghi nhận ", " kết luận "]))
                nb.emit(rng.choice(finds), KET_QUA_XET_NGHIEM, [])
            nb.add("\n")
    # thuốc điều trị hiện tại (KHÔNG historical)
    if rng.random() < 0.85:
        nb.add("    " + rng.choice(pools.HDR_TREAT) + "\n")
        for ingr, rxcui, strengths in rng.sample(pools.DRUGS, rng.randint(1, 3)):
            txt = ingr
            if rng.random() < 0.7:
                txt += " " + rng.choice(strengths)
            if rng.random() < 0.6:
                txt += " " + rng.choice(pools.DRUG_SUFFIX)
            nb.add("    - ")
            nb.emit(txt, THUOC, [], [rxcui])
            nb.add("\n")


def generate_note(rng) -> tuple[str, list[dict]]:
    """Sinh note với ĐỘ ĐẦY biến thiên (giống test: có note dày, có note cực thưa).

    profile:
      - 'sparse' (~25%): note ngắn như file 26 — ít concept, mục 3 thường RỖNG/thiếu.
      - 'medium' (~40%): độ đầy vừa.
      - 'full'   (~35%): dày đặc như file 3.
    """
    nb = NoteBuilder()
    r = rng.random()
    if r < 0.25:
        profile, density, p_eval = "sparse", 0.4, 0.35
    elif r < 0.65:
        profile, density, p_eval = "medium", 0.7, 0.85
    else:
        profile, density, p_eval = "full", 1.1, 1.0

    _history_section(nb, rng, density)
    _present_section(nb, rng, density)
    if rng.random() < p_eval:
        _eval_section(nb, rng, density)
    elif profile == "sparse":
        # mục 3 khai báo nhưng bỏ trống (giống file 26)
        nb.add("\n" + rng.choice(pools.HDR_EVAL) + "\n")
    return nb.text(), nb.concepts


# ---------- SFT export (khớp prompt.py) ----------
def _dedup_text_type(concepts) -> list[dict]:
    """Giống LLMExtractor._clean_spans: dedup (text,type), giữ thứ tự."""
    out, seen = [], set()
    for c in concepts:
        key = (c["text"], c["type"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": c["text"], "type": c["type"]})
    return out


def to_sft_example(text, concepts, fewshot=False):
    """Trả dict {messages:[...]} cho SFT.

    fewshot=False (mặc định): mẫu GỌN `system + user(note) -> assistant` — vì fine-tune
      thay thế nhu cầu few-shot; nhúng few-shot vào MỖI mẫu làm phình token (đáp án ở cuối
      bị cắt khi > max_len). Đo thực tế: few-shot -> 1168/1500 mẫu bị cắt @2048; bỏ -> hết cắt.
    fewshot=True: giữ nguyên build_messages của P1 (khớp prompt few-shot lúc inference chưa FT).
    Target JSON compact (ít token). Lưu ý cho P1: khi dùng model đã FT, inference cũng nên
    BỎ few-shot (system+user) cho khớp cách train.
    """
    import prompt
    target = _dedup_text_type(concepts)
    if fewshot:
        msgs = prompt.build_messages(text)      # system + fewshot + user(note)
    else:
        msgs = [{"role": "system", "content": prompt.SYSTEM},
                {"role": "user", "content": prompt._USER_TEMPLATE.format(text=text)}]
    msgs.append({"role": "assistant",
                 "content": json.dumps(target, ensure_ascii=False)})
    return {"messages": msgs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", default="data/synthetic")
    ap.add_argument("--save-notes", action="store_true",
                    help="ghi cả .txt + full gold/*.json (mặc định chỉ JSONL train + vài mẫu)")
    ap.add_argument("--sample-notes", type=int, default=20,
                    help="số note lưu .txt+gold để soi (khi không --save-notes)")
    ap.add_argument("--fewshot", action="store_true",
                    help="nhúng few-shot vào mỗi mẫu (mặc định TẮT: mẫu gọn, train nhanh, không cắt target)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    notes_dir = os.path.join(args.out_dir, "notes")
    gold_dir = os.path.join(args.out_dir, "gold")
    os.makedirs(notes_dir, exist_ok=True)
    os.makedirs(gold_dir, exist_ok=True)
    jsonl_path = os.path.join(args.out_dir, "train_sft.jsonl")

    # verify offset đúng: text[start:end] == concept["text"]
    def _check(text, concepts):
        for c in concepts:
            s, e = c["position"]
            assert text[s:e] == c["text"], f"offset lệch: {c['text']!r} vs {text[s:e]!r}"

    type_tot, n_concepts, lens, msg_chars = {}, 0, [], []
    with open(jsonl_path, "w", encoding="utf-8") as jf:
        for i in range(1, args.n + 1):
            text, concepts = generate_note(rng)
            _check(text, concepts)
            ex = to_sft_example(text, concepts, fewshot=args.fewshot)
            jf.write(json.dumps(ex, ensure_ascii=False) + "\n")
            msg_chars.append(sum(len(m["content"]) for m in ex["messages"]))
            n_concepts += len(concepts)
            lens.append(len(text))
            for c in concepts:
                type_tot[c["type"]] = type_tot.get(c["type"], 0) + 1
            # lưu mẫu để soi
            if args.save_notes or i <= args.sample_notes:
                with open(os.path.join(notes_dir, f"{i}.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
                with open(os.path.join(gold_dir, f"{i}.json"), "w", encoding="utf-8") as f:
                    json.dump(concepts, f, ensure_ascii=False, indent=2)

    avg_tok = (sum(msg_chars) / len(msg_chars)) / 3.5    # ước lượng token (~3.5 ký tự/token)
    print(f"✅ Sinh {args.n} note -> {jsonl_path}  (fewshot={args.fewshot})")
    print(f"   Tổng {n_concepts} concept (tb {n_concepts/args.n:.1f}/note), "
          f"độ dài note tb {sum(lens)//len(lens)} ký tự (min {min(lens)}, max {max(lens)})")
    print(f"   Mẫu SFT: tb {sum(msg_chars)//len(msg_chars)} ký tự (~{avg_tok:.0f} token), "
          f"max {max(msg_chars)} ký tự (~{max(msg_chars)/3.5:.0f} token)")
    print("   Phân bố type: " + "  ".join(f"{t}={n}" for t, n in sorted(type_tot.items())))
    kept = args.n if args.save_notes else min(args.sample_notes, args.n)
    print(f"   Lưu {kept} note mẫu (.txt + gold) tại {args.out_dir}")


if __name__ == "__main__":
    main()
