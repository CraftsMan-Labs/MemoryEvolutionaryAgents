FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src ./src
COPY workflows ./workflows

RUN uv pip install --system -e .

CMD ["python", "-m", "memory_evolutionary_agents.worker"]
