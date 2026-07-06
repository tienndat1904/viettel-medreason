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
