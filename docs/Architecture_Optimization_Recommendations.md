# 專案架構與程式碼組織優化建議

本文旨在對當前專案的架構、程式碼組織和開發實踐進行全面評估，並依據模組化、元件化及抽象化等軟體工程原則，提出具體可行的優化建議。

## 總體架構評估

本專案是一個功能豐富的複合型應用，其核心是一個先進的「統一智慧語音互動框架」，並延伸出 AI 遊戲（海龜湯）、語音合成應用（TTS、RAP、語音克隆）等多樣化功能。專案採用了容器化（Docker）、前後端分離等現代化架構，奠定了良好的基礎。

然而，隨著專案規模的擴大和功能的迭代，目前的程式碼組織與開發實踐也暴露出一些問題，主要集中在 **根目錄混亂、配置管理複雜、模組邊界模糊** 等方面。以下建議旨在解決這些挑戰，提升專案的可維護性、擴展性和開發效率。

---

## 核心優化建議

### 1. 模組化與職責單一化 (Modularity & Single Responsibility)

#### 問題：根目錄與 `backend` 目錄結構混亂
根目錄下存在大量腳本 (`.py`, `.ps1`, `.sh`)、狀態報告 (`.md`) 和配置文件，`backend` 目錄下也有類似的腳本散落。這使得專案結構難以理解，新成員上手困難。

#### 建議：
1.  **建立 `scripts` 中樞目錄**：
    *   將根目錄下所有 `.sh`, `.ps1`, `.bat` 和一次性/維護性的 `.py` 腳本（如 `database-auto-init.py`, `startup-verification.py` 等）全部移至專案根目錄下的 `scripts/` 目錄。
    *   為腳本添加清晰的命名和註解，並在 `scripts/README.md` 中說明其用途和用法。

2.  **建立 `reports` 或 `docs/adhoc` 歸檔報告**：
    *   將所有用於追蹤問題、記錄狀態的 `.md` 文件（如 `GOOGLE_OAUTH_FIX.md`, `NAVIGATION_RESTORATION_PLAN.md`, `SYSTEM_FIX_REPORT.md` 等）移至 `docs/reports/` 或 `docs/investigations/`。
    *   強烈建議引入正式的議題追蹤系統（如 GitHub Issues, Jira），將這些臨時記錄轉化為結構化的 tickets，以便更好地追蹤和管理。

3.  **整合後端管理命令**：
    *   後端的 `manage.py` 是一個很好的實踐，應將 `backend` 目錄下的獨立腳本（如 `create_user.py`, `fix_navigation.py`, `rebuild_navigation.py`）整合為 `manage.py` 的子命令。這類似於 Django 的 `management commands`。
    *   例如，`python backend/manage.py create_user --name=...`。

4.  **核心業務模組化**：
    *   AI/ML 相關的核心功能應作為獨立的內部模組進行管理。建議在 `backend/app/` 下建立 `services` 或 `modules` 目錄：
        *   `backend/app/services/speech_engine/`: 存放所有與 TTS、語音克隆相關的邏輯。
        *   `backend/app/services/game_logic/`: 存放「海龜湯」遊戲（`ZHPrompter`）和 `fish_game`（如果存在）的邏輯。
    *   這使得核心業務邏輯與 Web 框架的其他部分（如路由、資料庫模型）解耦。

### 2. 元件化與組態管理 (Componentization & Configuration Management)

#### 問題：配置硬編碼與環境管理複雜
遊戲規則、UI 選項被硬編碼在 Python 程式碼中。同時，多個 `Dockerfile` 和 `docker-compose.yml` 文件增加了配置的複雜性。

#### 建議：
1.  **外部化應用程式配置**：
    *   對於 `ZHPrompter` 中的遊戲規則和提示詞，應將其從程式碼中抽離，改為從外部文件（如 `YAML` 或 `JSON`）或資料庫中讀取。
    *   對於 `launch_demo` 中的 `emotion_options`, `language_options` 等 UI 選項，應改為由後端 API 提供，使前端 UI 與模型能力動態同步，而不是在前端硬編碼。

2.  **統一容器化配置**：
    *   整合多個 `Dockerfile.*` 和 `docker-compose.*.yml` 文件。推薦使用 `docker-compose.override.yml` 模式：
        *   `docker-compose.yml`: 定義所有環境共享的基礎服務和配置。
        *   `docker-compose.dev.yml` (或 `docker-compose.override.yml`): 專門用於本地開發，包含熱加載、調試工具、開發專用環境變數等。
        *   `docker-compose.prod.yml`: 用於生產環境，包含生產級的配置和優化。
    *   利用 Dockerfile 中的多階段構建（multi-stage builds）來統一開發和生產環境的鏡像構建過程，減少文件數量。

3.  **標準化環境變數管理**：
    *   嚴格實施使用 `.env` 文件來管理環境變數。`backend` 和 `frontend` 都應有自己的 `.env.example` 文件作為模板。
    *   確保所有敏感資訊（API 金鑰、資料庫密碼）都通過環境變數注入，而不是硬編碼在程式碼或配置文件中。`security-config-check.py` 的存在表明這是一個需要關注的重點。

### 3. 包裝層與抽象化 (Wrapper & Abstraction Layers)

#### 問題：缺乏資料庫遷移和資料操作的抽象
專案中存在 `.sql` 腳本（`create_missing_tables.sql`）和 Python 腳本（`execute_missing_tables.py`）直接操作資料庫結構，而專案本身已引入 Alembic。

#### 建議：
1.  **強制使用 Alembic 進行資料庫遷移**：
    *   所有資料庫結構的變更（Schema Changes）都必須通過 `alembic revision` 來產生遷移腳本。
    *   禁止手動執行 `.sql` 文件來修改生產或開發資料庫的結構，以確保資料庫版本的一致性和可追溯性。
    *   一次性的資料初始化或修正（Data Migrations）也應盡可能通過 Alembic 的 `op.execute()` 在遷移腳本中完成。

2.  **為外部服務建立抽象層**：
    *   如果專案與多個外部 API（如 Google Calendar）互動，應為每個服務建立一個客戶端或服務層 (`backend/app/clients/google_calendar_client.py`)。
    *   這個抽象層負責處理認證、API 請求和錯誤處理，使業務邏輯程式碼無需關心底層的 HTTP 請求細節。

## 結論

本專案技術基礎堅實，功能亮點突出。當前的挑戰主要源於快速迭代過程中產生的「技術債」。通過實施以上關於 **目錄結構重構、配置外部化、管理命令整合、以及強制使用遷移工具** 的建議，可以顯著提升專案的模組化程度和工程品質，為未來的開發和維護工作奠定更穩固的基礎。
