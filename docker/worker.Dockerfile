FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src ./src
COPY workflows ./workflows

RUN uv pip install --system -e .

CMD ["python", "-m", "memory_evolutionary_agents.worker"]
