# 混合部署拓撲圖

Docker Compose 管理基礎設施，PM2 管理應用服務。所有配置以根目錄 `.env` 為唯一來源。

> 最後更新：2026-02-27 | 關聯：[ADR-0005](../adr/0005-mixed-mode-deployment.md)

## 部署拓撲

```mermaid
graph TB
    subgraph PM2["PM2 管理 (應用服務)"]
        FE_APP["frontend<br/>npm run dev<br/>:3000"]
        BE_APP["backend<br/>uvicorn main:app<br/>:8001"]
    end

    subgraph Docker["Docker Compose (基礎設施)"]
        PG["PostgreSQL 16<br/>+ pgvector 0.8.0<br/>:5432"]
        REDIS["Redis 7<br/>:6379"]
        OLLAMA["Ollama<br/>+ NVIDIA GPU<br/>:11434"]
    end

    subgraph Config["配置 (SSOT)"]
        ENV[".env<br/>唯一環境設定來源"]
        ECO["ecosystem.config.js<br/>PM2 配置"]
        DC["docker-compose.infra.yml<br/>基礎設施定義"]
    end

    ENV -->|讀取| ECO
    ENV -->|讀取| DC
    ENV -->|讀取| BE_APP

    ECO -->|管理| FE_APP
    ECO -->|管理| BE_APP

    BE_APP -->|TCP| PG
    BE_APP -->|TCP| REDIS
    BE_APP -->|HTTP| OLLAMA

    FE_APP -->|HTTP :8001| BE_APP

    classDef pm2 fill:#e6f7ff,stroke:#1890ff
    classDef docker fill:#f9f0ff,stroke:#722ed1
    classDef config fill:#fff7e6,stroke:#faad14

    class FE_APP,BE_APP pm2
    class PG,REDIS,OLLAMA docker
    class ENV,ECO,DC config
```

## 啟動順序

```mermaid
graph LR
    A["1. Docker Compose<br/>基礎設施啟動"] --> B["2. PM2 Wrapper<br/>pip install"]
    B --> C["3. Alembic<br/>資料庫遷移"]
    C --> D["4. Uvicorn<br/>後端啟動"]
    D --> E["5. Vite<br/>前端啟動"]

    style A fill:#f9f0ff,stroke:#722ed1
    style B fill:#e6f7ff,stroke:#1890ff
    style C fill:#fff7e6,stroke:#faad14
    style D fill:#f6ffed,stroke:#52c41a
    style E fill:#f6ffed,stroke:#52c41a
```

## 常用管理命令

| 動作 | 命令 |
|------|------|
| 混合模式啟動 | `.\scripts\dev-start.ps1` |
| 查看服務狀態 | `.\scripts\dev-start.ps1 -Status` |
| 停止所有服務 | `.\scripts\dev-stop.ps1` |
| 僅停 PM2 保留 DB | `.\scripts\dev-stop.ps1 -KeepInfra` |
| 全 Docker 模式 | `.\scripts\dev-start.ps1 -FullDocker` |

## GPU 配置（Ollama）

| 項目 | 規格 |
|------|------|
| GPU | NVIDIA RTX 4060 |
| VRAM | 8 GB |
| Embedding 模型 | nomic-embed-text（~0.5 GB） |
| Chat 模型 | qwen3:4b（~2.5 GB） |
| 剩餘 VRAM | ~5 GB（可再載入模型） |

## Windows 編碼防護

`PYTHONUTF8=1` 必須在三個位置設定：

1. **`.env`** — 後端直接讀取
2. **`ecosystem.config.js`** — PM2 環境變數
3. **`startup.py`** — subprocess 子程序
