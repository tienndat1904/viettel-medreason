# Môi trường tái lập cho BTC dựng lại & chấm trên private test (GPU).
# Build:  docker build -t viettel-medreason .
# Run  :  docker run --gpus all -v /path/private_test:/data/input \
#              -v $PWD/out:/app/output viettel-medreason \
#              python3 src/pipeline.py --input /data/input --output output --backend llm
#         (rồi: python3 scripts/package_submission.py --output output --input /data/input --n <N>)
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 HF_HOME=/app/.hf_cache
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch cu128 trước (khớp base CUDA 12.8), rồi phần còn lại từ lock
RUN pip3 install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
COPY requirements-lock.txt .
RUN pip3 install --no-cache-dir -r requirements-lock.txt

COPY . .

# Mặc định: chạy pipeline LLM trên data/test/input (đổi --input khi mount private test).
# Model Qwen + LoRA adapter: xem models/README.md (ship adapter + tải base).
CMD ["python3", "src/pipeline.py", "--input", "data/test/input", "--output", "output", "--backend", "llm"]
