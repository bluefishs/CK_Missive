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

# Tier 1 共享套件（vendored wheels）— 模組化 import 式單一源，取代 copy vendoring。
# 見 docs/architecture/MODULARIZATION_CROSS_PROJECT_STRATEGY.md。wheel 隨 repo 版控、
# 版本釘選；改共享套件＝rebuild wheel + bump 版本，一次修全 consumer 同步。
COPY vendor/ ./vendor/
RUN pip install --no-cache-dir ./vendor/*.whl

# Stage 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Create a non-root user
RUN adduser --system --group appuser

# Install runtime tools (as root):
# - curl: healthcheck
# - postgresql-client: pg_dump/psql for backup service (L49 fix 2026-05-27 — replaces docker CLI subprocess)
# - libzbar0: pyzbar 的原生 zbar 函式庫 —— 發票 QR 解碼（L49 家族，2026-07-30 修）
# - libgl1 / libglib2.0-0: opencv (cv2) 執行期依賴（缺 libGL.so.1 會 import 失敗）
# - tesseract-ocr + chi-tra/eng: 紙本收據 OCR fallback（無 QR 時）
#
# ⚠️ 為何需要（L49「容器缺 host 原生依賴」第 N 案）：
#   2026-05-27 廢 PM2 native backend 改純 Docker 後，這些原本由 Windows host 提供的
#   原生函式庫沒有進 image → 容器內 pyzbar「Unable to find zbar shared library」、
#   cv2「libGL.so.1 not found」、tesseract 執行檔不存在
#   → 智慧掃描三條路徑（QR / OCR / 視覺）全部不可用，但端點仍回 200 + success:false
#   → 使用者只看到「未辨識出發票資訊，請手動填寫」＝沉默失敗。
#   實證：唯一成功的 smart_qr 紀錄是 2026-04-09（PM2 時代），改 Docker 後再無成功。
# 報價單正式文件轉 PDF（owner 2026-08-18）：libreoffice-calc + fonts-noto-cjk
#
# 用 LibreOffice 而非在程式碼裡重畫版面 —— 版面的唯一來源是
# `app/templates/quotation_template.xlsx`，改抬頭或欄位只要換那個檔；
# 若改用 reportlab 重畫，就會變成 xlsx 一份版面、PDF 一份版面，
# 日後兩份不一致時沒有任何一方會報錯（本專案反覆踩過的那一類）。
# fonts-noto-cjk 是必要的：沒有中文字型，PDF 會整片變成方框。
#
# ⚠️ 這段註解**必須放在 RUN 之前**，不能插在 `\` 續行中間。
# 2026-08-19 我第一版就是插在續行裡，結果 `libreoffice-calc fonts-noto-cjk`
# 被吞掉 —— build log 照樣印出安裝過程、映像照樣 Built，
# 但映像內 `dpkg -l | grep -c libreoffice` = **0**。
# 同型事故見 v6.52：註解插進 `COOKIE=... \` 的續行中間，環境變數整個沒套用。
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl postgresql-client \
    libzbar0 libgl1 libglib2.0-0 \
    tesseract-ocr tesseract-ocr-chi-tra tesseract-ocr-eng \
    libreoffice-calc fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

# runtime 身分證 —— 讓 /api/health/detailed 說得出「跑的是哪一份程式碼」。
# 2026-08-21：先前四個來源四個值且 health 根本不回版本，事故當下沒有人
# 說得出線上是修好的版本還是沒修的。容器內沒有 .git，只能在 build 當下釘住。
ARG CK_BUILD_COMMIT=unknown
ARG CK_BUILD_TIME=unknown
ENV CK_BUILD_COMMIT=${CK_BUILD_COMMIT}
ENV CK_BUILD_TIME=${CK_BUILD_TIME}

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
