"""Kho khái niệm y tế cho synthetic generator (bắt chước style bệnh án test).

Mỗi pool là dữ liệu thô để lắp ghép note + gold labels. Giữ tách khỏi gen_synthetic
để dễ mở rộng vocab. Mã ICD/RxNorm là best-effort (dùng cho full-gold; train chỉ cần text+type).
"""
from __future__ import annotations

# --- TRIỆU_CHỨNG (than phiền của bệnh nhân) ---
SYMPTOMS = [
    "ho", "ho khan", "ho đờm", "ho đờm xanh", "khó thở", "khó thở khi gắng sức",
    "khó thở về đêm", "đau ngực", "đau bụng", "đau thượng vị", "đau hạ vị",
    "đau hạ sườn phải", "đau đầu", "đau đầu dữ dội", "chóng mặt", "hoa mắt",
    "buồn nôn", "nôn", "tiêu chảy", "táo bón", "sốt", "sốt cao", "ớn lạnh",
    "mệt mỏi", "khò khè", "tiếng rít", "đánh trống ngực", "ngất xỉu", "gần ngất",
    "phù chi dưới", "phù hai bên", "vã mồ hôi", "đổ mồ hôi qua đêm", "ợ hơi",
    "ợ chua", "chán ăn", "sụt cân", "tê bì", "yếu cơ", "lơ mơ", "lú lẫn",
    "mất định hướng", "mất thăng bằng", "khó nuốt", "đau khớp", "đau lưng",
    "tiểu buốt", "tiểu dắt", "tiểu máu", "ban đỏ", "ngứa", "chảy nước mũi",
    "nghẹt mũi", "đau họng", "đau cơ", "đau vai", "mất ngủ", "hồi hộp",
]

# --- CHẨN_ĐOÁN (bệnh) -> mã ICD-10 best-effort ---
DIAGNOSES = [
    ("tăng huyết áp", "I10"),
    ("đái tháo đường típ 2", "E11.9"),
    ("đái tháo đường típ 1", "E10.9"),
    ("tăng lipid máu", "E78.5"),
    ("bệnh tim thiếu máu cục bộ", "I25.9"),
    ("rung nhĩ", "I48.91"),
    ("suy tim", "I50.9"),
    ("suy tim sung huyết", "I50.9"),
    ("nhồi máu cơ tim cấp", "I21.9"),
    ("bệnh thận mạn", "N18.9"),
    ("suy thận cấp", "N17.9"),
    ("viêm phổi", "J18.9"),
    ("viêm phổi thùy", "J18.1"),
    ("hen suyễn", "J45.909"),
    ("đợt cấp hen suyễn", "J45.901"),
    ("bệnh phổi tắc nghẽn mạn tính", "J44.9"),
    ("giãn phế quản", "J47.9"),
    ("bệnh trào ngược dạ dày thực quản", "K21.9"),
    ("viêm loét dạ dày", "K25.9"),
    ("loét tá tràng", "K26.9"),
    ("xơ gan", "K74.60"),
    ("xơ gan do rượu", "K70.3"),
    ("viêm tụy cấp", "K85.9"),
    ("viêm túi mật cấp", "K81.0"),
    ("sỏi mật", "K80.20"),
    ("nhiễm khuẩn huyết", "A41.9"),
    ("nhiễm khuẩn đường tiết niệu", "N39.0"),
    ("viêm bể thận", "N12"),
    ("thiếu máu", "D64.9"),
    ("đột quỵ nhồi máu não", "I63.9"),
    ("xuất huyết dưới nhện", "I60.9"),
    ("động kinh", "G40.909"),
    ("tăng calci máu", "E83.52"),
    ("tăng kali máu", "E87.5"),
    ("hạ kali máu", "E87.6"),
    ("suy giáp", "E03.9"),
    ("cường giáp", "E05.90"),
    ("béo phì", "E66.9"),
    ("viêm khớp dạng thấp", "M06.9"),
    ("gout", "M10.9"),
    ("trầm cảm", "F32.9"),
    ("rối loạn lo âu", "F41.9"),
    ("sa sút trí tuệ", "F03.90"),
    ("ung thư đại tràng", "C18.9"),
    ("ung thư phổi", "C34.90"),
    ("viêm mô tế bào", "L03.90"),
    ("huyết khối tĩnh mạch sâu", "I82.409"),
    ("thuyên tắc phổi", "I26.99"),
    ("hội chứng não gan", "K72.90"),
    ("viêm phế quản cấp", "J20.9"),
]

