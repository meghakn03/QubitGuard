FROM python:3.11-slim AS builder
# ARM Linux may build Stim and PyMatching from source.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /build
COPY pyproject.toml requirements.lock ./
COPY backend ./backend
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps .

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
RUN useradd --create-home app && mkdir -p /app/data && chown app:app /app/data
USER app
EXPOSE 8000
CMD ["uvicorn", "qubitguard.api:app", "--host", "0.0.0.0", "--port", "8000"]
