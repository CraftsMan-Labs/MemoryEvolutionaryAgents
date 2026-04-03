FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
COPY src ./src
COPY workflows ./workflows

RUN uv pip install --system -e .

EXPOSE 8000

CMD ["uvicorn", "memory_evolutionary_agents.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
