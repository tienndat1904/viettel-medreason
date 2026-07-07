# Moi truong tai lap cho BTC dung lai & cham tren private test.
# BAN NOP CHINH THUC = --backend rule: KHONG GPU, KHONG internet (KB da ship trong
# data/kb/*.parquet). Base python-slim nhe, tai lap tuyet doi, chay vai giay/100 file.
#
# Build:  docker build -t viettel-medreason .
# Run  :  docker run -v /path/private_test/input:/data/input -v $PWD/out:/app/output \
#              viettel-medreason \
#              python3 src/pipeline.py --input /data/input --output output --backend rule
#         docker run -v $PWD/out:/app/output viettel-medreason \
#              python3 scripts/package_submission.py --output output --input /data/input --n <N>
#
# (LLM/RAG la thi nghiem, KHONG dung khi nop - chay tren GPU Kaggle/Colab qua notebooks/,
#  deps o requirements-gpu.txt / requirements-semantic.txt. Dung dung Dockerfile nay cho chung.)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1

WORKDIR /app

# Chi can 6 goi core cho duong rule (da PIN, khong torch/GPU).
COPY requirements-submit.txt .
RUN pip3 install --no-cache-dir -r requirements-submit.txt

COPY . .

# Mac dinh: chay pipeline rule tren data/test/input (doi --input khi mount private test).
CMD ["python3", "src/pipeline.py", "--input", "data/test/input", "--output", "output", "--backend", "rule"]
