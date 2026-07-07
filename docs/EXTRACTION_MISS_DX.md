# Phân tích trích hụt CHẨN_ĐOÁN trên dev (60 file) — bàn giao P2

**Nút thắt candidates KHÔNG phải linking (đã 98% đúng) mà là EXTRACTION.** 354 CHẨN_ĐOÁN gold:

| nhóm | số | hướng sửa |
|---|---|---|
| trích ĐÚNG | 169 | — |
| **sai BIÊN** (bắt ngắn hơn gold) | **84** | extractor ưu tiên **longest-match**, nuốt qualifier CÓ trong note |
| **sai TYPE** | **15** | cụm bệnh DÀI phải thắng term xét nghiệm/triệu chứng NGẮN |
| **THIẾU gazetteer** | **86** | thêm bệnh vào gazetteer CHẨN_ĐOÁN |

> Cả 84 ca sai biên đều CÓ text đầy đủ trong note → lấy lại được 100%.

## 1. SAI BIÊN — extractor cần longest-match (kéo cả 3 metric)

Rule bắt phần đầu, bỏ đuôi mô tả (nguyên phát / không đặc hiệu / bệnh viện / thùy dưới phải / di lệch / gần đây / mất bù…).

| file | gold (đúng) | rule bắt (thiếu) |
|---|---|---|
| 11 | bệnh thận mạn, không đặc hiệu | bệnh thận mạn |
| 11 | xơ gan mất bù có tăng áp lực tĩnh mạch cửa | xơ gan |
| 13 | Tăng huyết áp nguyên phát | Tăng huyết áp |
| 15 | xuất huyết nội sọ không do chấn thương, không đặc hiệu | xuất huyết nội sọ không do chấn thương |
| 15 | xuất huyết nội sọ không do chấn thương, không đặc hiệu | xuất huyết nội sọ không do chấn thương |
| 16 | bệnh phổi tắc nghẽn mạn tính, không xác định | bệnh phổi tắc nghẽn mạn tính |
| 16 | Viêm phổi bệnh viện | Viêm phổi |
| 16 | hạ huyết áp, không đặc hiệu | hạ huyết áp |
| 16 | hạ huyết áp, không đặc hiệu | hạ huyết áp |
| 16 | xẹp phổi thùy dưới phải | xẹp phổi |
| 16 | Viêm phổi bệnh viện | Viêm phổi |
| 20 | bệnh thận mạn, không đặc hiệu | bệnh thận mạn |
| 20 | Nhồi máu cơ tim gần đây | Nhồi máu cơ tim |
| 20 | gãy cổ xương đùi di lệch | gãy cổ xương đùi |
| 20 | gãy cổ xương đùi di lệch | gãy cổ xương đùi |
| 20 | gãy cổ xương đùi di lệch | gãy cổ xương đùi |
| 20 | tràn dịch màng phổi hai bên | tràn dịch màng phổi |
| 20 | thoát vị hoành nhỏ | thoát vị hoành |
| 20 | thay đổi khí phế thủng | khí phế thủng |
| 20 | xẹp phổi hai đáy | xẹp phổi |
| 20 | tràn dịch màng phổi hai bên | tràn dịch màng phổi |
| 20 | thoát vị hoành nhỏ | thoát vị hoành |
| 20 | thay đổi khí phế thủng | khí phế thủng |
| 20 | xẹp phổi hai đáy | xẹp phổi |
| 20 | hở van ba lá vừa-nặng | hở van ba lá |
| 20 | gãy cổ xương đùi phải | gãy cổ xương đùi |
| 20 | Nhồi máu cơ tim vùng vách liên thất, mạn tính và đỉnh | Nhồi máu cơ tim |
| 22 | khối máu tụ dưới màng cứng bán cấp hai bên | máu tụ dưới màng cứng bán cấp |
| 23 | tụ máu ngoài màng cứng phải cấp tính | tụ máu ngoài màng cứng |
| 3 | nhịp tim chậm tương đối | nhịp tim chậm |
| 3 | nhồi máu cơ tim vùng dưới cũ | nhồi máu cơ tim |
| 3 | nhịp tim chậm tương đối | nhịp tim chậm |
| 3 | nhồi máu cơ tim vùng dưới cũ | nhồi máu cơ tim |
| 32 | Đái tháo đường típ 2 | Đái tháo đường |
| 32 | Rung nhĩ kèm đáp ứng thất nhanh | Rung nhĩ |
| 32 | bệnh thận mạn, không đặc hiệu | bệnh thận mạn |
| 33 | suy tim, không đặc hiệu | suy tim |
| 35 | tăng lipid máu, không đặc hiệu | tăng lipid máu |
| 35 | Đái tháo đường típ 2 | Đái tháo đường |
| 35 | bệnh thận mạn, không đặc hiệu Giai đoạn 4 | bệnh thận mạn |
| 36 | Suy thận ngày càng nặng | Suy thận |
| 37 | Đái tháo đường, có biến chứng bệnh lý thần kinh ngoại biên | Đái tháo đường |
| 37 | Suy tim không do thiếu máu cơ tim | Suy tim |
| 37 | tràn dịch màng phổi hai bên nhẹ | tràn dịch màng phổi |
| 38 | Đái tháo đường típ 2 | Đái tháo đường |
| 38 | Suy tim dãn tâm thu giữ nguyên trương lực | Suy tim |
| 39 | viêm túi mật thủng cấp tính | viêm túi mật |
| 40 | viêm phổi thùy dưới phải | viêm phổi thùy |
| 44 | suy tim, không đặc hiệu | suy tim |
| 49 | Khối sa âm đạo | sa âm đạo |
| 5 | tăng lipid máu, không đặc hiệu | tăng lipid máu |
| 5 | hạ huyết áp, không đặc hiệu | hạ huyết áp |
| 50 | đợt cấp hen suyễn | hen suyễn |
| 54 | tái phát u ác trực tràng | u ác trực tràng |
| 54 | viêm phổi thuỳ, không đặc hiệu | viêm phổi |
| 54 | rung nhĩ điển hình kèm theo đáp ứng thất nhanh | rung nhĩ |
| 54 | viêm phổi thùy dưới trái | viêm phổi thùy |
| 58 | tăng lipid máu, không đặc hiệu | tăng lipid máu |
| 58 | nhịp tim chậm nặng | nhịp tim chậm |
| 58 | hạ huyết áp, không đặc hiệu | hạ huyết áp |
| 63 | viêm túi mật cấp tính không biến chứng | viêm túi mật cấp |
| 64 | viêm túi mật không biến chứng | viêm túi mật |
| 64 | bệnh túi thừa của cả ruột non và đại tràng, không thủng hay áp xe | áp xe |
| 66 | tăng lipid máu, không đặc hiệu | tăng lipid máu |
| 66 | Nhiễm trùng đường tiết niệu (UTIs) tái phát nhiễm khuẩn đường tiết niệu, vị trí không xác định | Nhiễm trùng đường tiết niệu |
| 66 | huyết khối tĩnh mạch sâu (DVT) | huyết khối tĩnh mạch sâu |
| 71 | Đái tháo đường típ 2 | Đái tháo đường |
| 71 | suy tim, không đặc hiệu | suy tim |
| 71 | Suy tim sung huyết cấp | Suy tim |
| 71 | Bệnh động mạch vành phải | Bệnh động mạch vành |
| 73 | tăng huyết áp vô căn (nguyên phát) | tăng huyết áp |
| 73 | tăng lipid máu, không đặc hiệu | tăng lipid máu |
| 73 | bệnh phổi tắc nghẽn mạn tính, không xác định | bệnh phổi tắc nghẽn mạn tính |
| 75 | bệnh động mạch vành sau can thiệp bắc cầu nối | bệnh động mạch vành |
| 8 | nốt tuyến giáp thùy trái | nốt tuyến giáp |
| 8 | nốt tuyến giáp thùy trái | nốt tuyến giáp |
| 8 | nốt tuyến giáp trái | nốt tuyến giáp |
| 8 | nốt tuyến giáp trái | nốt tuyến giáp |
| 8 | nốt tuyến giáp trái | nốt tuyến giáp |
| 8 | Nốt tuyến giáp thùy trái | Nốt tuyến giáp |
| 91 | Suy thận mạn giai V | Suy thận mạn |
| 92 | Nhiễm trùng đường tiết niệu kháng thuốc | Nhiễm trùng đường tiết niệu |
| 96 | nhiễm khuẩn đường tiết niệu tái phát | nhiễm khuẩn đường tiết niệu |
| 96 | nhiễm trùng huyết đường vào tiết niệu | nhiễm trùng huyết |

