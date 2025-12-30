# 乾坤測繪公文管理系統 (CK Missive) - v3.1

這是一個現代化的公文管理系統，旨在提供公文記錄、檢索、案件歸聯以及智慧型提醒等功能。此版本 (v3.1) 經過了全面的架構優化與功能重構，具備了更強的穩定性、可維護性和擴展性。

## 技術棧 (Tech Stack)

- **後端 (Backend)**: Python 3.11+, FastAPI, SQLAlchemy, Alembic, Pydantic, Typer
- **前端 (Frontend)**: TypeScript, React (推測), Vite, Ant Design
- **資料庫 (Database)**: PostgreSQL 15
- **容器化 (Containerization)**: Docker & Docker Compose

---

## 專案設定與安裝 (Setup & Installation)

請依照以下步驟從零開始設定並執行專案。

### 1. 環境準備

請確保您的本機已安裝以下軟體：
- [Docker](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### 2. 取得專案

```bash
# 克隆專案至您的本機
git clone <您的專案 Git Repo URL>
cd <專案目錄>
```

### 3. 設定環境變數

在專案的**根目錄**下，建立一個名為 `.env` 的檔案，並填入以下內容。請根據您的實際情況修改等號後面的值。

```dotenv
# .env 檔案範本

# --- Docker Compose Settings ---
COMPOSE_PROJECT_NAME=ck_missive

# --- Database Settings (PostgreSQL) ---
POSTGRES_USER=admin
POSTGRES_PASSWORD=your_strong_password
POSTGRES_DB=ck_missive_db
POSTGRES_HOST_PORT=5434
POSTGRES_CONTAINER_PORT=5432

# --- Backend Settings (FastAPI) ---
DATABASE_URL="postgresql+asyncpg://admin:your_strong_password@postgres:5432/ck_missive_db"
BACKEND_HOST_PORT=8001
BACKEND_CONTAINER_PORT=8000
SECRET_KEY="a_very_secret_and_long_random_string_for_jwt"

# --- Frontend Settings (React/Vite) ---
# **注意：請確保您的本機 3000 端口未被其他應用程式占用**
FRONTEND_HOST_PORT=3000
FRONTEND_CONTAINER_PORT=80
VITE_API_BASE_URL="http://localhost:8001"

# --- Adminer (Database GUI) Settings ---
ADMINER_HOST_PORT=8080
ADMINER_CONTAINER_PORT=8080

# --- Google Calendar API Settings (選填) ---
GOOGLE_CALENDAR_ID="primary"
GOOGLE_CALENDAR_CREDENTIALS_PATH="./GoogleCalendarAPIKEY.json"
```

### 4. 放置 Google API 金鑰 (選填)

如果您需要使用 Google Calendar 同步功能，請將您的服務帳號金鑰檔案命名為 `GoogleCalendarAPIKEY.json`，並放置在 `backend/` 目錄下。

> **安全提示**: 請務必將 `.env` 和 `GoogleCalendarAPIKEY.json` 檔案加入到您的 `.gitignore` 檔案中。

### 5. 啟動專案

在專案的根目錄下，執行以下指令：

```bash
docker-compose -f .\configs\docker-compose.yml up --build
```

### 6. 初始化資料庫

專案第一次啟動時，您需要手動建立資料表和管理員帳號。

1.  開啟**新的**終端機視窗，進入專案的 `backend/` 目錄。
2.  執行 `python manage.py create-tables` 來建立資料表。
3.  執行 `python manage.py create-admin` 來建立管理員帳號。

---

## 日常使用

- **訪問前端頁面**: [http://localhost:3000](http://localhost:3000)
- **訪問後端 API 文件**: [http://localhost:8001/api/docs](http://localhost:8001/api/docs)
- **訪問資料庫管理介面**: [http://localhost:8080](http://localhost:8080)

### 管理命令

管理命令皆透過 `backend/` 目錄下的 `manage.py` 執行。

- **檢查資料庫連線**: `python manage.py check-db`
- **建立管理員**: `python manage.py create-admin`

### 停止專案

在您執行 `docker-compose up` 的終端機視窗中，按下 `Ctrl + C` 即可。