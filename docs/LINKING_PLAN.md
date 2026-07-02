# KẾ HOẠCH LINKING (P2 — Duckun) — ICD-10 & RxNorm

Chi tiết hóa mục 5.3 của `PLAN.md` cho module `src/kb/*` + `src/linking/*`.
Mục tiêu: điền `Linker.link_diagnosis` / `Linker.link_drug` (đang `NotImplementedError`) → trả candidate hợp lệ, chính xác, xếp theo độ tin cậy giảm dần.

## 0. Quyết định đã chốt
- **ICD-10:** **KB chính = ICD-10-CM (Mỹ)** vì gold dev của P3 dùng hệ mã CM (5–7 ký tự, vd `E83.52`), không phải WHO/BYT. Tên tiếng Việt ghép từ **Danh mục BYT** theo mã cha (`build_icd_cm_kb.py`). *Chưa xác nhận BTC dùng WHO hay CM — nên hỏi thêm; đổi lại chỉ cần trỏ `kb_icd` về BYT.*
- **RxNorm:** trả mã ở **mức SCD trước** (hoạt chất + hàm lượng + dạng, như ví dụ gold `308135`), **fallback SCDC/IN** khi thiếu dạng bào chế hoặc không khớp SCD.
- **Lộ trình:** **v0 lexical/fuzzy trước** (chạy ngay, không cần GPU) → **v1 semantic** (bge-m3 + reranker). De-risk và tăng điểm dần.

## 0.1 Kết quả v0 (đo bằng `src/eval/eval_linking.py` trên 30 file dev gold)
| | hit@k | top1 | ghi chú |
|---|---|---|---|
| **RxNorm (THUỐC)** — chấm theo hoạt chất | **0.915** | 0.915 | parse + brand/typo + SCD; coi như đạt cho v0 |
| **ICD (CHẨN_ĐOÁN)** — exact mã | **0.495** | 0.448 | BYT 0.335 → CM 0.418 → +synonym 0.495 (đã chạm trần lexical) |

**Đòn bẩy tiếp theo cho ICD:** (1) **v1 semantic** bge-m3 khớp text VN với mô tả EN của CM (xử lý ~½ miss là sai ngữ nghĩa); (2) P3 chuẩn hóa **độ sâu mã gold** (đang trộn WHO 4 ký tự & CM 5 ký tự → chặn trần exact-match).

## 1. Hợp đồng interface (KHÔNG đổi — cả nhóm phụ thuộc)
```python
Linker.link_diagnosis(text: str, context: str = "") -> list[str]   # list mã ICD-10, best-first, vd ["K21.0","K21.9"]
Linker.link_drug(text: str, context: str = "") -> list[str]        # list RXCUI string, best-first, vd ["308135"]
```
- Giữ **no-op fallback** khi chưa có KB (trả `[]` — vẫn hợp lệ), như hiện tại.
- `candidates` chỉ áp dụng CHẨN_ĐOÁN (ICD) và THUỐC (RxNorm); type khác `[]` (do `pipeline.py` xử lý).
- **Định dạng mã bắt buộc:** ICD giữ **dấu chấm** (`K21.0`), RxNorm là **chuỗi số** (`"308135"`).

## 2. Nhận định dữ liệu thật (khảo sát 100 file test)
- **THUỐC:** tên tiếng Anh/Latin; **nhiều biệt dược** (prograf→tacrolimus, lasix/laxis→furosemide, coumadin→warfarin, dilaudid→hydromorphone, ranexa→ranolazine, z-pack→azithromycin, combivent, nitro); **lỗi chính tả** (Laxis, asa81); **thiếu dạng bào chế** nhiều; hàm lượng dạng `25mg`, `40 mg/ngày`, `0.4 MG/ML`; lẫn route/tần suất VN + EN (`po`, `bid`, `q4h`, `iv`, `khí dung`, `đường uống`).
  → RxNorm cần: chuẩn hóa **brand→ingredient**, **fuzzy typo**, suy dạng từ đơn vị hàm lượng (`MG/ML`→dung dịch, `MG`→viên).
