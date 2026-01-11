# Database Administration Procedures Skill

**技能名稱**：資料庫管理程序
**用途**：定義資料庫日常管理與維護的標準作業程序 (SOPs)，確保資料庫操作的一致性、安全性與可追溯性。
**適用場景**：資料庫結構變更、日常備份、緊急還原、效能調校。

---

## 1. 核心原則

1.  **遷移優先 (Migration-First)**：任何資料庫結構 (Schema) 的變更，都**必須**透過 Alembic 遷移腳本來完成。嚴禁手動在正式環境的資料庫上執行 `ALTER TABLE` 等指令。
2.  **備份是生命線 (Backup is Lifeline)**：必須建立並遵循嚴格的備份與還原演練計畫。
3.  **權限最小化 (Least Privilege)**：應用程式連線資料庫的使用者，其權限應被限制在僅能執行必要的 DML (SELECT, INSERT, UPDATE, DELETE) 操作。DDL (CREATE, ALTER, DROP) 權限應由專門的遷移使用者持有。
4.  **所有操作皆需記錄 (Everything is Logged)**：所有重大的資料庫操作（如遷移、還原）都應被記錄下來。

---

## 2. 資料庫結構遷移 (Alembic)

本專案使用 **Alembic** 來管理資料庫結構的版本。原始碼位於 `backend/alembic/`。

### 2.1 建立一個新的遷移 (Creating a Migration)

**時機**：當您在 `backend/app/models/` 目錄下的任何 model 進行了變更（例如，新增欄位、修改類型、新增資料表）。

**程序**：
1.  在終端機中，確保您的環境已設定完成，並切換到 `backend` 目錄。
2.  執行以下指令以自動生成遷移腳本：
    ```bash
    # -m 後面應附上對本次變更的簡短、清晰的描述
    alembic revision --autogenerate -m "Add last_login_ip column to users table"
    ```
3.  **審查腳本**：Alembic 會在 `backend/alembic/versions/` 目錄下生成一個新的 Python 檔案。**務必打開此檔案，仔細審查**自動生成的程式碼是否符合您的預期。
4.  提交此遷移腳本到 Git 版本控制中。

### 2.2 應用遷移 (Applying a Migration)

**時機**：部署新版應用程式時，或在本地開發環境中更新到最新程式碼後。

**程序**：
1.  確保資料庫連線設定正確。
2.  執行以下指令將資料庫更新到最新版本：
    ```bash
    alembic upgrade head
    ```
3.  **驗證版本**：可透過 API `/api/v1/database/schema-version` (由 `schema_version.py` 提供) 來驗證目前資料庫的 schema 版本是否與程式碼同步。

---

## 3. 備份與還原 (Backup & Restore)

資料庫的備份與還原功能由 `backup.py` 中的 API 端點提供。

### 3.1 執行手動備份

*   **API 端點**：`POST /api/v1/database/backups`
*   **程序**：向此端點發送一個 POST 請求，後端將會執行 `pg_dump` 來建立一個完整的資料庫備份。備份檔案會儲存在伺服器端的指定目錄中。
*   **SOP**：在進行任何重大資料變更或結構遷移前，應先執行一次手動備份。

### 3.2 列出所有備份

*   **API 端點**：`GET /api/v1/database/backups`
*   **程序**：向此端點發送 GET 請求，將會回傳所有可用的備份檔案列表及其建立時間與大小。

### 3.3 從備份中還原 (Restore)

*   **API 端點**：`POST /api/v1/database/restore` (需有管理者權限)
*   **請求內文**：`{ "filename": "backup_filename.sql.gz" }`
*   **⚠️ 極度危險操作**：此操作將會**覆蓋**現有的資料庫。
*   **SOP**：
    1.  還原操作**必須**在維護模式下進行，並確保沒有任何使用者正在存取系統。
    2.  在執行還原前，應先對當前狀態執行一次**最後備份**。
    3.  操作人員必須取得明確授權。
    4.  還原完成後，必須立即驗證資料的完整性。

### 3.4 自動化備份策略

*   **策略**：應設定一個排程任務（例如 Linux 的 cron job 或 Kubernetes CronJob）來定期呼叫 `POST /api/v1/database/backups` API。
*   **建議排程**：
    *   **每日備份**：每天凌晨 2:00 執行一次完整備份。
    *   **備份保留策略**：至少保留最近 14 天的每日備份，以及最近 3 個月的每月備份。

---

## 4. 日常維護 (Maintenance)

資料庫的日常維護由 `maintenance.py` 中的 API 端點提供。

### 4.1 執行資料庫優化

*   **API 端點**：`POST /api/v1/database/optimize`
*   **執行內容**：此端點會對資料庫執行 `VACUUM` 和 `ANALYZE` 指令。
    *   `VACUUM`：回收已刪除資料所佔據的空間。
    *   `ANALYZE`：更新資料庫的統計資訊，以幫助查詢優化器做出更好的決策。
*   **SOP**：建議每週在離峰時段（例如週日凌晨）自動執行一次資料庫優化。

---

## 5. 健康狀況與監控

由 `health.py` 與 `schema_version.py` 提供。

### 5.1 檢查資料庫連線

*   **API 端點**：`/api/v1/database/health`
*   **用途**：一個簡單的端點，用於檢查應用程式是否能成功連線到資料庫。常被用於 Docker 的 `healthcheck` 或負載平衡器的健康檢查。

### 5.2 檢查結構版本

*   **API 端點**：`/api/v1/database/schema-version`
*   **用途**：回報當前資料庫中 Alembic 的版本號。在 CI/CD 部署流程中，可以用此端點來驗證 `alembic upgrade head` 是否已成功執行。

---
**建立日期**：2025-12-26
**最後更新**：2025-12-26