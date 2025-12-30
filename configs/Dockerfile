# CK Missive Multi-stage Production Dockerfile
# 🚀 Phase 3 Production Deployment Configuration

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production
COPY frontend/ .
RUN npm run build

# Stage 2: Setup backend
FROM python:3.11-slim AS backend-base
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/

# Stage 3: Production runtime
FROM python:3.11-slim AS production
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from backend-base
COPY --from=backend-base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-base /usr/local/bin /usr/local/bin

# Copy application files
COPY --from=backend-base /app/backend ./backend
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy configuration files
COPY configs/nginx.conf /etc/nginx/sites-available/default
# COPY configs/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories
RUN mkdir -p /var/log/supervisor /app/logs

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV NODE_ENV=production

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]