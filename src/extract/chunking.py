"""Chia văn bản dài thành chunk theo ranh giới DÒNG (không cắt giữa khái niệm).

Bệnh án dài tới ~5700 ký tự + nhiều khái niệm → gọi LLM 1 lần dễ bị cắt output.
Chia theo dòng, mỗi chunk ≤ max_chars, KHÔNG chồng lấp (mỗi occurrence chỉ nằm
trong 1 chunk → tránh trùng khi gộp; offset map lại bằng resolve_spans trên input gốc).
"""
from __future__ import annotations


def chunk_document(text: str, max_chars: int = 1800) -> list[tuple[int, str]]:
    """Trả list (char_offset, chunk_text). Gộp các dòng tới khi vượt max_chars."""
    lines = text.splitlines(keepends=True)
    chunks: list[tuple[int, str]] = []
    buf, start, pos = "", 0, 0
    for ln in lines:
        if buf and len(buf) + len(ln) > max_chars:
            chunks.append((start, buf))
            buf, start = "", pos
        buf += ln
        pos += len(ln)
    if buf.strip():
        chunks.append((start, buf))
    if not chunks:                      # văn bản 1 dòng / rỗng
        chunks = [(0, text)]
    return chunks
