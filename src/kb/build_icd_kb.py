"""Build KB ICD-10 tiếng Việt từ Danh mục Bộ Y tế -> data/kb/icd10_vn.parquet.

Đặt file gốc (xls/xlsx) rồi chạy:
  python src/kb/build_icd_kb.py --raw data/kb/raw/icd10_byt.xls

Hỗ trợ 2 chế độ đọc:
  1) LAYOUT CHÍNH THỨC (QĐ 4469, sheet 'ICD10'): tự tìm hàng header chứa
     'MÃ BỆNH' + 'TÊN BỆNH', lấy cột MÃ BỆNH / TÊN BỆNH / DISEASE NAME.
  2) FALLBACK heuristic: tự dò cột mã & tên nếu không nhận ra layout chính thức.
Chuẩn hóa: giữ dấu chấm trong mã (A00.0), tên VN ở name_vi, tên EN ở name_en.
"""
from __future__ import annotations
import os, re, argparse
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# mã ICD hợp lệ: A00, A00.0, A00.11, U07.1 ...
_CODE_RE = re.compile(r"^[A-Z]\d{2}(\.\d+)?$")


# ---------- layout chính thức QĐ 4469 ----------
def _load_official(path):
    xl = pd.ExcelFile(path)
    sheet = "ICD10" if "ICD10" in xl.sheet_names else xl.sheet_names[0]
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str).fillna("")
    hdr = cols = None
    for i in range(min(20, len(raw))):
        vals = [str(x).strip().upper() for x in raw.iloc[i].tolist()]
        if "MÃ BỆNH" in vals and "TÊN BỆNH" in vals:
            hdr, cols = i, vals
            break
    if hdr is None:
        return None
    df = raw.iloc[hdr + 1:].reset_index(drop=True)
    cj = cols.index("MÃ BỆNH")
    vj = cols.index("TÊN BỆNH")
    ej = cols.index("DISEASE NAME") if "DISEASE NAME" in cols else None
    out = pd.DataFrame({
        "code": df.iloc[:, cj].astype(str).str.strip().str.upper(),
        "name_vi": df.iloc[:, vj].astype(str).str.strip(),
        "name_en": (df.iloc[:, ej].astype(str).str.strip() if ej is not None else ""),
    })
    print(f"[icd] layout chính thức: sheet='{sheet}', header dòng {hdr}, "
          f"cột code={cj} vi={vj} en={ej}")
    return out


# ---------- fallback heuristic ----------
def _pick_col(cols, keys):
    for c in cols:
        if any(k in str(c).lower() for k in keys):
            return c
    return None


def _code_ratio(series, sample=300):
    vals = series.dropna().astype(str).str.strip().head(sample)
    if len(vals) == 0:
        return 0.0
    return sum(bool(_CODE_RE.match(v.upper())) for v in vals) / len(vals)


def _load_generic(path):
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path, dtype=str).fillna("")
    else:
        df = pd.read_csv(path, dtype=str, sep=None, engine="python").fillna("")
    code_col = max(df.columns, key=lambda c: _code_ratio(df[c]))
    name_col = _pick_col(df.columns, ["tên tiếng việt", "tên bệnh", "tên", "vietnamese"])
    en_col = _pick_col(df.columns, ["disease name", "tiếng anh", "english"])
    print(f"[icd] fallback heuristic: code='{code_col}' name='{name_col}'")
    return pd.DataFrame({
        "code": df[code_col].astype(str).str.strip().str.upper(),
        "name_vi": df[name_col].astype(str).str.strip() if name_col else "",
        "name_en": df[en_col].astype(str).str.strip() if en_col else "",
    })


def build(raw_path, out_path):
    out = None
    if raw_path.lower().endswith((".xls", ".xlsx")):
        out = _load_official(raw_path)
    if out is None:
        out = _load_generic(raw_path)

    out = out[out["code"].str.match(_CODE_RE)].drop_duplicates("code").reset_index(drop=True)
    out["level"] = out["code"].str.replace(".", "", regex=False).str.len().map(
        lambda n: 3 if n == 3 else 4)
    out["chapter"] = out["code"].str[0]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out.to_parquet(out_path, index=False)
    n3 = (out.level == 3).sum()
    print(f"[icd] {len(out)} mã ({n3} mã 3 ký tự, {len(out) - n3} mã chi tiết) -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True, help="file Danh mục ICD-10 BYT (xls/xlsx/csv)")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "kb", "icd10_vn.parquet"))
    args = ap.parse_args()
    build(args.raw, args.out)


if __name__ == "__main__":
    main()
