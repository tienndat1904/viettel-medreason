"""Prompt cho LLM extractor (Qwen2.5-7B-Instruct).

LLM CHỈ sinh {text, type} — assertion & position do module chuyên trách xử lý sau
(giảm token/truncation; assertion module đã đạt ~0.94 trên dev).
"""

SYSTEM = """Bạn là hệ thống trích xuất khái niệm y tế từ bệnh án tiếng Việt (có lẫn thuật ngữ tiếng Anh, viết tắt, lỗi chính tả do dịch máy).
Liệt kê MỌI khái niệm y tế và phân loại đúng 1 trong 5 nhãn:
- TRIỆU_CHỨNG: triệu chứng bệnh nhân gặp (vd: ho, khó thở, đau ngực, buồn nôn)
- TÊN_XÉT_NGHIỆM: TÊN xét nghiệm/thăm dò (vd: wbc, troponin, ast, chụp x-quang ngực, siêu âm)
- KẾT_QUẢ_XÉT_NGHIỆM: GIÁ TRỊ + đơn vị của xét nghiệm (vd: 11.6, 0.01, 90%, 101.4)
- CHẨN_ĐOÁN: tên bệnh/chẩn đoán (vd: viêm phổi, tăng huyết áp, trào ngược dạ dày thực quản)
- THUỐC: tên thuốc điều trị (vd: aspirin 325mg, metoprolol 25mg po bid, albuterol nebs)

QUY TẮC BẮT BUỘC:
1. "text" phải COPY NGUYÊN VĂN chuỗi con trong input (đúng từng ký tự, kể cả lỗi chính tả), KHÔNG dịch, KHÔNG sửa, KHÔNG thêm dấu.
2. TÁCH RIÊNG tên xét nghiệm và giá trị: "wbc" (TÊN_XÉT_NGHIỆM) và "11.6" (KẾT_QUẢ_XÉT_NGHIỆM) là 2 khái niệm khác nhau.
3. Phân biệt TRIỆU_CHỨNG (bệnh nhân cảm nhận) với CHẨN_ĐOÁN (bác sĩ kết luận).
4. Bỏ qua thông tin hành chính (tên, tuổi, ngày) và câu không phải khái niệm y tế.
5. Chỉ trả về JSON hợp lệ, KHÔNG giải thích, KHÔNG markdown."""

_FEWSHOT_IN = """Triệu chứng chính
- đau bụng vùng thượng vị
- buồn nôn
Các triệu chứng liên quan: Không có sốt, ho
Kết quả xét nghiệm
- ast (aspartate aminotransferase) là 319
- bạch cầu (wbc) 11.6
Chẩn đoán: viêm phổi thùy dưới phải
Thuốc: metoprolol 25mg po bid"""

_FEWSHOT_OUT = """[
  {"text": "đau bụng vùng thượng vị", "type": "TRIỆU_CHỨNG"},
  {"text": "buồn nôn", "type": "TRIỆU_CHỨNG"},
  {"text": "sốt", "type": "TRIỆU_CHỨNG"},
  {"text": "ho", "type": "TRIỆU_CHỨNG"},
  {"text": "ast (aspartate aminotransferase)", "type": "TÊN_XÉT_NGHIỆM"},
  {"text": "319", "type": "KẾT_QUẢ_XÉT_NGHIỆM"},
  {"text": "bạch cầu (wbc)", "type": "TÊN_XÉT_NGHIỆM"},
  {"text": "11.6", "type": "KẾT_QUẢ_XÉT_NGHIỆM"},
  {"text": "viêm phổi thùy dưới phải", "type": "CHẨN_ĐOÁN"},
  {"text": "metoprolol 25mg po bid", "type": "THUỐC"}
]"""

_USER_TEMPLATE = """Trích xuất khái niệm y tế. Trả về JSON là list các object {{"text": "...", "type": "<một trong 5 nhãn>"}}.

VĂN BẢN:
\"\"\"
{text}
\"\"\"

JSON:"""


def build_messages(chunk_text: str, fewshot: bool = True):
    """fewshot=True: kèm 1 ví dụ (dùng cho model CHƯA fine-tune).
    fewshot=False: chỉ system + user — KHỚP format SFT leaner (gen_synthetic fewshot=False)
    -> dùng khi chạy model ĐÃ fine-tune (có lora_adapter)."""
    msgs = [{"role": "system", "content": SYSTEM}]
    if fewshot:
        msgs.append({"role": "user", "content": _USER_TEMPLATE.format(text=_FEWSHOT_IN)})
        msgs.append({"role": "assistant", "content": _FEWSHOT_OUT})
    msgs.append({"role": "user", "content": _USER_TEMPLATE.format(text=chunk_text)})
    return msgs