# --- TÊN_XÉT_NGHIỆM (lab) -> (đơn vị, khoảng giá trị min,max, số chữ số thập phân) ---
LABS = [
    ("wbc", "", 3.0, 25.0, 1), ("bạch cầu (wbc)", "", 3.0, 25.0, 1),
    ("hgb", "", 7.0, 17.0, 1), ("hemoglobin", "", 7.0, 17.0, 1),
    ("hct", "%", 20.0, 50.0, 1), ("tiểu cầu (plt)", "", 50.0, 450.0, 0),
    ("neut%", "%", 40.0, 90.0, 1), ("lymph%", "%", 5.0, 45.0, 1),
    ("natri", "", 128.0, 145.0, 0), ("kali", "", 2.8, 6.5, 1),
    ("creatinine", "", 0.6, 6.0, 1), ("ure (bun)", "", 10.0, 90.0, 0),
    ("glucose", "", 70.0, 350.0, 0), ("ast", "", 10.0, 400.0, 0),
    ("alt", "", 10.0, 400.0, 0), ("bilirubin toàn phần", "", 0.3, 5.0, 1),
    ("troponin", "", 0.0, 2.0, 2), ("bnp", "", 20.0, 25000.0, 0),
    ("lactate", "", 0.5, 6.0, 1), ("inr", "", 0.9, 4.0, 1),
    ("hba1c", "%", 5.0, 12.0, 1), ("crp", "", 1.0, 200.0, 0),
    ("spo2", "%", 82.0, 100.0, 0),
]

# --- xét nghiệm cho KẾT_QUẢ dạng CHỮ (định tính) -> (tên, list kết quả chữ) ---
# BTC (forum): giá trị chữ "dương tính"/"âm tính"/"bình thường" VẪN lấy làm KẾT_QUẢ_XÉT_NGHIỆM.
LABS_TEXT = [
    ("cấy máu", ["âm tính", "dương tính", "không mọc vi khuẩn"]),
    ("cấy nước tiểu", ["âm tính", "dương tính"]),
    ("test nhanh cúm", ["âm tính", "dương tính"]),
    ("xét nghiệm HIV", ["âm tính"]),
    ("HBsAg", ["âm tính", "dương tính"]),
    ("protein niệu", ["âm tính", "dương tính", "vết"]),
    ("hồng cầu niệu", ["âm tính", "dương tính"]),
    ("khí máu động mạch", ["trong giới hạn bình thường"]),
    ("soi phân tìm ký sinh trùng", ["âm tính"]),
    ("test kháng nguyên phế cầu", ["âm tính", "dương tính"]),
]

# --- TÊN_XÉT_NGHIỆM (hình ảnh / thăm dò, không kèm giá trị số) ---
IMAGING = [
    "chụp x-quang ngực", "chụp ct sọ não", "chụp ct bụng chậu", "siêu âm ổ bụng",
    "siêu âm tim", "siêu âm gan mật", "điện tâm đồ", "ecg", "mri sọ não",
    "nội soi dạ dày", "monitor holter", "tổng phân tích nước tiểu",
    "cấy máu", "cấy nước tiểu", "chụp x-quang bàn chân", "siêu âm mạch máu chi dưới",
]

