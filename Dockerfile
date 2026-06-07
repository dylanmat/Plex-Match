FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLEXMATCH_CACHE_PATH=/app/.plexmatch/cache.sqlite3

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY plexmatch ./plexmatch
COPY tests ./tests
COPY pytest.ini test_api.py ./

RUN mkdir -p /app/.plexmatch

EXPOSE 8000

ENTRYPOINT ["python", "-m", "plexmatch"]
CMD ["--help"]
