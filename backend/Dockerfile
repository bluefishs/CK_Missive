# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build deps for compiled wheels (lxml, asyncpg, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt ./

# Filter packages exported from local conda env that conflict on Linux:
# - pywin32 / pywin32-ctypes / win32_setctime: Windows-only
# - torch / torchvision +cu126: CUDA-Windows wheels; CPU torch installed separately below
# - virtualenv 21.x: conda-only version, conflicts with poetry's pin (<20.33.0)
# - poetry / uv / build: dev-only env management tools (not needed in runtime image)
# - pip / setuptools / wheel: managed by base image
# - bandit / pip-audit: dev-only security tooling
RUN grep -ivE '^(pywin32|pywin32-ctypes|win32_setctime|torch==|torchvision==|virtualenv==|poetry==|uv==|build==|pip==|setuptools==|wheel==|bandit==|pip-audit==)' requirements.txt > requirements.linux.txt

# Create virtual environment and install dependencies
# --use-deprecated=legacy-resolver: tolerant of minor conda-export version mismatches
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.linux.txt && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 torchvision==0.21.0

# Stage 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN adduser --system --group appuser

# Install curl for healthcheck (as root)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Start command with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
