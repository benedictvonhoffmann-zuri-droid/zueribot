FROM python:3.14-slim

WORKDIR /app

# Layer 1: Heavy ML deps (torch, sentence-transformers, chromadb).
# This layer is cached independently — only re-runs when requirements-heavy.txt changes.
COPY requirements-heavy.txt .
RUN pip install --no-cache-dir -r requirements-heavy.txt

# Layer 2: App deps (langchain, fastapi, pandas, etc.).
# Changes here do NOT invalidate the torch/sentence-transformers cache above.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Layer 3: Application code (most frequently changing).
COPY . .

EXPOSE 8000

CMD ["python3", "api_server.py"]
