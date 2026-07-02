"""Xuất HTML review cho dev set: tô màu span theo type ngay trên văn bản gốc để
người review soát nhanh (đúng span? đúng type? assertion/candidate hợp lý?).

Dùng gián tiếp qua make_dev.py (--html), hoặc trực tiếp:
  python src/datagen/build_review_html.py --gold data/dev/gold --input data/test/input --out data/dev/review
"""
from __future__ import annotations
import os, sys, json, argparse, glob, re, html as _html

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

COLORS = {
    "TRIỆU_CHỨNG":        ("#fde68a", "#92400e"),  # vàng
    "TÊN_XÉT_NGHIỆM":     ("#bfdbfe", "#1e3a8a"),  # xanh dương
    "KẾT_QUẢ_XÉT_NGHIỆM": ("#c7d2fe", "#3730a3"),  # tím nhạt
    "CHẨN_ĐOÁN":          ("#fecaca", "#991b1b"),  # đỏ
    "THUỐC":              ("#bbf7d0", "#065f46"),  # xanh lá
}
SHORT = {"TRIỆU_CHỨNG": "TC", "TÊN_XÉT_NGHIỆM": "XN", "KẾT_QUẢ_XÉT_NGHIỆM": "KQ",
         "CHẨN_ĐOÁN": "DX", "THUỐC": "RX"}


def _esc(s: str) -> str:
    return _html.escape(s).replace("\n", "<br>")


def _render_text(text: str, concepts: list[dict]) -> str:
    """Chèn <mark> vào văn bản. Bỏ qua span lồng nhau (chỉ tô span ngoài cùng)."""
    spans = sorted(concepts, key=lambda c: (c["position"][0], -c["position"][1]))
    out, cur, last_end = [], 0, 0
    for i, c in enumerate(spans):
        s, e = c["position"]
        if s < last_end:  # lồng/chồng span đã tô -> bỏ để không vỡ HTML
            continue
        out.append(_esc(text[cur:s]))
        fg, _ = COLORS.get(c["type"], ("#e5e7eb", "#111"))
        tip = f'{c["type"]}'
        if c.get("assertions"):
            tip += " | " + ",".join(c["assertions"])
        if c.get("candidates"):
            tip += " | " + ",".join(c["candidates"])
        out.append(
            f'<mark class="c" style="background:{fg}" title="{_esc(tip)}">'
            f'{_esc(text[s:e])}'
            f'<sup class="tag">{SHORT.get(c["type"], "?")}</sup></mark>')
        cur = last_end = e
    out.append(_esc(text[cur:]))
    return "".join(out)


def _render_table(concepts: list[dict]) -> str:
    rows = []
    for c in sorted(concepts, key=lambda x: x["position"][0]):
        fg, tc = COLORS.get(c["type"], ("#e5e7eb", "#111"))
        rows.append(
            "<tr>"
            f'<td class="pos">{c["position"][0]}–{c["position"][1]}</td>'
            f'<td><span class="pill" style="background:{fg};color:{tc}">{c["type"]}</span></td>'
            f'<td>{_esc(c["text"])}</td>'
            f'<td>{_esc(", ".join(c.get("assertions", [])))}</td>'
            f'<td>{_esc(", ".join(c.get("candidates", [])))}</td>'
            "</tr>")
    return "\n".join(rows)


def _page(name: str, text: str, concepts: list[dict]) -> str:
    counts = {}
    for c in concepts:
        counts[c["type"]] = counts.get(c["type"], 0) + 1
    legend = " ".join(
        f'<span class="pill" style="background:{COLORS[t][0]};color:{COLORS[t][1]}">'
        f'{t} ({counts.get(t,0)})</span>' for t in COLORS)
    return f"""<!doctype html><meta charset="utf-8">
<title>dev {name}</title>
<style>
 body{{font:14px/1.6 system-ui,Segoe UI,Arial;margin:0;background:#f8fafc;color:#0f172a}}
 header{{position:sticky;top:0;background:#fff;border-bottom:1px solid #e2e8f0;padding:10px 16px;z-index:5}}
 .wrap{{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:16px;align-items:start}}
 @media(max-width:1100px){{.wrap{{grid-template-columns:1fr}}}}
 .card{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:14px}}
 .doc{{white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,Consolas,monospace;font-size:13px}}
 mark.c{{border-radius:4px;padding:0 2px;position:relative}}
 sup.tag{{font-size:8px;font-weight:700;opacity:.6;margin-left:1px}}
 table{{border-collapse:collapse;width:100%;font-size:12.5px}}
 th,td{{border-bottom:1px solid #eef2f7;padding:4px 6px;text-align:left;vertical-align:top}}
 th{{position:sticky;top:0;background:#f1f5f9}}
 .pos{{color:#64748b;white-space:nowrap;font-family:monospace}}
 .pill{{border-radius:999px;padding:1px 8px;font-size:11px;white-space:nowrap}}
 .legend .pill{{margin-right:6px}}
 nav a{{margin-right:8px}}
</style>
<header>
 <b>Dev review — {name}.txt</b> · {len(concepts)} concept · {len(text)} ký tự
 <div class="legend" style="margin-top:6px">{legend}</div>
</header>
<div class="wrap">
 <div class="card"><div class="doc">{_render_text(text, concepts)}</div></div>
 <div class="card"><table>
   <tr><th>pos</th><th>type</th><th>text</th><th>assertions</th><th>candidates</th></tr>
   {_render_table(concepts)}
 </table></div>
</div>"""


def write_review(out_dir: str, built: list[tuple[str, str, list[dict]]]):
    """built = [(name, text, concepts), ...]"""
    os.makedirs(out_dir, exist_ok=True)
    items = sorted(built, key=lambda x: int(re.sub(r"\D", "", x[0]) or 0))
    for name, text, concepts in items:
        with open(os.path.join(out_dir, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(_page(name, text, concepts))
    # index
    links = " ".join(f'<a href="{n}.html">{n}</a>' for n, _, _ in items)
    total = sum(len(c) for _, _, c in items)
    idx = (f"<!doctype html><meta charset='utf-8'><title>dev review</title>"
           f"<style>body{{font:15px system-ui;margin:24px;line-height:2}}"
           f"a{{display:inline-block;min-width:34px;text-align:center;"
           f"border:1px solid #cbd5e1;border-radius:6px;padding:2px 6px;text-decoration:none}}</style>"
           f"<h2>Dev set review — {len(items)} file · {total} concept</h2>"
           f"<p>Mở từng file để soát span/type/assertion/candidate:</p><p>{links}</p>")
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/dev/gold")
    ap.add_argument("--input", default="data/test/input")
    ap.add_argument("--out", default="data/dev/review")
    args = ap.parse_args()
    built = []
    for fp in glob.glob(os.path.join(args.gold, "*.json")):
        name = os.path.splitext(os.path.basename(fp))[0]
        tp = os.path.join(args.input, f"{name}.txt")
        if not os.path.exists(tp):
            continue
        text = open(tp, encoding="utf-8").read()
        concepts = json.load(open(fp, encoding="utf-8"))
        built.append((name, text, concepts))
    write_review(args.out, built)
    print(f"📝 {len(built)} trang -> {args.out}/index.html")


if __name__ == "__main__":
    main()