- **CHẨN_ĐOÁN:** cụm bệnh tiếng Việt phức tạp, nhiều modifier (xơ gan mất bù có tăng áp lực TM cửa; nhiễm khuẩn huyết do tụ cầu vàng nhạy methicillin; ung thư vú trái giai IIIB; giãn phế quản; xuất huyết dưới nhện; bệnh thận đa nang).
  → ICD cần: **semantic matching** + **từ điển đồng nghĩa** cho bệnh phổ biến; trả **nhiều mã** khi có biến thể gần nhau (vd GERD → `K21.0` + `K21.9`).

## 3. Cấu trúc module
```
src/kb/
  build_icd_kb.py       # Danh mục ICD-10 BYT (xlsx/csv) -> data/kb/icd10_vn.parquet + synonyms
  build_rxnorm_kb.py    # RxNorm RRF -> data/kb/rxnorm_scd.parquet + brand->ingredient map
  build_icd_index.py    # [v1] bge-m3 embed -> data/kb/icd10.faiss (+ sparse)
  build_rxnorm_index.py # [v1] bge-m3 embed SCD strings -> data/kb/rxnorm.faiss
src/linking/
  linker.py             # orchestrator; chọn mode lexical|semantic theo config
  drug_parser.py        # parse hoạt chất+hàm lượng+dạng, chuẩn hóa brand/typo (mở rộng bản hiện có)
  icd_match.py          # lexical fuzzy + synonym dict  |  semantic retrieve+rerank
  rxnorm_match.py       # khớp SCD/SCDC/IN từ parse result
data/kb/synonyms/
  icd_synonyms.tsv      # bệnh phổ biến VN -> mã ICD (tay)
  drug_brands.tsv       # biệt dược/typo -> ingredient (tay, bổ sung ngoài RxNorm)
```
Cấu hình thêm vào `configs/config.yaml`:
```yaml
linking:
  backend: lexical          # lexical | semantic  (v0 = lexical)
  icd_fuzzy_threshold: 88   # rapidfuzz token_set_ratio
  rxnorm_fuzzy_threshold: 90
  # (các key top_k / reranker / min_confidence hiện có dùng cho semantic)
```

## 4. Bước 1 — Xây KB (data/kb/*.parquet)  [T1]
### 4.1 ICD-10 VN → `icd10_vn.parquet`
- Tải Danh mục ICD-10 Bộ Y tế (kcb.vn / Thông tư). Cột chuẩn hóa: `code` (giữ dấu chấm), `name_vi`, `name_en?`, `chapter`, `level` (3/4 ký tự).
- Chuẩn hóa text: lower, gộp khoảng trắng, bỏ dấu ngoặc chú thích; tạo cột `name_norm` (bỏ dấu tùy chọn) để fuzzy.
- Tự soạn `icd_synonyms.tsv` cho ~50–100 bệnh hay gặp trong test (tăng huyết áp→I10; đái tháo đường→E11; viêm phổi→J18.9; hen suyễn→J45; xơ gan→K74; GERD→K21.0/K21.9; suy thận cấp→N17; nhiễm khuẩn huyết→A41; rung nhĩ→I48…).
- **Reproducibility:** ship snapshot parquet (nhỏ) + script tải; ghi nguồn/phiên bản trong README.

### 4.2 RxNorm → `rxnorm_scd.parquet` + brand map
- Tải RxNorm full monthly release (RRF, NLM — RxNorm tải tự do). Đọc `RXNCONSO.RRF` (RXCUI, STR, TTY, SAB), `RXNREL.RRF` (quan hệ), `RXNSAT.RRF` (hàm lượng).
- Lọc `TTY ∈ {SCD, SCDC, SCDF, IN, PIN, BN, SBD}`. Bảng chính: `rxcui, str, tty, ingredient_rxcui, strength, dose_form`.
- Dựng `drug_brands.tsv`: SBD/BN → IN (qua RXNREL `tradename_of`/`has_ingredient`) + bổ sung tay các biệt dược/typo thấy trong test (prograf, lasix/laxis, coumadin, dilaudid, ranexa, z-pack, nitro…).
- Ship snapshot parquet đã lọc (gọn) + script build; nêu nguồn trong README.

