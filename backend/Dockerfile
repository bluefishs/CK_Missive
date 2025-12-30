# Stage 1: Builder
FROM python:3.11-slim as builder

# Install poetry
RUN pip install poetry

# Add poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy poetry dependency files
COPY poetry.lock pyproject.toml ./

# Install dependencies, without installing the project itself
# --no-root: Skips installing the project itself.
# --only=main: Only install main dependencies (excludes dev dependencies)
# --no-interaction: Prevents poetry from asking any interactive questions.
RUN poetry config virtualenvs.create false
RUN poetry install --no-root --only=main --no-interaction

# Stage 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN adduser --system --group appuser

# Install curl for healthcheck (as root)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONIOENCODING=utf-8

# Set ownership and permissions
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Start command with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]