## 2. SAI TYPE — cụm bệnh dài phải thắng term ngắn

| file | gold=CHẨN_ĐOÁN | rule bắt nhầm |
|---|---|---|
| 23 | cơn co giật | co giật => TRIỆU_CHỨNG |
| 32 | Bệnh bạch cầu dòng tủy mãn tính | bạch cầu => TÊN_XÉT_NGHIỆM |
| 35 | Bệnh bạch cầu dòng tủy mãn tính | bạch cầu => TÊN_XÉT_NGHIỆM |
| 37 | tăng kali máu | kali => TÊN_XÉT_NGHIỆM |
| 37 | tăng kali máu | kali => TÊN_XÉT_NGHIỆM |
| 48 | ngất xỉu do phản ứng thần kinh mạch máu | ngất xỉu => TRIỆU_CHỨNG |
| 51 | hạ kali máu | kali => TÊN_XÉT_NGHIỆM |
| 58 | co giật | co giật => TRIỆU_CHỨNG |
| 66 | Tiểu đường loại 1 đái tháo đường | 1 => KẾT_QUẢ_XÉT_NGHIỆM |
| 7 | Ảo giác do rượu | Ảo giác => TRIỆU_CHỨNG |
| 70 | tăng bilirubin máu | bilirubin => TÊN_XÉT_NGHIỆM |
| 70 | tăng bilirubin máu | bilirubin => TÊN_XÉT_NGHIỆM |
| 70 | tăng bilirubin máu | bilirubin => TÊN_XÉT_NGHIỆM |
| 84 | Táo bón mãn tính | Táo bón => TRIỆU_CHỨNG |
| 92 | Bạch cầu tăng | Bạch cầu => TÊN_XÉT_NGHIỆM |

## 3. THIẾU GAZETTEER — thêm các bệnh này (đã khử trùng lặp)

| bệnh (thêm vào gazetteer CHẨN_ĐOÁN) | số lần |
|---|---|
| ung thư biểu mô tuyến | 4 |
| tắc nghẽn | 3 |
| bệnh trào ngược dạ dày- thực quản không có viêm thực quản | 2 |
| thay đổi sóng T không đặc hiệu | 2 |
| khối u trực tràng | 1 |
| u tuyến | 1 |
| U ác của đại tràng | 1 |
| nhồi máu cũ nhỏ ở vỏ não đỉnh trái | 1 |
| bệnh gút không đặc hiệu | 1 |
| Hội chứng kháng enzym tổng hợp protein | 1 |
| Nhiễm virus Herpes simplex | 1 |
| Bệnh thủy đậu/Zona | 1 |
| Ung thư biểu mô tuyến đại tràng | 1 |
| ung thư tuyến đại tràng | 1 |
| tụt huyết áp không rõ nguyên nhân | 1 |
| Chấn thương tù ở Chi dưới phải | 1 |
| vết thương hở phần khác của chi dưới | 1 |
| chấn thương đầu | 1 |
| hở van hai lá/van động mạch chủ nhẹ | 1 |
| Gãy xương hông phải | 1 |
| bệnh mạch máu | 1 |
| ăng huyết áp | 1 |
| bầm dập nhu mô vùng trán phải | 1 |
| tách thành động mạch chủ | 1 |
| Rò động - tĩnh mạch đùi phải | 1 |
| hội chứng turner, không đặc hiệu | 1 |
| viêm tụy | 1 |
| u ác của tuyến tiền liệt | 1 |
| rối loạn cảm xúc lưỡng cực khác | 1 |
| phình động mạch chủ nhỏ | 1 |
| huyết khối | 1 |
| ngừng thở khi ngủ | 1 |
| đào thải kháng thể hữu hình cấp tính | 1 |
| Bệnh lý thận do BK | 1 |
| viêm họng do liên cầu | 1 |
| nhịp tim nhanh | 1 |
| bất thường điện giải | 1 |
| sỏi đoạn cuối ống mật chủ | 1 |
| ngưng thở khi ngủ do tắc nghẽn | 1 |
| loét thực quản | 1 |
| Viêm thực quản độ C ở thực quản dưới | 1 |
| bệnh tim mạch | 1 |
| nhiễm trùng tụ cầu | 1 |
| hẹp van động mạch chủ nghiêm trọng | 1 |
| hẹp gây hạn chế dòng chảy | 1 |
| phình mạch ACom bên phải | 1 |
| hẹp khoảng 65% của động mạch cảnh chung trái | 1 |
| ung thư biểu mô tế bào mật | 1 |
| xuất huyết dưới màng cứng | 1 |
| viêm gan do men | 1 |
| nhiễm trùng đường hô hấp trên cấp | 1 |
| rối loạn cân bằng kiềm toan phối hợp | 1 |
| rung cuống nhĩ với đáp ứng thất nhanh | 1 |
| não úng thuỷ khác | 1 |
| não úng tuỷ | 1 |
| Bệnh túi thừa ở cả ruột non và đại tràng | 1 |
| gãy xương | 1 |
| viêm xương tủy | 1 |
| ung thư biểu mô tuyến giật nhú | 1 |
| khối ở chỗ uốn gan | 1 |
| Rối loạn cảm xúc (trầm cảm) | 1 |
| hội chứng nghiện rượu | 1 |
| bệnh lý chất trắng | 1 |
| loạn thần | 1 |
| graft SVG bị tắc | 1 |
| giãn đường dẫn mật trong gan | 1 |
| ung thư biểu mô tuyến, biệt hóa vừa phải đến kém | 1 |
| u ác của đầu tuỵ | 1 |
| ngưng thở khi ngủ | 1 |
| nhiễm trùng đường hô hấp trên | 1 |
| khối u thần kinh nội tiết ở thân tụy | 1 |
| rò ống tuỵ mật | 1 |
| nhiễm trùng vết mổổ | 1 |
| Viêm nội tâm mạc | 1 |
| rối loạn chức năng tâm thất phải | 1 |
| tăng bạch cầu | 1 |
| bàng quang thần kinh | 1 |
| liệt hai chi dưới | 1 |
| loét tì đè giai đoạn IV mãn tính | 1 |

## 4. NGHI LỖI GOLD (báo P3 kiểm)

- [23] `ăng huyết áp` — nghi OCR/annotation sai

---

## Cách sửa (P2) + kỷ luật đo

**Nhóm 1 (sai biên, 84) — cao điểm nhất, sửa 1 lần được nhiều:**
Extractor/gazetteer phải **longest-match**: khi text có cụm dài hơn là 1 mục gazetteer hợp lệ, lấy cụm dài. Thêm biến thể có đuôi (`... nguyên phát`, `..., không đặc hiệu`, `... bệnh viện`, `... thùy dưới phải`, `... di lệch`, `... hai bên`, `... mất bù...`) HOẶC cho matcher nuốt đuôi mô tả đứng ngay sau cụm gốc khi có trong note.

**Nhóm 2 (sai type, 15):** cụm bệnh DÀI phải ưu tiên hơn term xét nghiệm/triệu chứng NGẮN chồng vị trí. Vd `tăng kali máu`(CHẨN_ĐOÁN) thắng `kali`(TÊN_XÉT_NGHIỆM); `tăng bilirubin máu` thắng `bilirubin`; `Bệnh bạch cầu dòng tủy mãn tính` thắng `bạch cầu`. Thêm các cụm dài này vào gazetteer CHẨN_ĐOÁN với ưu tiên.

**Nhóm 3 (thiếu, 86):** thêm thẳng vào gazetteer CHẨN_ĐOÁN (danh sách mục 3). Ưu tiên bệnh phổ biến còn sót: `viêm tụy`, `huyết khối`, `chấn thương đầu`, `tách thành động mạch chủ`, `u ác đại tràng/tuyến tiền liệt`, `Viêm nội tâm mạc`, `viêm xương tủy`…

**⚠️ Kỷ luật đo (bắt buộc mỗi thay đổi):**
1. Sửa gazetteer → `python src/pipeline.py --input <dev> --output dev_pred --backend rule`
2. `python src/eval/official_scorer.py --pred dev_pred --gold data/dev/gold`
3. So với **0.3682**. CHỈ giữ nếu FINAL tăng (longest-match có thể phá ca gold vốn ngắn → phải verify, không đoán).

**Tác động kỳ vọng:** hiện chỉ 169/354 CHẨN_ĐOÁN khớp. Nhóm 1+2 (99 ca) là lỗi hệ thống, sửa 1 lần vét nhiều; nhóm 3 thêm tay. Vì concept khớp còn đóng góp đúng text (giảm WER) + assertion → **kéo cả 3 metric**, không riêng candidates.

*Sinh lại bảng: chạy lại phân tích P1 trên `data/dev/gold` vs output rule.*
