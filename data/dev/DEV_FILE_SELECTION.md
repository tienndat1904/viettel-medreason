# Dev set — chọn 30 file (v1)

Chọn từ 100 file test public (`data/test/input/`) để dev set **đa dạng** theo độ dài và
đặc trưng nội dung, giúp `scorer.py` phản ánh đúng điểm mạnh/yếu của pipeline.

> Đây là **dev để đo offline**, KHÔNG phải nhãn của BTC. Nhãn do nhóm tự gán
> (xem `ANNOTATION_GUIDE.md`) → cần review tay.

## 30 file đã chọn
```
1, 2, 3, 5, 8, 15, 17, 20, 22, 23, 27, 28, 32, 35, 36,
37, 41, 42, 44, 49, 50, 54, 58, 64, 66, 70, 84, 95, 96, 100
```

## Tiêu chí & phân bố (dựa trên profil 100 file)
- **Độ dài** (min 136 / max 4428 / trung bình 1323 ký tự): trải đều
  - Rất dài (>2800): 3, 41, 20, 54, 58, 23, 1
  - Dài (1700–2800): 70, 28, 36, 32, 50, 44, 64, 35, 96
  - Trung bình (900–1700): 27, 66, 37, 100, 5, 17, 84, 49
  - Ngắn (<900): 2, 8, 42, 95, 22, 15
- **Nhiều THUỐC:** 50, 36, 37, 44, 27, 1, 70, 33*(dự phòng)*
- **Nhiều XÉT_NGHIỆM (tách TÊN vs KẾT_QUẢ):** 54, 70, 36, 58, 17, 66, 3, 20
- **Ngữ cảnh người nhà (isFamily):** 3, 23, 32, 35, 58, 70, 84
- **Nhiều phủ định (isNegated):** 1, 23, 49, 58, 64, 95
- **Tiền sử / mạn tính (isHistorical):** 1, 20, 28, 32, 50, 64, 96 (+ hầu hết có mục "Tiền sử")
- **Nhiều CHẨN_ĐOÁN:** 2, 23, 28, 32, 41

## Cách tái lập lựa chọn
Profil bằng đếm cue (drug/lab/family/neg/historical/dx) + độ dài ký tự trên toàn bộ
100 file, rồi lấy mẫu phủ các nhóm trên. Có thể mở rộng dev set lên ~150 file (mục tiêu
tuần 3) bằng cách bổ sung file ở các nhóm còn thiếu.
