"""Build KB ICD-10-CM (Mỹ) song ngữ -> data/kb/icd10cm.parquet.

Gold của bài toán dùng ICD-10-CM (mã 5-7 ký tự, vd E83.52). KB này là KHÔNG GIAN
MÃ CHÍNH cho CHẨN_ĐOÁN. Tên tiếng Việt lấy từ BYT (WHO) theo mã cha gần nhất để
vẫn match được văn bản tiếng Việt; tên tiếng Anh là mô tả CM gốc.

Nguồn: CDC ICD-10-CM order file (public domain).
  data/kb/raw/icd10cm/icd10cm-order-2026.txt
Chạy:
  python src/kb/build_icd_cm_kb.py \
    --order data/kb/raw/icd10cm/icd10cm-order-2026.txt \
    --byt data/kb/icd10_vn.parquet
"""
from __future__ import annotations
import os, argparse
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _dot(code: str) -> str:
    """Chèn dấu chấm sau 3 ký tự đầu: A000 -> A00.0, I7090 -> I70.90, A00 -> A00."""
    return code if len(code) <= 3 else f"{code[:3]}.{code[3:]}"


def _parse_order(path):
    """Đọc order file fixed-width: order(0:5) code(6:13) flag(14) short(16:76) long(77:)."""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 16:
                continue
            code = line[6:13].strip()
            flag = line[14:15].strip()
            long_desc = line[77:].strip() or line[16:76].strip()
            if code:
                rows.append((_dot(code), long_desc, flag == "1"))
    return pd.DataFrame(rows, columns=["code", "name_en", "billable"])


def _vi_lookup(byt_path):
    """Trả hàm code(CM, có chấm) -> tên tiếng Việt của mã cha gần nhất trong BYT."""
    byt = pd.read_parquet(byt_path)
    vi = dict(zip(byt["code"].astype(str), byt["name_vi"].astype(str)))

    def ancestors(code):
        yield code                      # khớp đúng
        d = code.replace(".", "")
        for n in (4, 3):                # cha 4 ký tự rồi 3 ký tự
            if len(d) > n:
                p = d[:n]
                yield (f"{p[:3]}.{p[3:]}" if n == 4 else p)

    def get(code):
        for a in ancestors(code):
            if a in vi and vi[a]:
                return vi[a]
        return ""
    return get


def build(order_path, byt_path, out_path):
    df = _parse_order(order_path)
    get_vi = _vi_lookup(byt_path)
    df["name_vi"] = df["code"].map(get_vi)
    df["level"] = df["code"].str.replace(".", "", regex=False).str.len()
    df["chapter"] = df["code"].str[0]
    df = df[["code", "name_vi", "name_en", "billable", "level", "chapter"]]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_parquet(out_path, index=False)
    have_vi = (df["name_vi"] != "").sum()
    print(f"[icd-cm] {len(df)} mã CM ({df.billable.sum()} billable) -> {out_path}")
    print(f"[icd-cm] có tên tiếng Việt (ghép từ BYT): {have_vi}/{len(df)} = {have_vi/len(df):.1%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--order", default=os.path.join(
        ROOT, "data/kb/raw/icd10cm/icd10cm-order-2026.txt"))
    ap.add_argument("--byt", default=os.path.join(ROOT, "data/kb/icd10_vn.parquet"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data/kb/icd10cm.parquet"))
    args = ap.parse_args()
    build(args.order, args.byt, args.out)


if __name__ == "__main__":
    main()