## 5. Bước 2 — v0 Lexical linker (không GPU)  [T1]
### 5.1 RxNorm (`drug_parser.py` + `rxnorm_match.py`)
1. `parse_drug`: tách `ingredient`, `strengths` (chuẩn hóa `MG/ML`, `mg`, `,`→`.`), `dose_form` (suy từ đơn vị + cue `po`/`đường uống`/`nebs`/`susp`); loại route/tần suất (đã có NOISE list — mở rộng thêm `khí dung`, `tiêm`, `truyền`).
2. Chuẩn hóa brand→ingredient (drug_brands.tsv) + fuzzy typo (rapidfuzz ≥ threshold) trên tên hoạt chất.
3. Khớp RxNorm theo tầng: **SCD** (ingredient+strength+form) → **SCDC** (ingredient+strength) → **IN** (ingredient). Trả RXCUI của tầng khớp cao nhất trước.
4. Xác thực trên 5 cặp gold từ Info.txt: `amlodipine 10 mg`→308135, `aspirin 81 mg`→243670, `Chlorpheniramine 0.4 MG/ML`→360047, `Capsaicin 0.38 MG/ML`→1660761.

### 5.2 ICD (`icd_match.py` lexical)
1. Chuẩn hóa text chẩn đoán; tra `icd_synonyms.tsv` trước (hit → trả ngay, độ tin cậy cao).
2. Fuzzy `token_set_ratio` với `name_vi`/`name_norm`; lấy các mã ≥ `icd_fuzzy_threshold`, gom biến thể cùng gốc (vd K21.x) → trả top 1–3 best-first.

## 6. Bước 3 — v1 Semantic linker (GPU)  [T2–T3]
### 6.1 ICD hybrid
- `build_icd_index.py`: bge-m3 (dense + sparse) embed `name_vi` → FAISS.
- `icd_match.py` (semantic): embed `text` + ngữ cảnh câu → retrieve top-`icd_top_k_retrieve` (30) → **bge-reranker-v2-m3** rerank kèm ngữ cảnh → lọc `min_confidence` → top `icd_top_k_return` (1–3). Synonym dict override khi trùng.
### 6.2 RxNorm fallback embedding
- `build_rxnorm_index.py`: embed chuỗi SCD → FAISS. Khi parse-match thất bại (tên lạ/typo nặng) → embedding-match làm fallback, vẫn ưu tiên SCD.

## 7. Đánh giá (bắt buộc trước mỗi thay đổi)
- Phối hợp P3: tạo **mini gold linking** ~30–50 mention (thuốc + chẩn đoán) từ test set, gán mã ICD/RxNorm tay → dùng chỉ số `candidate hit (gold∈pred)` của `scorer.py`.
- Theo dõi tách biệt **precision vs recall của candidates** để chỉnh số mã trả về (posture chốt theo leaderboard ở T4).
- Bộ hồi quy nhỏ: 5 cặp gold trong Info.txt luôn phải đúng.

## 8. Mốc thời gian (khớp lịch T1–T4 trong TEAM.md)
| Tuần | Việc P2 | Đầu ra |
|---|---|---|
| **T1 02–08/07** | Tải+chuẩn hóa ICD-10 VN + RxNorm → parquet; v0 lexical (drug_parser hoàn chỉnh + fuzzy ICD + synonym/brand dict); mini gold ~30 | `link_*` trả candidate khác rỗng, hợp lệ → góp cho submission #1 |
| **T2 09–15/07** | `build_icd_index` + bge-m3 retrieve + reranker (ICD semantic) | ICD F1 candidate tăng rõ trên dev |
| **T3 16–22/07** | Hoàn thiện RxNorm SCD parser + fallback embedding; tuning thứ tự/ngưỡng candidate | RxNorm hit@k ổn định |
| **T4 23–30/07** | Chốt confidence/threshold & số mã trả theo leaderboard | Bản linking cuối |

## 9. Rủi ro & giảm thiểu
- **Mô tả ICD-10 VN lệch cách diễn đạt** → synonym dict + reranker ngữ cảnh.
- **Suy dạng bào chế sai (RxNorm)** → tầng fallback SCDC/IN, không ép SCD cứng.
- **Bản quyền/reproducibility** → ship snapshot KB đã lọc (gọn, ta tạo) + script build; ghi rõ nguồn & phiên bản trong README; không phụ thuộc API online (RxNav) lúc inference.
- **Precision tụt do trả nhiều mã** → mặc định trả ít (ICD 1–3, RxNorm 1), tăng chỉ khi dev cho thấy lợi.
