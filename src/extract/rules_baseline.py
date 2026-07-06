"""Baseline trích xuất bằng luật (gazetteer + regex).

MỤC ĐÍCH: có submission HỢP LỆ ngay và kiểm thử toàn bộ đường ống
(offset → assertion → linking → validate). Chất lượng thật sẽ do LLM extractor thay thế.
Trả về list {text, type} — assertion & position do module chuyên trách xử lý sau.

THUỐC/CHẨN_ĐOÁN dùng gazetteer nạp lazy từ KB (tên hoạt chất RxNorm + brand map;
term trong icd_synonyms.tsv) + luật "chẩn đoán ..." — đủ để linking P2 kích hoạt.
"""
from __future__ import annotations
import os, re

# --- Gazetteer tối giản (mở rộng dần) ---
SYMPTOMS = [
    # cụm dài để TRƯỚC (khớp ưu tiên khi quét theo thứ tự)
    "khó thở khi gắng sức", "cảm giác thắt chặt ngực", "khó chịu vùng ngực",
    "giảm dung nạp gắng sức", "sợ ánh sáng", "khô âm đạo", "thiếu oxy",
    # --- dấu hiệu thực thể bác sĩ khám (BTC forum: KHÔNG phân loại triệu chứng
    #     => sign thực thể vẫn tính TRIỆU_CHỨNG). Cụm dài trước cụm ngắn cùng gốc. ---
    "rì rào phế nang giảm", "thông khí phổi giảm", "phản ứng thành bụng",
    "đề kháng thành bụng", "cảm ứng phúc mạc", "dấu hiệu thần kinh khu trú",
    "phản xạ gân xương tăng", "tĩnh mạch cổ nổi", "phù mềm ấn lõm",
    "rút lõm lồng ngực", "niêm mạc nhợt", "sưng nóng đỏ", "gan lách to",
    "yếu nửa người", "liệt nửa người", "nhịp tim không đều", "thổi tâm thu",
    "thổi tâm trương", "tiếng thổi", "ran nổ", "ran ẩm", "ran rít", "ran ngáy",
    "gan to", "lách to", "hạch to", "cứng gáy", "gõ đục", "bụng chướng",
    "chướng bụng", "thở nhanh", "thở rít", "ấn đau", "tím tái", "vàng mắt",
    # --- triệu chứng lâm sàng chuẩn hay gặp (tổng quát hóa được) ---
    "khó thở khi nằm đầu thấp", "khó thở khi nằm", "phù gai thị", "phù chi dưới",
    "đau bụng dữ dội", "đau đầu kéo dài", "nghẹt ngực", "nuốt vướng", "nuốt nghẹn",
    "giọng khàn", "chảy máu mũi", "chảy máu cam", "ho ra máu", "khạc đờm",
    "đau âm ỉ", "lú lẫn", "lơ mơ",
    "đau thượng vị", "đánh trống ngực", "nôn ra máu", "phù hai bên", "ăn uống kém",
    "vã mồ hôi", "đổ mồ hôi", "mất ý thức", "ngất xỉu", "chóng mặt", "mệt mỏi",
    "khó thở", "đau ngực", "đau bụng", "đau đầu", "đau lưng", "đau khớp", "đau cơ",
    "đau họng", "buồn nôn", "tiêu chảy", "táo bón", "khò khè", "tiếng rít", "ớn lạnh",
    "khó nuốt", "khó tiêu", "ợ hơi", "ợ chua", "đầy hơi", "khó chịu", "ảo giác",
    "sổ mũi", "nghẹt mũi", "ho khan", "ho đờm", "khàn tiếng", "sụt cân", "chán ăn",
    "mất ngủ", "co giật", "tê bì", "vàng da", "phát ban", "ban đỏ", "chảy máu",
    "tiểu buốt", "tiểu rắt", "tiểu khó", "hoa mắt", "run tay", "yếu cơ", "sưng",
    "nôn", "sốt", "ho", "phù", "đờm", "ngứa",
]
LAB_NAMES = [
    # chẩn đoán hình ảnh / thủ thuật
    "chụp x-quang ngực", "chụp x-quang", "x-quang ngực", "x-quang", "x quang",
    "siêu âm tim qua thành ngực", "siêu âm bụng", "siêu âm tim", "siêu âm", "doppler",
    "chụp cắt lớp vi tính sọ não", "chụp ct ngực", "chụp ct sọ não",
    "chụp cắt lớp vi tính", "chụp ct", "ct scan",
    "chụp cộng hưởng từ", "mri", "điện tâm đồ", "ecg", "monitor holter", "holter",
    "chụp hida", "nội soi", "sinh thiết", "chọc dò dịch não tủy", "thông tim trái",
    "thông tim",
    # panel / xét nghiệm
    "tổng phân tích nước tiểu", "phân tích nước tiểu", "công thức máu", "sinh hóa máu",
    "chức năng gan", "chức năng thận", "cấy máu", "cấy nước tiểu", "khí máu động mạch",
    # chỉ số máu / marker
    "wbc", "ast", "alt", "troponin", "cea", "creatinine", "bilirubin toàn phần",
    "bilirubin", "spo2", "canxi toàn phần", "canxi ion hóa", "canxi", "canci",
    "hgb", "hct", "plt", "neut", "lyph",
    "bạch cầu", "phosphatase kiềm", "kali", "natri", "lactate", "lymphocyte",
    "amylase", "lipase",
    "glucose", "hba1c", "ure", "crp", "inr", "bnp", "alp", "albumin", "ferritin",
    "procalcitonin", "d-dimer", "cholesterol", "triglyceride",
]

