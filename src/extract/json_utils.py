"""Parse JSON bền vững từ output LLM.

Xử lý: thinking mode (<think>...</think>), code-fence ```json,
và bóc block [ ... ] bằng đếm ngoặc cân bằng.
"""
from __future__ import annotations
import json
import re

_THINK_RE = re.compile(r"<think>[\s\S]*?</think>\s*", re.IGNORECASE)
_THINK_CONTENT_RE = re.compile(r"<think>([\s\S]*?)</think>", re.IGNORECASE)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?([\s\S]*?)\n?```")


def strip_thinking(text: str) -> str:
    """Bỏ khối <think>...</think>. Nếu bỏ xong rỗng thì lấy nội dung bên trong."""
    if not text:
        return text
    stripped = _THINK_RE.sub("", text).strip()
    if stripped:
        return stripped
    m = _THINK_CONTENT_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _balanced(cleaned: str, open_c: str, close_c: str):
    start = cleaned.find(open_c)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == open_c:
            depth += 1
        elif cleaned[i] == close_c:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_json_list(text: str) -> list:
    """Trả về list JSON từ output LLM; [] nếu không parse được.

    Thứ tự thử: strip thinking → parse trực tiếp → code-fence → block [..] cân bằng.
    """
    if not text:
        return []
    cleaned = strip_thinking(text)
    if not cleaned:
        return []

    # 1) parse trực tiếp
    try:
        data = json.loads(cleaned)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):  # đôi khi model bọc {"concepts": [...]}
            for v in data.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        pass

    # 2) code fence
    m = _JSON_BLOCK_RE.search(cleaned)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    # 3) block [ ... ] cân bằng, rồi bỏ dấu phẩy thừa
    data = _balanced(cleaned, "[", "]")
    if isinstance(data, list):
        return data
    m2 = cleaned.find("[")
    if m2 >= 0:
        frag = re.sub(r",\s*([\]}])", r"\1", cleaned[m2:cleaned.rfind("]") + 1])
        try:
            data = json.loads(frag)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []
