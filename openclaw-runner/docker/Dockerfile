FROM python:3.11-slim

# Note: This base image must be mirrored to ECR before use
# See SECURITY_CHECKLIST.md for instructions

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r runner && useradd -r -g runner -u 1000 runner

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create workspace directory
RUN mkdir -p /workspace && chown runner:runner /workspace

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Switch to non-root user
USER runner

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "src.main"]