# số + đơn vị kết quả hợp lệ (gộp vào text): %, °C, range, nồng độ...
_RESULT_UNIT = (r"(?:\s*(?:%|°?[cCfF]\b|mmol/l|mg/dl|ng/ml|ng/dl|ng|g/l|meq/l|"
                r"mm[hH]g|bpm|mm|cm|/min|x?10\^?\d*|[kK]/[uµ]l|[gG]/[dD][lL]))?")
_num = re.compile(r"(?<![\w.])(\d[\d.,]*(?:\s*[-x×]\s*\d[\d.,]*)?)" + _RESULT_UNIT)
# số theo sau bởi đơn vị THỜI GIAN/LIỀU -> không phải kết quả xét nghiệm
_DUR_AFTER = re.compile(r"^\s*(tu[aầ]n|ngày|ngay|tháng|thang|năm|nam|giờ|gio|phút|phut|"
                        r"tuổi|tuoi|lần|lan|viên|vien|gói|goi|mg|ml|mcg|g)\b", re.I)
_RESULT_CUE = (":", "là ", "kết quả", "chỉ số", "nồng độ", "mức ", "kqxn", "chỉ điểm",
               "nhiệt độ")

# ---- đường dẫn KB mặc định (khớp configs/config.yaml) ----
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KB_RXNORM = os.path.join(_ROOT, "data/kb/rxnorm_scd.parquet")
_SYN_ICD = os.path.join(_ROOT, "data/kb/synonyms/icd_synonyms.tsv")
_BRANDS = [os.path.join(_ROOT, "data/kb/synonyms/drug_brands_auto.tsv"),
           os.path.join(_ROOT, "data/kb/synonyms/drug_brands.tsv")]

# hoạt chất là từ tiếng Anh phổ thông -> bỏ để tránh dương tính giả
_DRUG_STOP = {"water", "oxygen", "air", "alcohol", "iron", "zinc", "gold", "lead",
              "salt", "tar", "coal", "honey", "starch", "sugar", "nicotine", "caffeine",
              # enzyme/acid amin = xét nghiệm, KHÔNG phải thuốc (tránh type-confusion)
              "amylase", "lipase", "aspartate", "alanine", "phosphatase", "globulin",
              "aminotransferase", "creatine", "lactate", "albumin"}
# cụm hay theo sau "chẩn đoán" nhưng không phải tên bệnh
_DX_STOP = {"khác", "hình ảnh", "sơ bộ", "phân biệt", "xác định", "ban đầu",
            "cuối cùng", "chính", "kèm theo", "và điều trị"}

# đuôi liều/đường dùng ngay sau tên thuốc (định dạng danh mục thuốc EN)
_DOSE_TAIL = re.compile(
    r"(?:\s+(?:\d[\d.,\-]*\s*(?:%|mg/ml|mcg/ml|mg/dl|mmol|mg|ml|mcg|g|iu|units?)?"
    r"|mg|ml|mcg|po|iv|im|sc|sq|bid|tid|qid|qd|qod|daily|qhs|qam|qpm|q\d+h"
    r"|:?prn|xl|er|sr|cr|oral|tablet|cap|caps|suspension|nebs?|inhaler"
    r"|hằng\ ngày|đường\ uống|khí\ dung|tiêm|truyền|viên|nang|gói))+",
    re.IGNORECASE)

_CACHE = {}


