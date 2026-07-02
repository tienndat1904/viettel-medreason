# Phân công nhóm — viettel-medreason (Bài 2, Vòng 1)

3 thành viên, mỗi người sở hữu một mảng module độc lập → làm song song không dẫm chân nhau.
Ranh giới ghép nối là các **hợp đồng interface** cố định trong code; chỉ cần tuân thủ là tích hợp được qua `src/pipeline.py` bất cứ lúc nào.

| Người | Vai trò | Sở hữu module |
|---|---|---|
| **Đạt** (P1) | Extraction & Assertion (lõi mô hình) + chủ repo | `src/extract/*`, `notebooks/`, `src/pipeline.py` |
| **Duckun** (P2) | Linking ICD-10 + RxNorm | `src/kb/*`, `src/linking/*` |
| **Deadpool** (P3) | Data, Eval & Reproducibility/Ops | `src/datagen/*`, `src/eval/*`, `scripts/*`, `Dockerfile`, `data/dev/` |

---

## 👤 Đạt (P1) — Extraction & Assertion
**Hợp đồng đầu ra:** `extract(text) -> [{"text","type","assertions"}]` (KHÔNG offset, KHÔNG candidate)

- Prompt engineering (`prompt.py`): tinh chỉnh few-shot theo style nhiễu thật (mục 1/2/3, `po bid`, `q6h`, dính chữ, `**markdown**`).
- **Tách TÊN_XÉT_NGHIỆM vs KẾT_QUẢ_XÉT_NGHIỆM** cho chuẩn (vd "wbc" vs "11.6").
- Luật assertion:
  - `isNegated`: "Không", "Phủ nhận", "âm tính", "chưa"
  - `isFamily`: "vợ/chồng/bố/mẹ/con/cháu/gia đình/người nhà"
  - `isHistorical`: mục "Thuốc trước khi nhập viện", "bệnh lý mạn/mãn tính", "tiền sử", "(trước đây)"
- **QLoRA fine-tune Qwen2.5-7B** trên synthetic data (Deadpool cấp) — train script + guided-JSON decoding.
- Iterate nhanh bằng Qwen2.5-3B → bản final 7B; cân nhắc Gemma-2-9B để ensemble.
- Với vai trò chủ repo: review/merge PR, quyết định lần submit.

## 👤 Duckun (P2) — Linking ICD-10 + RxNorm
**Hợp đồng đầu ra:** `Linker.link_diagnosis(text, ctx) -> [icd]` · `Linker.link_drug(text, ctx) -> [rxnorm]`

- Tải & chuẩn hóa **ICD-10 tiếng Việt (Bộ Y tế)** + **RxNorm** → `data/kb/*.parquet`.
- Build index **bge-m3** (dense+sparse) + FAISS: `build_icd_index.py`, `build_rxnorm_index.py`.
- ICD: retrieve top-30 → **bge-reranker-v2-m3** → lọc theo confidence → trả 1–3 mã (tin cậy giảm dần).
- RxNorm: hoàn thiện `drug_parser` (hoạt chất + hàm lượng + dạng) → khớp mức **SCD**, trả mã tin cậy nhất trước.

## 👤 Deadpool (P3) — Data, Eval & Reproducibility/Ops
**Hợp đồng đầu ra:** `data/dev/gold/*.json` (dev set có nhãn) + `scorer.py` khớp rubric

- **Sinh synthetic data** (offline, LLM lớn) bắt chước đúng style + gold labels đầy đủ; **dịch i2b2/n2c2** sang tiếng Việt.
- **Dev set ~150 file gán nhãn tay** để P1/P2 đo tiến bộ (ưu tiên ~30 file trong tuần 1).
- Tinh chỉnh `scorer.py` theo công thức chấm chính thức khi có.
- **Reproducibility**: Dockerfile, pin deps, đóng gói weights, test dựng lại trên máy sạch.
- **Chiến lược 5 submit/ngày**: mỗi lần submit phải có giả thuyết + đã đo trên dev.

---

## Giả định đã chốt (không chờ BTC)
Xem `PLAN.md` mục 0.1. Tóm tắt: chấm micro-F1 theo entity (span+type), assertions exact-set, candidates "gold ∈ predicted" → tối ưu span/type, trả candidate ngắn best-first (ICD 1–3, RxNorm 1–2); synthetic offline được dùng; tự tải ICD-10 VN + RxNorm; pipeline chạy gọn & deterministic.

## Lịch 4 tuần

| Tuần | Đạt (P1) | Duckun (P2) | Deadpool (P3) |
|---|---|---|---|
| **T1 02–08/07** | Prompt + few-shot Qwen7B chạy trên dev nhỏ | Tải ICD-10 VN + RxNorm, build index thô | ~30 file dev có nhãn + `scorer` chạy được |
| **T2 09–15/07** | QLoRA v1 + tách TÊN/KẾT_QUẢ + assertion | ICD retrieve + rerank hoàn chỉnh | Synthetic v1 (~1.5k) + dịch i2b2 |
| **T3 16–22/07** | Retrain, xử lý nhiễu/viết tắt | RxNorm SCD parser + tuning candidates | Synthetic mở rộng ~4–5k + dev đủ 150 |
| **T4 23–30/07** | Ensemble + error analysis | Chốt confidence/threshold theo leaderboard | Docker + đóng gói reproducible + chốt submit |

## Nguyên tắc phối hợp
- Code theo **hợp đồng interface** ở trên → tích hợp qua `pipeline.py` bất cứ lúc nào.
- **Không tự đổi schema output** nếu chưa thống nhất cả nhóm.
- Mỗi thay đổi phải **tăng điểm trên dev set** trước khi dùng 1 lượt submit.
- Mỗi người làm nhánh riêng → PR về `main` (Đạt merge).
- Luôn chạy `scripts/package_submission.py` (validate) trước khi nộp — JSON lỗi = 0 điểm file đó.
