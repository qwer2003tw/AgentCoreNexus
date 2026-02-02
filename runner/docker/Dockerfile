# Base image: Must be mirrored to ECR first!
# See infrastructure/runner/ecr-setup.sh

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd -r runner && useradd -r -g runner -u 1000 runner

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /workspace && chown runner:runner /workspace

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

USER runner
EXPOSE 8080

CMD ["python", "-m", "src.server"]