# --- KẾT_QUẢ mô tả (định tính, dạng cụm dài) theo modality hình ảnh/thăm dò ---
# BTC (forum HHM #2): mô tả chẩn đoán hình ảnh ("xẹp phổi thùy dưới phải…",
# "ổ tụ dịch chia hai thùy…") VẪN là KẾT_QUẢ_XÉT_NGHIỆM. Dạy LLM lấy KQXN mô tả dài
# (rule không vét được). Không phải modality nào cũng có -> ca thiếu = "chỉ có tên".
IMAGING_FINDINGS = {
    "chụp x-quang ngực": [
        "đông đặc thùy dưới phải", "xẹp phổi thùy dưới trái do chèn ép",
        "tràn dịch màng phổi hai bên", "bóng tim to", "thâm nhiễm mô kẽ lan tỏa",
        "không thấy tổn thương nhu mô phổi",
    ],
    "chụp ct sọ não": [
        "nhồi máu não thùy đỉnh trái", "không thấy xuất huyết nội sọ",
        "teo não lan tỏa theo tuổi", "ổ giảm tỷ trọng vùng nhân bèo phải",
    ],
    "chụp ct bụng chậu": [
        "dày thành đại tràng sigma", "khối u đầu tụy kích thước khoảng 3 cm",
        "dịch tự do khoang phúc mạc lượng vừa", "sỏi niệu quản phải gây ứ nước thận",
    ],
    "siêu âm ổ bụng": [
        "gan nhiễm mỡ độ 2", "sỏi túi mật kích thước 8 mm",
        "dịch tự do ổ bụng lượng ít", "thận ứ nước độ 1 bên phải",
    ],
    "siêu âm tim": [
        "phân suất tống máu giảm còn 40%", "hở van hai lá mức độ vừa",
        "giãn buồng thất trái", "tăng áp động mạch phổi nhẹ",
    ],
    "siêu âm gan mật": [
        "giãn đường mật trong gan", "sỏi ống mật chủ", "gan thô echo không đều",
    ],
    "điện tâm đồ": [
        "rung nhĩ đáp ứng thất nhanh", "nhịp xoang đều",
        "ST chênh lên ở V1 đến V4", "block nhánh trái hoàn toàn",
    ],
    "ecg": [
        "nhịp nhanh xoang", "ngoại tâm thu thất thưa",
        "sóng T âm ở các chuyển đạo trước tim",
    ],
    "mri sọ não": [
        "tổn thương chất trắng quanh não thất", "ổ nhồi máu cấp thùy thái dương phải",
        "không thấy khối choán chỗ",
    ],
    "nội soi dạ dày": [
        "loét hang vị đường kính khoảng 1 cm", "viêm trợt niêm mạc dạ dày",
        "giãn tĩnh mạch thực quản độ 2",
    ],
    "monitor holter": [
        "nhiều cơn nhịp nhanh trên thất", "cơn rung nhĩ kịch phát",
    ],
    "chụp x-quang bàn chân": [
        "gãy xương bàn ngón 3", "thoái hóa khớp cổ chân",
        "không thấy tổn thương xương",
    ],
    "siêu âm mạch máu chi dưới": [
        "huyết khối tĩnh mạch sâu đùi phải", "không thấy huyết khối",
        "hẹp động mạch khoeo",
    ],
}

# --- THUỐC -> (ingredient RxNorm rxcui, list hàm lượng phổ biến) ---
DRUGS = [
    ("metoprolol", "6918", ["25mg", "50mg", "100mg"]),
    ("atenolol", "1202", ["25mg", "50mg"]),
    ("carvedilol", "20352", ["6.25mg", "12.5mg", "25mg"]),
    ("amlodipine", "17767", ["5mg", "10mg"]),
    ("lisinopril", "29046", ["10mg", "20mg"]),
    ("losartan", "52175", ["50mg", "100mg"]),
    ("furosemide", "4603", ["20mg", "40mg", "80mg"]),
    ("torsemide", "38413", ["10mg", "20mg"]),
    ("spironolactone", "9997", ["25mg", "50mg"]),
    ("aspirin", "1191", ["81mg", "325mg"]),
    ("clopidogrel", "32968", ["75mg"]),
    ("warfarin", "11289", ["2mg", "5mg"]),
    ("apixaban", "1364430", ["2.5mg", "5mg"]),
    ("atorvastatin", "83367", ["20mg", "40mg", "80mg"]),
    ("rosuvastatin", "301542", ["10mg", "20mg"]),
    ("metformin", "6809", ["500mg", "1000mg"]),
    ("insulin glargine", "274783", ["100 đơn vị"]),
    ("omeprazole", "7646", ["20mg", "40mg"]),
    ("pantoprazole", "40790", ["40mg"]),
    ("prednisone", "8640", ["10mg", "20mg", "40mg"]),
    ("albuterol", "435", ["nebs"]),
    ("ipratropium", "7213", ["nebs"]),
    ("azithromycin", "18631", ["250mg", "500mg"]),
    ("amoxicillin", "723", ["500mg", "875mg"]),
    ("ceftriaxone", "2193", ["1g", "2g"]),
    ("ciprofloxacin", "2551", ["500mg"]),
    ("vancomycin", "11124", ["1g"]),
    ("acetaminophen", "161", ["500mg", "1g"]),
    ("ibuprofen", "5640", ["400mg", "600mg"]),
    ("morphine", "7052", ["2mg", "4mg"]),
    ("gabapentin", "25480", ["300mg"]),
    ("levothyroxine", "10582", ["50mcg", "100mcg"]),
    ("nitroglycerin", "4917", ["0.4mg"]),
    ("methadone", "6813", ["5mg", "10mg"]),
    ("tacrolimus", "42316", ["1mg"]),
]

