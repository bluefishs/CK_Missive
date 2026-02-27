# ADR-0005: 混合部署模式 — Docker 基礎設施 + PM2 應用服務

> **狀態**: accepted
> **日期**: 2026-02-03
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.33.0

## 背景

CK_Missive 公文管理系統在開發與部署階段需要一種兼顧**便利性**與**可重現性**的運行模式。團隊在實際開發過程中遇到以下問題：

1. **全 Docker 模式的痛點** — 每次程式碼修改都需要重建容器，冷啟動時間長，除錯困難（需要 `docker exec` 進入容器），GPU passthrough 設定複雜且不穩定
2. **全原生模式的痛點** — PostgreSQL、Redis、Ollama 等基礎設施的版本與配置難以在不同開發環境間保持一致，缺乏可重現性
3. **Windows 開發環境** — 團隊主要使用 Windows 開發，需要處理編碼（cp950 vs UTF-8）和路徑差異等平台特有問題
4. **GPU 運算需求** — Ollama 需要 NVIDIA RTX 4060 GPU 加速推論，Docker GPU passthrough 在 Windows/WSL2 環境下需要特殊配置

## 決策

採用**混合部署模式**，將基礎設施與應用服務分層管理：

- **基礎設施層**（Docker Compose）：`docker-compose.infra.yml`
  - PostgreSQL 16（含 pgvector 擴充）
  - Redis（快取與 session 存儲）
  - Ollama（NVIDIA GPU passthrough，8GB VRAM）
- **應用服務層**（PM2 程序管理）：`ecosystem.config.js`
  - Backend：PM2 wrapper script 依序執行 `pip install` → `alembic migrate` → `uvicorn` 啟動
  - Frontend：React dev server（`npm run dev`）
- **配置管理**：專案根目錄單一 `.env` 檔案作為所有環境設定的唯一來源（SSOT）
- **啟動腳本**：`scripts/dev-start.ps1` 統一管理啟停流程，支援 `-Status`、`-Restart`、`-FullDocker` 等參數

## 後果

### 正面

- 程式碼修改即時生效，無需重建容器，開發迭代速度大幅提升
- GPU passthrough 透過 Docker Compose 的 `deploy.resources.reservations` 穩定運作，Ollama 推論效能不受影響
- 基礎設施服務（PostgreSQL、Redis）版本鎖定在 Docker image 中，跨環境一致
- PM2 提供程序管理、自動重啟、日誌聚合等功能，簡化運維
- 單一 `.env` 避免配置散落多處的混亂

### 負面

- 需要學習兩套編排工具（Docker Compose + PM2），新成員上手成本略高
- Windows 編碼問題需要**三層防護**：`.env`（`PYTHONUTF8=1`）+ `ecosystem.config.js`（env 區塊）+ `startup.py`（程式碼層），任一缺失都可能導致 cp950 crash
- subprocess 呼叫 Docker CLI 需要 `shutil.which()` 偵測路徑，並加上 `encoding="utf-8", errors="replace"` 參數
- 全 Docker 模式仍保留（`docker-compose.dev.yml`）但較少使用，兩份 Compose 檔案需要同步維護

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **全 Docker 模式** | 可重現性最佳，但冷啟動慢、除錯困難、GPU passthrough 不穩定，開發體驗差 |
| **全原生模式** | 開發最便利，但 PostgreSQL/Redis 版本管理困難，新成員環境建置耗時 |
| **Docker + docker-compose.override.yml** | 可部分掛載原始碼，但仍需 rebuild，且 override 邏輯增加複雜度 |
| **Dev Containers (VS Code)** | 整合度高，但強綁 VS Code，且 GPU passthrough 支援不成熟 |

最終選擇混合模式，讓基礎設施享有 Docker 的可重現性，應用服務享有原生開發的便利性。
