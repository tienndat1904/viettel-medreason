"""QLoRA fine-tune Qwen2.5-7B-Instruct trên synthetic SFT data (train_sft.jsonl).

Cầu nối "synthetic data (P3) -> QLoRA". Chạy trên GPU Kaggle/Colab (4-bit nf4).
- Đọc JSONL {messages:[...]} (do gen_synthetic.py sinh, khớp prompt.py của P1).
- Completion-only: CHỈ tính loss trên câu trả lời assistant cuối (mask phần prompt).
- Chỉ dùng transformers + peft + bitsandbytes (không cần trl) -> ít rủi ro phiên bản.
- Lưu LoRA adapter vào models/qwen7b-lora -> điền vào config extract.lora_adapter.

Dùng (trên GPU):
  pip install -r requirements-gpu.txt   # + đảm bảo có peft, bitsandbytes, accelerate
  python scripts/train_qlora.py --data data/synthetic/train_sft.jsonl --out models/qwen7b-lora

Reproducible: seed cố định; ghi lại config train ra <out>/train_config.json.
"""
from __future__ import annotations
import os, sys, json, argparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


def build_examples(path, tok, max_len, max_samples=0):
    """Mỗi dòng JSONL -> dict(input_ids, labels) với labels mask phần prompt (=-100).
    max_samples>0: chỉ lấy N mẫu đầu (cấu hình nhẹ cho T4)."""
    import torch  # noqa
    examples = []
    n_trunc = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if max_samples and len(examples) >= max_samples:
                break
            line = line.strip()
            if not line:
                continue
            msgs = json.loads(line)["messages"]
            # prompt = tất cả trừ assistant cuối, + generation prompt.
            # Render ra CHUỖI rồi tokenize riêng -> luôn nhận list[int]
            # (transformers 5.x: apply_chat_template(tokenize=True) trả BatchEncoding, không phải list).
            prompt_text = tok.apply_chat_template(
                msgs[:-1], tokenize=False, add_generation_prompt=True)
            full_text = tok.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=False)
            prompt_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
            full_ids = tok(full_text, add_special_tokens=False)["input_ids"]
            if len(full_ids) > max_len:
                full_ids = full_ids[:max_len]
                n_trunc += 1
            labels = list(full_ids)
            for i in range(min(len(prompt_ids), len(labels))):
                labels[i] = -100          # chỉ học phần assistant
            examples.append({"input_ids": full_ids, "labels": labels})
    if n_trunc:
        print(f"[data] {n_trunc} mẫu bị cắt vì > max_len={max_len} "
              f"(cân nhắc tăng max_len hoặc note ngắn hơn)")
    return examples


class Collator:
    def __init__(self, tok):
        self.pad = tok.pad_token_id

    def __call__(self, batch):
        import torch
        m = max(len(b["input_ids"]) for b in batch)
        ids, lbl, att = [], [], []
        for b in batch:
            iid, lab = list(b["input_ids"]), list(b["labels"])
            k = m - len(iid)
            ids.append(iid + [self.pad] * k)
            lbl.append(lab + [-100] * k)
            att.append([1] * len(iid) + [0] * k)
        return {"input_ids": torch.tensor(ids),
                "labels": torch.tensor(lbl),
                "attention_mask": torch.tensor(att)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic/train_sft.jsonl")
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--out", default="models/qwen7b-lora")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=2048)
    ap.add_argument("--max-samples", type=int, default=0,
                    help="chỉ lấy N mẫu đầu (0=tất cả) — cấu hình nhẹ cho T4")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-4bit", action="store_true")
    args = ap.parse_args()

    import torch
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              BitsAndBytesConfig, Trainer, TrainingArguments, set_seed)
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    set_seed(args.seed)

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    print(f"[data] nạp {args.data} ...")
    examples = build_examples(args.data, tok, args.max_len, args.max_samples)
    print(f"[data] {len(examples)} mẫu train")

    # T4 (Turing) KHÔNG hỗ trợ bf16 -> tự chọn bf16 (Ampere+/L4/A100) hoặc fp16 (T4)
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    cdt = torch.bfloat16 if use_bf16 else torch.float16
    print(f"[train] {'bf16' if use_bf16 else 'fp16'} (GPU hỗ trợ bf16: {use_bf16})")

    kw = {"torch_dtype": cdt, "device_map": "auto"}
    if not args.no_4bit:
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=cdt, bnb_4bit_use_double_quant=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, **kw)
    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    lora = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=args.lora_dropout,
        bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir=args.out + "_ckpt",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr, lr_scheduler_type="cosine", warmup_ratio=0.03,
        bf16=use_bf16, fp16=not use_bf16, gradient_checkpointing=True, logging_steps=20,
        save_strategy="epoch", report_to="none", seed=args.seed,
        optim="paged_adamw_8bit")
    trainer = Trainer(model=model, args=targs, train_dataset=examples,
                      data_collator=Collator(tok))
    trainer.train()

    os.makedirs(args.out, exist_ok=True)
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    with open(os.path.join(args.out, "train_config.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, ensure_ascii=False, indent=2)
    print(f"✅ Lưu LoRA adapter -> {args.out}")
    print(f"   Điền vào configs/config.yaml: extract.lora_adapter: {args.out}")


if __name__ == "__main__":
    main()
