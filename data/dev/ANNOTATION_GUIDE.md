# Hướng dẫn gán nhãn DEV SET — viettel-medreason (Bài 2)

Mục tiêu: tạo **gold labels** nhất quán để P1/P2 đo tiến bộ offline (`scorer.py`).
Đây là *diễn giải của nhóm* (BTC chưa công bố rubric) → ghi rõ quy ước, **v1, có thể sửa**.

> Người gán nhãn KHÔNG cần đếm offset. Chỉ cần copy `text` **nguyên văn** từ `N.txt`
> + gán `type`/`assertions`/`candidates`. `make_dev.py` tự dò offset ký tự.

## 1. Định dạng 1 nhãn (label spec — `data/dev/labels/N.json`)
```json
{
  "text": "metoprolol 25mg po bid",   // BẮT BUỘC — copy đúng từng ký tự trong N.txt
  "type": "THUỐC",                     // 1 trong 5 nhãn
  "assertions": ["isHistorical"],       // [] nếu không có; chỉ TC/DX/RX
  "candidates": [],                     // ICD-10 (DX) / RxNorm (RX); [] nếu chưa có
  "occ": 1,                             // (tùy chọn) chuỗi lặp -> chọn lần thứ mấy
  "note": "RxNorm TODO"                 // (tùy chọn) ghi chú review, KHÔNG vào gold
}
```
- `text` phải khớp **nguyên văn** (kể cả lỗi chính tả, double-space, `**`). Nếu chuỗi
  xuất hiện nhiều lần và muốn lần cụ thể → thêm `"occ"` (1-index). Ca chồng lấn hiếm →
  ép `"pos": [start, end]`.
- Không gộp 2 khái niệm vào 1 span. Không tạo span lồng nhau (mỗi ký tự thuộc tối đa 1 nhãn).
- **Khái niệm lặp lại:** gán **mỗi lần xuất hiện** là 1 concept riêng (position khác nhau) —
  quy tắc khách quan, khớp cách extractor sinh mention. *Ngoại lệ:* bỏ qua lần nhắc thuần
  **meta/thủ tục** không khẳng định về bệnh nhân (vd tiêu đề, "được chỉ định làm…"). Nếu
  sau này BTC dedupe, ta prune sau. Dùng `occ` khi chuỗi trùng để trỏ đúng lần.

## 2. Năm nhãn `type`

| Nhãn | Gồm | KHÔNG gồm |
|---|---|---|
| **TRIỆU_CHỨNG** | Triệu chứng/than phiền của BN: `khó thở`, `ho`, `đau đầu`, `đánh trống ngực`, `khò khè`, `tiếng rít`, `mệt mỏi`, `buồn nôn`, `đau hạ vị`, `phù` | Bệnh/chẩn đoán (→ CHẨN_ĐOÁN) |
| **TÊN_XÉT_NGHIỆM** | Tên xét nghiệm/cận lâm sàng có định danh: lab (`wbc`, `neut%`, `troponin`, `ast`, `creatinine`); hình ảnh/thăm dò (`x-quang ngực`, `điện tâm đồ`/`ecg`, `siêu âm tim`, `monitor holter`, `phân tích nước tiểu`, `tổng phân tích tế bào máu`) | Giá trị số (→ KẾT_QUẢ) |
| **KẾT_QUẢ_XÉT_NGHIỆM** | **Giá trị số** (kèm đơn vị/`%` nếu liền): `14,43`, `76,4`, `11.6`, `0.01`, `90%`, `98.3` | Mô tả định tính (`bình thường`, `không bất thường`) → **không gán** |
| **CHẨN_ĐOÁN** | Bệnh/chẩn đoán bác sĩ: `viêm phổi`, `xơ gan do rượu`, `hội chứng não gan`, `bệnh trào ngược dạ dày - thực quản`, `đợt cấp hen suyễn`, `hen suyễn`(bệnh mạn), `tăng huyết áp` | Triệu chứng (→ TRIỆU_CHỨNG) |
| **THUỐC** | Cụm thuốc như viết: tên + hàm lượng + đường/tần suất khi **liền mạch**: `metoprolol 25mg po bid`, `albuterol nebs q4h`, `prednisone 40 mg/ngày`, `aspirin 325mg`, `azithromycin`, `iv magnesium`, `z-pack` | Nhóm/hoạt chất chung chung không phải thuốc cụ thể |

### Ranh giới hay nhầm
- **Triệu chứng vs Chẩn đoán:** than phiền/dấu hiệu = TRIỆU_CHỨNG; tên bệnh (thường có
  cơ chế/vị trí giải phẫu, hoặc đứng sau "chẩn đoán/nghi ngờ/bệnh mạn tính") = CHẨN_ĐOÁN.
  VD `khó thở`=TC, `hen suyễn`=DX. `hội chứng não gan`=DX.
- **Tên XN vs Kết quả:** LUÔN tách. `WBC` (XN) và `14,43` (KQ) là **2 nhãn**, position khác nhau.
- **THUỐC span:** lấy trọn cụm dùng thuốc *tại lần nhắc đó* (gồm liều/đường dùng nếu liền).
  Nếu chỉ có tên trần (`azithromycin`) thì span = tên.

### KHÔNG gán nhãn (ngoài 5 type)
- Thủ thuật/can thiệp: `đặt shunt dẫn lưu…`, `combivent nebs x3` (nếu là thao tác, không phải kê thuốc → cân nhắc; mặc định coi thuốc khí dung là THUỐC).
- Yếu tố nguy cơ/lối sống (`cà phê`, `căng thẳng`, `mất việc`), thời gian, người/khoa phòng, câu mô tả diễn biến.
- Mô tả kết quả định tính không có số.

## 3. `assertions` (chỉ cho TRIỆU_CHỨNG / CHẨN_ĐOÁN / THUỐC)
Tập con của `{isNegated, isFamily, isHistorical}`. Một khái niệm có thể có 0–3 giá trị.

- **isNegated** — khái niệm bị phủ định: `không ho`, `phủ nhận đau ngực`, `âm tính`,
  `không có`, `không ghi nhận … bất thường`, `chưa` (chưa xuất hiện).
  *Lưu ý:* "ngừng/không dung nạp thuốc" ⇒ thuốc **vẫn đã dùng** → KHÔNG negated.
- **isFamily** — của người nhà: câu chủ ngữ là `vợ/chồng/bố/mẹ/con/cháu/anh/chị/gia đình/người nhà`.
- **isHistorical** — tiền sử/quá khứ. Bật khi khái niệm nằm trong/đề mục:
  - `Tiền sử …`, `Thuốc trước khi nhập viện`, `Bệnh (lý) mạn/mãn tính`,
    `Các đợt tương tự trước đây`, `(trước đây)`, `Nhập viện trong quá khứ`.
  - Thuốc liệt kê ở mục "Thuốc trước khi nhập viện" → **isHistorical**.
  - Thuốc/điều trị *trong đợt nằm viện hiện tại* (mục 2/3, "Các thủ thuật đã thực hiện",
    "được chỉ định điều trị") → **KHÔNG** historical.

## 4. `candidates`  (chấm bằng **Jaccard** — trả đúng tập mã, KHÔNG thừa)
- **CHẨN_ĐOÁN → ICD-10** (vd `"K21.0"`). Metric so exact mã → gán đúng độ sâu; 1–2 mã khi
  thật sự có biến thể gần nhau, tránh trả thừa (Jaccard phạt union to). P2/KB xác nhận.
- **THUỐC → RxNorm theo NGUYÊN TẮC "mã ở mức cụ thể nhất mention hỗ trợ"** (dung hòa IN-vs-SCD):
  | Mention có | Mức mã | Ví dụ |
  |---|---|---|
  | hoạt chất + hàm lượng + dạng | **SCD** | `amlodipine 10 mg po` → `308135` |
  | hoạt chất + hàm lượng (dạng mơ hồ, IV) | **SCDC** | `iv lasix 40 mg` → `315971` (furosemide 40 MG) |
  | **chỉ hoạt chất** (thuốc trần) | **IN** | `omeprazole` → `7646` |
  Không tra được mã sạch (combo, có liều nhưng KB thiếu SCD/SCDC, hoạt chất mơ hồ) → `[]` + `note`.
  Linker (P2) cũng trả ĐÚNG MỨC này. *(Ví dụ đề đều là thuốc có liều → SCD; thuốc trần
  không thể có SCD duy nhất → IN là mức đúng nhất. Cần BTC xác nhận cách mã hóa thuốc không liều.)*
- Các type khác (`TÊN_XÉT_NGHIỆM`/`KẾT_QUẢ`): KHÔNG có candidates (metric không tính).

## 5. Quy trình
1. Đọc `N.txt`, liệt kê MỌI khái niệm y tế thuộc 5 type.
2. Với mỗi khái niệm: copy `text` nguyên văn, chọn `type`, suy `assertions` theo mục 3,
   điền `candidates` nếu chắc (mục 4).
3. Lưu `data/dev/labels/N.json`.
4. `python src/datagen/make_dev.py --files N` → xuất `data/dev/gold/N.json` + review HTML.
   Nếu báo "KHÔNG tìm thấy text" → sửa `text` cho khớp nguyên văn (hoặc thêm `occ`).
5. Mở `data/dev/review/N.html` soát lại span/type/assertion trên văn bản.

## 6. Nhắc quan trọng
- `position` là **offset ký tự** (0…n-1), do máy tính — người gán KHÔNG tự đếm.
- Tách `TÊN_XÉT_NGHIỆM` vs `KẾT_QUẢ_XÉT_NGHIỆM`.
- `assertions` chỉ 3 giá trị hợp lệ; chỉ cho TC/DX/RX.
- `candidates` chỉ cho DX/RX.
- Gán nhãn tự động = **bản nháp**; luôn cần người review vì đây là "gold".
