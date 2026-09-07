# 貢獻指南 (Contributing Guide)

> `lifecycle: status=current reviewed=2026-09-08 owner=CK_Missive`

感謝您投入時間為「乾坤測繪公文管理系統」做出貢獻！本指南旨在幫助您了解專案的開發流程與規範，確保我們能夠高效、一致地協作。

## 核心設計理念

**同一件事只能有一份宣告。** 這條比目錄整潔更重要——2026-09-07 的收斂覆盤（`docs/architecture/CONSOLIDATION_20260907.md`）
列了十個「兩份宣告、沒有一方會報錯」的事故，每一個都比放錯目錄貴。

## 目錄結構規範

現行頂層（`ls` 即得，這裡只寫**職責**）：

| 目錄 | 職責 | 不該放的東西 |
|---|---|---|
| `backend/`／`frontend/` | 應用本體 | 一次性腳本 |
| `scripts/` | 排程、部署、備份、檢核（`scripts/checks/README.md` 按「誰在跑它」分組） | 沒有 runner 的腳本（weekly 39 會抓） |
| `configs/` | 基礎設施設定（compose、nginx、prometheus） | 應用層設定 |
| `backend/config/` | 應用層設定 | **第三個設定目錄不允許**（weekly 96） |
| `docs/` | 現行文件；`docs/archived/` 已作廢 | 描述已不存在架構的文件（weekly 122） |
| `uploads/`／`backups/`／`logs/`／`secrets/` | 執行時資料（皆 git-ignored） | 任何要進版控的東西 |
| `data/` | 匯入用原始資料 | 資料庫檔（**沒有 SQLite**，資料庫是 PostgreSQL 容器） |

> ⛔ 舊版本檔寫的 `claude_plant/` 規劃區與 `data/database/` SQLite **已不存在**（2026-09-08 作廢，原文在 `docs/archived/PROJECT_STRUCTURE_STANDARD_2025.md`）。
> 不確定放哪：先問「它有沒有 runner／消費端」——沒有的話多半不該新增。

## 開發流程

請參考 `README.md` 中的「快速開始」指南來啟動您的開發環境。

- **後端**: 依賴 `backend/.env` 檔案進行配置。請由 `.env.example` 複製建立。
- **前端**: 依賴 `frontend/.env.development` 檔案進行配置。

## 程式碼風格

為確保程式碼風格一致，我們使用以下工具進行自動格式化與檢查。

- **後端 (Python)**:
  - **格式化**: `Black`
  - **語法檢查**: `Ruff` (或 `Flake8`)

- **前端 (TypeScript/React)**:
  - **格式化**: `Prettier`
  - **語法檢查**: `ESLint`

強烈建議在您的編輯器中安裝對應的插件，以便在存檔時自動格式化。

## Git Commit 訊息規範

我們遵循 [Conventional Commits](https://www.conventionalcommits.org/) 規範。這有助於追蹤變更歷史並自動產生版本日誌。

Commit 訊息格式為：`<type>[optional scope]: <description>`

- **`<type>`** 必須是以下之一：
  - `feat`: 新增功能
  - `fix`: 修復錯誤
  - `docs`: 文件變更
  - `style`: 程式碼風格變更 (不影響程式碼邏輯)
  - `refactor`: 重構程式碼
  - `test`: 新增或修改測試
  - `chore`: 建構流程、輔助工具的變更 (例如修改 `.gitignore`)

**範例:**
```
feat: 新增使用者登入 API
fix: 修正案件查詢時的分頁錯誤
docs: 更新貢獻指南 CONTRIBUTING.md
chore: 將 ruff 加入 pre-commit 設定
```

---

遵循以上指南將極大地提升我們的協作效率與專案品質。
