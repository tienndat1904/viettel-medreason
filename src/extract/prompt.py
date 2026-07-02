"""Prompt cho LLM extractor (Qwen2.5-7B-Instruct). Ép trả JSON, KHÔNG có offset."""

SYSTEM = """Bạn là hệ thống trích xuất khái niệm y tế từ bệnh án tiếng Việt (có lẫn thuật ngữ tiếng Anh, viết tắt, lỗi chính tả do dịch máy).
Nhiệm vụ: liệt kê MỌI khái niệm y tế, phân loại đúng 1 trong 5 nhãn:
- TRIỆU_CHỨNG: triệu chứng bệnh nhân gặp (vd: ho, khó thở, đau ngực)
- TÊN_XÉT_NGHIỆM: tên xét nghiệm (vd: wbc, troponin, ast)
- KẾT_QUẢ_XÉT_NGHIỆM: GIÁ TRỊ + đơn vị của xét nghiệm (vd: 11.6, 0.01, 90%)
- CHẨN_ĐOÁN: tên bệnh bác sĩ chẩn đoán (vd: viêm phổi, tăng huyết áp)
- THUỐC: tên thuốc điều trị (vd: aspirin 325mg, metoprolol 25mg po bid)

QUY TẮC:
1. Trường "text" phải COPY NGUYÊN VĂN chuỗi con trong input (đúng từng ký tự), KHÔNG sửa lỗi, KHÔNG dịch.
2. TÁCH RIÊNG tên xét nghiệm và kết quả: "wbc" và "11.6" là 2 khái niệm khác nhau.
3. "assertions" (chỉ cho TRIỆU_CHỨNG/CHẨN_ĐOÁN/THUỐC), tập con của:
   - isNegated: bị phủ định ("không ho", "phủ nhận đau ngực", "âm tính")
   - isFamily: của người nhà ("vợ có triệu chứng...", "bố bệnh nhân...")
   - isHistorical: tiền sử / bệnh mạn tính / thuốc trước khi nhập viện / "(trước đây)"
4. KHÔNG xuất vị trí ký tự (hệ thống tự tính).
Chỉ trả về JSON hợp lệ, không thêm chữ nào khác."""

USER_TEMPLATE = """Trích xuất khái niệm y tế từ văn bản sau. Trả về JSON là list các object dạng:
{{"text": "...", "type": "<một trong 5 nhãn>", "assertions": ["..."]}}

VĂN BẢN:
\"\"\"
{text}
\"\"\"

JSON:"""


def build_messages(text: str):
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER_TEMPLATE.format(text=text)},
    ]
