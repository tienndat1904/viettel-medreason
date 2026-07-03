"""LLM extractor (Qwen2.5-7B-Instruct + LoRA tùy chọn). Self-host, ≤9B.

Thiết kế:
- Chunk văn bản theo dòng (tránh cắt output với note dài) → gọi LLM từng chunk → gộp.
- LLM chỉ sinh {text, type}; assertion & position do module chuyên trách xử lý sau.
- Tách phần model ra sau `generate_fn` (inject được) → test toàn bộ logic không cần GPU.
- Lazy-load model để `import` không đòi torch/GPU.

Chạy thật trên Kaggle/Colab (transformers 4-bit đủ cho 100 doc). Xem notebooks/.
"""
from __future__ import annotations

from prompt import build_messages
from json_utils import extract_json_list
from chunking import chunk_document
from schema import LABELS


def _clean_spans(raw: list) -> list[dict]:
    """Giữ object hợp lệ {text,type}; bỏ trùng y hệt trong cùng output chunk."""
    out, seen = [], set()
    for o in raw:
        if not isinstance(o, dict):
            continue
        t, typ = o.get("text"), o.get("type")
        if not isinstance(t, str) or not t.strip() or typ not in LABELS:
            continue
        key = (t, typ)
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": t, "type": typ})
    return out


class LLMExtractor:
    def __init__(self, model_id="Qwen/Qwen2.5-7B-Instruct", lora_adapter="",
                 max_new_tokens=1536, temperature=0.0, load_in_4bit=True,
                 seed=42, max_chunk_chars=1800, generate_fn=None, fewshot=None):
        self.model_id = model_id
        self.lora_adapter = lora_adapter
        # có adapter (đã fine-tune) -> KHÔNG few-shot (khớp SFT leaner); base model -> few-shot.
        self.fewshot = (not bool(lora_adapter)) if fewshot is None else fewshot
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.load_in_4bit = load_in_4bit
        self.seed = seed
        self.max_chunk_chars = max_chunk_chars
        self._generate_fn = generate_fn        # inject để test (chunk_text -> raw str)
        self._model = None
        self._tok = None

    # ---- model thật (lazy) ----
    def _ensure(self):
        if self._model is not None or self._generate_fn is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
        set_seed(self.seed)
        kw = {"torch_dtype": torch.bfloat16, "device_map": "auto"}
        if self.load_in_4bit:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        self._tok = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **kw)
        if self.lora_adapter:
            from peft import PeftModel
            self._model = PeftModel.from_pretrained(self._model, self.lora_adapter)
        self._model.eval()

    def _generate(self, chunk_text: str) -> str:
        if self._generate_fn is not None:      # đường test / backend tùy biến
            return self._generate_fn(chunk_text)
        self._ensure()
        import torch
        prompt = self._tok.apply_chat_template(
            build_messages(chunk_text, fewshot=self.fewshot),
            tokenize=False, add_generation_prompt=True)
        inputs = self._tok(prompt, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            out = self._model.generate(
                **inputs, max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0, temperature=max(self.temperature, 1e-6),
                no_repeat_ngram_size=30,       # chống lặp trên văn bản nhiễu
                pad_token_id=self._tok.eos_token_id)
        return self._tok.decode(out[0][inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)

    # ---- API (hợp đồng cố định: text -> [{text,type}]) ----
    def extract(self, text: str) -> list[dict]:
        spans = []
        for _, chunk in chunk_document(text, self.max_chunk_chars):
            raw = extract_json_list(self._generate(chunk))
            spans.extend(_clean_spans(raw))
        return spans