# biệt dược / cách viết khác (dùng để tạo mention "khó") -> (ingredient rxcui)
BRAND_ALIASES = [
    ("coumadin", "11289"), ("lasix", "4603"), ("crestor", "301542"),
    ("tylenol", "161"), ("advil", "5640"), ("plavix", "32968"),
    ("eliquis", "1364430"), ("gleevec", "282388"), ("prograf", "42316"),
    ("ntg", "4917"), ("asa", "1191"),
]

# route / tần suất nối sau thuốc (nhiễu thật)
DRUG_SUFFIX = ["po", "po bid", "po daily", "po qid", "iv", "iv x2", "q4h", "q6h",
               "đường uống", "tiêm tĩnh mạch", "x 1", "nebs q4h", "hằng ngày"]

# cue phủ định (đứng trước triệu chứng/chẩn đoán -> isNegated)
NEG_PREFIX = ["Không ", "Phủ nhận ", "không có ", "Không ghi nhận ", "âm tính với "]

# người nhà (isFamily)
FAMILY_PREFIX = ["Vợ bệnh nhân có ", "Bố bệnh nhân có ", "Mẹ bệnh nhân có ",
                 "Con trai bệnh nhân có ", "Anh trai bệnh nhân có ",
                 "Gia đình có tiền sử "]

# dòng hành chính / không phải khái niệm (để dạy model KHÔNG trích)
FILLER = [
    "Bệnh nhân được chuyển từ khoa cấp cứu lên khoa nội.",
    "Người bệnh uống nhiều cà phê mỗi ngày.",
    "Mất việc làm cách đây 2 tuần, nhiều căng thẳng.",
    "Được thăm khám bởi bác sĩ phụ trách chính.",
    "Lên lịch tái khám với bác sĩ chuyên khoa vào tuần tới.",
    "Bệnh nhân tỉnh, tiếp xúc tốt.",
    "Người nhà xin về theo nguyện vọng.",
    "Sinh hoạt cá nhân bình thường.",
]

# ============ MỞ RỘNG ĐA DẠNG (Phase 1: khớp phân phối note THẬT) ============
# Quan sát note test: nhiều biến thể tiêu đề mục, trường con "Đặc điểm triệu chứng"
# đa số N/A (KHÔNG phải concept), triệu chứng bọc ngữ cảnh tường thuật lộn xộn,
# độ đầy/độ dài rất khác nhau (có note mục 3 RỖNG), nhiễu MT nặng.

# Biến thể tiêu đề mục — chọn ngẫu nhiên để model KHÔNG bám 1 khuôn cố định.
HDR_HISTORY = ["1. Tiền sử bệnh", "1.  Tiền sử bệnh", "1. Tiền sử bệnh nội khoa",
               "1) Tiền sử", "I. Tiền sử bệnh", "TIỀN SỬ BỆNH"]
HDR_CHRONIC = ["Các bệnh lý mạn tính", "Các bệnh lý nội khoa mạn tính",
               "Bệnh lý mãn tính", "Tiền sử nội khoa", "Các bệnh mạn tính kèm theo",
               "Các tập kinh lâm sàng trước đây"]
