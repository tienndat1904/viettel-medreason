# data/kb/raw/ — file KB gốc (KHÔNG commit)

Thư mục chứa dữ liệu gốc tải về để build KB. Nội dung bị `.gitignore`
(dung lượng lớn / chỉ ship bản parquet đã lọc + script build). Chỉ README này được commit.

## Cần đặt gì ở đây

### 1. RxNorm (RRF) → `data/kb/raw/rrf/`
- Tải **RxNorm Current Prescribable Content** (không cần đăng nhập) từ:
  https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html
  → file `RxNorm_full_prescribe_<MMDDYYYY>.zip`.
  *(Hoặc bản Full: https://download.nlm.nih.gov/umls/kss/rxnorm/RxNorm_full_current.zip — cần tài khoản UMLS/UTS.)*
- Giải nén, copy thư mục `rrf/` (chứa `RXNCONSO.RRF`, `RXNREL.RRF`, `RXNSAT.RRF`) vào `data/kb/raw/rrf/`.
- Build:  `python src/kb/build_rxnorm_kb.py --rrf data/kb/raw/rrf`

### 2. ICD-10 tiếng Việt → `data/kb/raw/icd10_byt.xlsx`
- Tải Excel danh mục theo **Quyết định 4469/QĐ-BYT** (cột Mã / Tên tiếng Việt / Tên tiếng Anh):
  https://luatvietnam.vn/y-te/quyet-dinh-4469-phan-loai-quoc-te-ma-hoa-benh-tat-nguyen-nhan-tu-vong-icd-10-193069-d1.html
  (tra cứu: https://icd.kcb.vn/)
- Lưu thành `data/kb/raw/icd10_byt.xlsx`.
- Build:  `python src/kb/build_icd_kb.py --raw data/kb/raw/icd10_byt.xlsx`

Sau khi build, KB thật ở `data/kb/icd10_vn.parquet` + `data/kb/rxnorm_scd.parquet`
sẽ được Linker tự ưu tiên dùng (thay cho seed).
