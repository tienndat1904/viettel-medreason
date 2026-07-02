"""LLM extractor (Qwen2.5-7B-Instruct + LoRA tùy chọn). Lazy-load để import không cần GPU.

Chạy trên Kaggle/Colab. Với 100 doc, transformers 4-bit là đủ.
"""
from __future__ import annotations
import json, re
from prompt import build_messages


def _extract_json(s: str):
    """Bóc list JSON đầu tiên từ output của model, có sửa lỗi nhẹ."""
    s = s.strip()
    # bỏ hàng rào ```json ... ```
    s = re.sub(r"^```(?:json)?|```$", "", s.strip(), flags=re.MULTILINE).strip()
    start = s.find("[")
    end = s.rfind("]")
    if start < 0 or end < 0 or end < start:
        return []
    frag = s[start:end + 1]
    try:
        data = json.loads(frag)
    except json.JSONDecodeError:
        frag2 = re.sub(r",\s*([\]}])", r"\1", frag)  # bỏ dấu phẩy thừa
        try:
            data = json.loads(frag2)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


class LLMExtractor:
    def __init__(self, model_id="Qwen/Qwen2.5-7B-Instruct", lora_adapter="",
                 max_new_tokens=2048, temperature=0.0, load_in_4bit=True, seed=42):
        self.model_id = model_id
        self.lora_adapter = lora_adapter
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.load_in_4bit = load_in_4bit
        self.seed = seed
        self._model = None
        self._tok = None

    def _ensure(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
        set_seed(self.seed)
        kw = {"torch_dtype": torch.bfloat16, "device_map": "auto"}
        if self.load_in_4bit:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True)
        self._tok = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **kw)
        if self.lora_adapter:
            from peft import PeftModel
            self._model = PeftModel.from_pretrained(self._model, self.lora_adapter)
        self._model.eval()

    def extract(self, text: str) -> list[dict]:
        self._ensure()
        import torch
        msgs = build_messages(text)
        prompt = self._tok.apply_chat_template(msgs, tokenize=False,
                                               add_generation_prompt=True)
        inputs = self._tok(prompt, return_tensors="pt").to(self._model.device)
        with torch.no_grad():
            out = self._model.generate(
                **inputs, max_new_tokens=self.max_new_tokens,
                do_sample=self.temperature > 0, temperature=max(self.temperature, 1e-6),
                pad_token_id=self._tok.eos_token_id)
        gen = self._tok.decode(out[0][inputs["input_ids"].shape[1]:],
                               skip_special_tokens=True)
        raw = _extract_json(gen)
        # chỉ giữ field cần thiết
        cleaned = []
        for o in raw:
            if isinstance(o, dict) and o.get("text") and o.get("type"):
                cleaned.append({"text": o["text"], "type": o["type"],
                                "assertions": o.get("assertions", []) or []})
        return cleaned