HDR_PREMED  = ["Thuốc trước khi nhập viện", "Thuốc đang dùng tại nhà",
               "Thuốc trước khi nhập viện lần này", "Điều trị ngoại trú trước đó",
               "Thuốc đang sử dụng"]
HDR_PRESENT = ["2. Bệnh sử hiện tại", "2.  Bệnh sử hiện tại", "2. Tiền sử bệnh hiện tại",
               "2) Quá trình bệnh lý", "II. Bệnh sử", "BỆNH SỬ HIỆN TẠI"]
HDR_SYMPTOM = ["Triệu chứng hiện tại", "Các triệu chứng hiện tại",
               "Triệu chứng cơ năng", "Các triệu chứng lúc nhập viện"]
HDR_RELATED = ["Các triệu chứng liên quan", "Triệu chứng đi kèm", "Khám các cơ quan",
               "Các triệu chứng khác"]
HDR_EVAL    = ["3. Đánh giá tại bệnh viện", "3.  Đánh giá tại bệnh viện",
               "3. Cận lâm sàng", "3) Đánh giá", "III. Đánh giá tại bệnh viện",
               "KẾT QUẢ CẬN LÂM SÀNG"]
HDR_LAB     = ["Kết quả xét nghiệm", "Xét nghiệm", "Kết quả cận lâm sàng",
               "Xét nghiệm máu", "Sinh hóa - huyết học"]
HDR_IMAGING = ["Chẩn đoán hình ảnh", "Chẩn đoán hình ảnh và thăm dò",
               "Hình ảnh học", "Thăm dò chức năng"]
HDR_TREAT   = ["Điều trị", "Điều trị tại viện", "Hướng xử trí", "Thuốc điều trị"]

# Trường con "Đặc điểm triệu chứng" — dịch từ template Anh, ĐA SỐ N/A (KHÔNG phải concept).
# Dạy model bỏ qua khối nhiễu này (rất phổ biến trong note test).
SYMPTOM_CHAR_FIELDS = ["Vị trí", "Mức độ nghiêm trọng", "Thời gian", "Tần suất",
                       "Chiếu xạ", "Các yếu tố làm nặng thêm", "Các yếu tố làm giảm",
                       "Hoàn cảnh khởi phát", "Diễn tiến", "Tính chất"]
SYMPTOM_CHAR_VALS = ["N/A", "N/A", "N/A", "Không rõ", "không xác định", "-"]

# Ngữ cảnh tường thuật bọc QUANH triệu chứng (đưa vào text NHƯNG NGOÀI span concept).
SYMPTOM_NARRATIVE = [
    "xuất hiện đột ngột", "khởi phát từ từ", "kéo dài vài ngày nay",
    "tăng dần trong tuần qua", "sau khi đi bộ vài chặng", "khi thay đổi tư thế",
    "được người nhà phát hiện", "tự hết sau vài phút", "trong lúc làm việc",
    "lặp lại nhiều lần trong ngày",
]

# Yếu tố nguy cơ / tiền sử xã hội — KHÔNG trích (dạy model bỏ qua).
RISK_FACTORS = [
    "Hiện đang hút thuốc", "Đã bỏ thuốc lá 5 năm", "Uống rượu thường xuyên",
    "Không hút thuốc không uống rượu", "Tiền sử hút thuốc 20 gói-năm",
    "Ít vận động", "Chế độ ăn nhiều muối", "Công việc văn phòng ít vận động",
]

# Dòng hành chính hay gặp trong note thật (filler mở rộng, KHÔNG trích).
ADMIN_LINES = [
    "Thời điểm khởi phát triệu chứng: Hôm qua",
    "Thời điểm khởi phát: cách đây 3 ngày",
    "Người cung cấp thông tin: bệnh nhân",
    "Người cung cấp thông tin: con gái bệnh nhân",
    "Tình trạng lúc vào viện: tỉnh, tiếp xúc được",
    "Dị ứng: không rõ",
    "Dị ứng thuốc: chưa ghi nhận",
    "Lý do vào viện được ghi nhận qua lời kể người nhà.",
]
