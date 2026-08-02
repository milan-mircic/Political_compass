FROM python:3.11-slim

WORKDIR /code

# Keep the HF model cache under /code so it's downloaded once at build time
# (as root) and still readable after chown below -- and so it lands on the
# same uid as a typical host user (1000) for bind-mounted local Docker use.
ENV HF_HOME=/code/.cache/huggingface

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app ./app

RUN useradd --uid 1000 --create-home appuser && chown -R appuser:appuser /code
USER appuser

EXPOSE 7860

# Schema init + source seeding run at container start, not build time --
# both are idempotent, and this way a fresh (empty) mounted volume still
# ends up with a valid, seeded database regardless of build history.
CMD ["sh", "-c", "python -m app.db && python -m app.seed_sources && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