def _load_gazetteers():
    if _CACHE:
        return _CACHE
    drugs, dx = set(), set()
    try:
        import pandas as pd
        if os.path.exists(_KB_RXNORM):
            kb = pd.read_parquet(_KB_RXNORM, columns=["ingredient"])
            for ing in kb["ingredient"].dropna().astype(str):
                ing = ing.strip().lower()
                if len(ing) >= 4 and ing not in _DRUG_STOP:
                    drugs.add(ing)
        for bp in _BRANDS:
            if os.path.exists(bp):
                with open(bp, encoding="utf-8") as f:
                    for ln in f:
                        ln = ln.strip()
                        if not ln or ln.startswith("#") or ln.lower().startswith("brand"):
                            continue
                        brand = ln.split("\t")[0].strip().lower()
                        if len(brand) >= 3 and brand not in _DRUG_STOP:
                            drugs.add(brand)
    except Exception as e:  # noqa
        print(f"[rules] không nạp được gazetteer thuốc: {e}")
    if os.path.exists(_SYN_ICD):
        with open(_SYN_ICD, encoding="utf-8") as f:
            for ln in f:
                ln = ln.rstrip("\n")
                if not ln or ln.startswith("#") or ln.lower().startswith("term"):
                    continue
                term = ln.split("\t")[0].strip()
                if len(term) >= 4:
                    dx.add(term.lower())
    # dài trước để ưu tiên khớp cụm dài nhất
    _CACHE["drugs"] = sorted(drugs, key=len, reverse=True)
    _CACHE["dx"] = sorted(dx, key=len, reverse=True)
    return _CACHE


def _find_terms(low, text, terms, ttype, taken):
    """Khớp từng term (whole-word cho token ASCII), nới đuôi liều với THUỐC."""
    out = []
    for term in terms:
        start = 0
        while True:
            i = low.find(term, start)
            if i < 0:
                break
            j = i + len(term)
            start = j
            # biên trái/phải: không cắt giữa token chữ-số
            lc = low[i - 1] if i > 0 else " "
            rc = low[j] if j < len(low) else " "
            if (lc.isalnum() and lc.isascii()) or (rc.isalnum() and rc.isascii()):
                continue
            if any(a < j and i < b for a, b in taken):   # đã bị term dài hơn chiếm
                continue
            e = j
            if ttype == "THUỐC":
                m = _DOSE_TAIL.match(text[j:])
                if m and m.end() > 0:
                    e = j + m.end()
            taken.append((i, e))
            out.append({"text": text[i:e].strip(), "type": ttype})
    return out


def extract(text: str) -> list[dict]:
    low = text.lower()
    found = []

    # triệu chứng — word-boundary để "ho" không khớp trong "cho/khó", "phù" trong "phù hợp"
    sym_taken = []
    for kw in SYMPTOMS:                                  # cụm dài trước -> chiếm chỗ, tránh trùng lồng
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", low):
            if any(a < m.end() and m.start() < b for a, b in sym_taken):
                continue
            sym_taken.append((m.start(), m.end()))
            found.append({"text": text[m.start():m.end()], "type": "TRIỆU_CHỨNG"})

    # tên xét nghiệm (span chồng lấn đã được resolve_offsets ở pipeline dedup)
    for kw in LAB_NAMES:
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", low):
            found.append({"text": text[m.start():m.end()], "type": "TÊN_XÉT_NGHIỆM",
                          "assertions": []})

    # kết quả xét nghiệm (số): gần tên xét nghiệm / dấu ":" / cue kết quả,
    # loại số theo sau bởi đơn vị thời gian/liều (3 tuần, 325 mg).
    for m in _num.finditer(text):
        raw = m.group(1)
        # bỏ số thứ tự liệt kê "2.", "3." (toàn match là 1-2 chữ số + dấu chấm, không phải kết quả)
        if re.fullmatch(r"\d{1,2}\.", raw):
            continue
        has_unit = bool(m.group(0)[len(raw):].strip())
        after = low[m.end():m.end() + 10]
        if not has_unit and _DUR_AFTER.match(after):
            continue
        pre = low[max(0, m.start() - 28):m.start()]
        if any(k in pre for k in _RESULT_CUE) or any(ln in pre for ln in LAB_NAMES):
            txt = text[m.start():m.end()].strip().strip(",.;")   # bỏ dấu câu đuôi: "99," -> "99"
            if txt:
                found.append({"text": txt, "type": "KẾT_QUẢ_XÉT_NGHIỆM", "assertions": []})

    # thuốc + chẩn đoán (gazetteer từ KB) — để linking P2 chạy
    gz = _load_gazetteers()
    taken = []
    found += _find_terms(low, text, gz["drugs"], "THUỐC", taken)
    found += _find_terms(low, text, gz["dx"], "CHẨN_ĐOÁN", taken)

    # chẩn đoán theo cue "chẩn đoán mắc/là <cụm>" — yêu cầu mắc/là để tránh
    # "chẩn đoán hình ảnh", "chẩn đoán khác" (chẩn đoán là danh từ, không phải cue)
    for m in re.finditer(r"chẩn đoán(?:\s+xác định)?\s+(?:mắc|là)\s+(?:bệnh\s+)?"
                         r"([^.;,\n\d]{4,80})", low):
        s, e = m.start(1), m.end(1)
        phrase = text[s:e].strip()
        if phrase and phrase.lower() not in _DX_STOP \
                and not any(a < e and s < b for a, b in taken):
            taken.append((s, e))
            found.append({"text": phrase, "type": "CHẨN_ĐOÁN"})

    return found
