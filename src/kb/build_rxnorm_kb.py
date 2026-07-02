"""Build KB RxNorm từ RRF release (NLM) -> data/kb/rxnorm_scd.parquet + brand map.

Tải RxNorm full monthly release (RRF) từ NLM (RxNorm tải tự do, KHÔNG cần UMLS license),
giải nén, đặt thư mục rrf/ (chứa RXNCONSO.RRF, RXNREL.RRF, RXNSAT.RRF) vào data/kb/raw/.
Chạy:
  python src/kb/build_rxnorm_kb.py --rrf data/kb/raw/rrf

Sinh:
  data/kb/rxnorm_scd.parquet          (rxcui, str, tty, ingredient, strength, dose_form)
  data/kb/synonyms/drug_brands_auto.tsv  (SBD/BN -> ingredient, để trộn với dict thủ công)

RXNCONSO.RRF cột: 0 RXCUI,1 LAT,...,11 SAB,12 TTY,13 CODE,14 STR,16 SUPPRESS.
Heuristic hàm lượng/dạng parse từ STR; kiểm tra lại trên vài mẫu SCD trước khi dùng.
CHƯA test với RRF thật (chờ raw).
"""
from __future__ import annotations
import os, re, csv, argparse
from collections import defaultdict
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KEEP_TTY = {"SCD", "SCDF", "SCDC", "IN", "PIN", "BN", "SBD"}

_STRENGTH = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mg/ml|mcg/ml|mg/mg|mcg/mg|mg/g|mg/actuation|mcg/actuation|"
    r"mg|mcg|g|ml|meq|units?/ml|units?|%)", re.I)
_FORMS = ["extended release oral tablet", "delayed release oral tablet",
          "extended release oral capsule", "oral tablet", "oral capsule",
          "oral solution", "oral suspension", "injectable solution", "injection",
          "inhalant solution", "metered dose inhaler", "topical solution",
          "topical", "patch", "cream", "ointment", "lotion", "gel",
          "prefilled syringe", "auto-injector", "chewable tablet",
          "disintegrating tablet", "rectal suppository", "ophthalmic solution"]
_FORM_RE = re.compile("|".join(re.escape(f) for f in _FORMS), re.I)


def _ingredient_from_str(s):
    """Suy hoạt chất từ STR của SCD/SCDC/SBD: bỏ {pack}/[brand], hàm lượng, dạng bào chế."""
    x = re.sub(r"\{[^}]*\}|\[[^\]]*\]", " ", s)   # bỏ {pack} và [brand]
    x = _STRENGTH.sub(" ", x)
    x = _FORM_RE.sub(" ", x)
    x = re.sub(r"\b(in|pack|prefilled|syringe|kit|pen|actuation)\b", " ", x, flags=re.I)
    x = re.sub(r"[0-9]+", " ", x)
    x = re.sub(r"[/,]", " ", x)
    return re.sub(r"\s+", " ", x).strip().lower()


def _read_rrf(path, ncol):
    """Đọc file RRF (phân tách '|'), trả list các list field."""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            parts = line.rstrip("\n").split("|")
            if len(parts) >= ncol:
                rows.append(parts)
    return rows


def _parse_strength(s):
    m = _STRENGTH.search(s)
    return f"{m.group(1)} {m.group(2).lower().replace(' ', '')}" if m else ""


def _parse_form(s):
    low = s.lower()
    for f in _FORMS:
        if f in low:
            return f
    return ""


def build(rrf_dir, out_path, brands_out):
    conso = _read_rrf(os.path.join(rrf_dir, "RXNCONSO.RRF"), 17)
    rel = _read_rrf(os.path.join(rrf_dir, "RXNREL.RRF"), 8)

    # tên hoạt chất theo RXCUI (từ dòng TTY=IN)
    ingr_name = {}
    for r in conso:
        if r[1] == "ENG" and r[12] == "IN" and r[16] != "Y":
            ingr_name[r[0]] = r[14].lower()

    # quan hệ has_ingredient / tradename_of: RXNREL cột 4 RXCUI1, 7 RELA, ... 4? dùng RELA(7)
    # RRF REL: 0 RXCUI1,1 RXAUI1,2 STYPE1,3 REL,4 RXCUI2,5 RXAUI2,6 STYPE2,7 RELA
    prod_to_ingr = defaultdict(set)
    for r in rel:
        rela = r[7] if len(r) > 7 else ""
        if rela in ("has_ingredient", "consists_of", "tradename_of", "has_tradename"):
            c1, c2 = r[0], r[4]
            if c2 in ingr_name:
                prod_to_ingr[c1].add(ingr_name[c2])
            if c1 in ingr_name:
                prod_to_ingr[c2].add(ingr_name[c1])

    recs, brand_rows = [], []
    for r in conso:
        if r[1] != "ENG" or r[16] == "Y":
            continue
        tty, rxcui, s = r[12], r[0], r[14]
        if tty not in KEEP_TTY:
            continue
        if tty in ("IN", "PIN", "BN"):
            ingr = s.lower()
        else:                                     # SCD/SCDC/SCDF/SBD: parse từ STR
            ingr = _ingredient_from_str(s) or s.lower()
        recs.append({
            "rxcui": rxcui, "str": s, "tty": tty, "ingredient": ingr,
            "strength": _parse_strength(s) if tty in ("SCD", "SCDC", "SBD") else "",
            "dose_form": _parse_form(s) if tty in ("SCD", "SCDF", "SBD") else "",
        })
        if tty in ("SBD", "BN"):
            for ing in prod_to_ingr.get(rxcui, []):
                brand_rows.append((s.lower(), ing))

    df = pd.DataFrame(recs).drop_duplicates("rxcui").reset_index(drop=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_parquet(out_path, index=False)
    print(f"[rxnorm] {len(df)} concept ({sorted(df.tty.unique())}) -> {out_path}")

    os.makedirs(os.path.dirname(brands_out), exist_ok=True)
    seen = set()
    with open(brands_out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["alias", "ingredient"])
        for a, ing in brand_rows:
            if (a, ing) not in seen:
                seen.add((a, ing))
                w.writerow([a, ing])
    print(f"[rxnorm] brand map: {len(seen)} dòng -> {brands_out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rrf", required=True, help="thư mục chứa RXNCONSO.RRF, RXNREL.RRF")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "kb", "rxnorm_scd.parquet"))
    ap.add_argument("--brands", default=os.path.join(
        ROOT, "data", "kb", "synonyms", "drug_brands_auto.tsv"))
    args = ap.parse_args()
    build(args.rrf, args.out, args.brands)


if __name__ == "__main__":
    main()
