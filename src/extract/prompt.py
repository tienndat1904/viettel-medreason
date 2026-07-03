"""Prompt cho LLM extractor (Qwen2.5-7B-Instruct).

LLM CHỈ sinh {text, type} — assertion & position do module chuyên trách xử lý sau
(giảm token/truncation; assertion module đã đạt ~0.94 trên dev).
"""

SYSTEM = """Bạn là hệ thống trích xuất khái niệm y tế từ bệnh án tiếng Việt (có lẫn thuật ngữ tiếng Anh, viết tắt, lỗi chính tả do dịch máy).
Liệt kê các khái niệm y tế, mỗi khái niệm đúng 1 trong 5 nhãn:
- TRIỆU_CHỨNG: điều bệnh nhân CẢM NHẬN/than phiền (vd: ho, khó thở, đau đầu, buồn nôn, mất ngủ, chóng mặt)
- TÊN_XÉT_NGHIỆM: TÊN xét nghiệm/thăm dò (vd: wbc, troponin, ast, chụp x-quang ngực, siêu âm, lưu lượng đỉnh thở ra)
- KẾT_QUẢ_XÉT_NGHIỆM: GIÁ TRỊ số + đơn vị của xét nghiệm (vd: 11.6, 0.01, 90%, 101.4, 240 đến 260)
- CHẨN_ĐOÁN: TÊN BỆNH bác sĩ kết luận (vd: viêm phổi, tăng huyết áp, đái tháo đường, trào ngược dạ dày thực quản)
- THUỐC: tên thuốc điều trị, GỒM hàm lượng+đường dùng (vd: aspirin 325mg, metoprolol 25mg po bid, albuterol nebs)

QUY TẮC BẮT BUỘC:
1. COPY NGUYÊN VĂN + NGẮN GỌN NHẤT: "text" là đúng cụm khái niệm, KHÔNG kèm chữ thừa quanh nó.
   ✗ SAI: "Nhập viện trong quá khứ vì đợt cấp hen suyễn"  → ✓ ĐÚNG: "đợt cấp hen suyễn"
   ✗ SAI: "được chẩn đoán mắc bệnh trào ngược..."        → ✓ ĐÚNG: "bệnh trào ngược..."
   ✗ SAI: "prednisone giảm liều"                          → ✓ ĐÚNG: "prednisone" (hoặc kèm hàm lượng nếu có)
2. TÁCH tên xét nghiệm và giá trị: "wbc"(TÊN) và "11.6"(KẾT_QUẢ) là 2 khái niệm; "lưu lượng đỉnh thở ra"(TÊN) và "240 đến 260"(KẾT_QUẢ) là 2 khái niệm. KHÔNG gộp.
3. TRIỆU_CHỨNG vs CHẨN_ĐOÁN — phân biệt kỹ (hay nhầm nhất):
   - đau đầu, khó thở, ho, khò khè, đau vùng xoang, mất ngủ, đau hạ vị = TRIỆU_CHỨNG (cảm nhận).
   - viêm phổi, hen suyễn, tăng huyết áp, nhồi máu cơ tim = CHẨN_ĐOÁN (tên bệnh).
   Nếu chỉ là cảm giác/dấu hiệu → TRIỆU_CHỨNG, KHÔNG phải CHẨN_ĐOÁN.
4. MỖI khái niệm chỉ liệt kê MỘT LẦN với MỘT type đúng nhất (không lặp 1 cụm ra 2 type).
5. CHỈ trích cụm chắc chắn là khái niệm y tế. Bỏ hành chính (tên/tuổi/ngày) & câu văn không phải khái niệm.
6. Chỉ trả JSON hợp lệ, KHÔNG giải thích, KHÔNG markdown."""

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
