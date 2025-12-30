# 貢獻指南 (Contributing Guide)

感謝您投入時間為「乾坤測繪公文管理系統」做出貢獻！本指南旨在幫助您了解專案的開發流程與規範，確保我們能夠高效、一致地協作。

## 核心設計理念

本專案遵循一個核心理念：**保持根目錄的整潔，並將核心應用與開發工具徹底分離**。

- **核心區 (`CK_Missive/`)**: 僅保留生產環境必需的檔案，包括 `frontend`, `backend`, `configs`, `data`。
- **規劃區 (`claude_plant/`)**: 統一管理所有與開發、測試、維護相關的工具、腳本和文件。

## 目錄結構規範

所有新檔案都必須嚴格遵守以下結構。在新增檔案前，請先思考它應該屬於哪個分類。

```
CK_Missive/
├── frontend/          # React 前端應用
├── backend/           # FastAPI 後端應用
├── configs/           # 生產環境配置 (Docker, Nginx)
├── data/              # 核心資料檔案 (例如 SQLite 資料庫)
│   └── database/
└── claude_plant/      # 開發規劃與工具區
    ├── development_logs/
    ├── development_tools/
    │   ├── tests/     # 各類測試腳本
    │   ├── scripts/   # 自動化輔助腳本
    │   ├── deployment/ # 部署相關工具
    │   ├── maintenance/ # 維護工具
    │   ├── backup/    # 備份工具或檔案
    │   └── docs/      # **所有開發文檔放這裡**
    └── archive/       # 歷史歸檔
```

**黃金規則：如果您不確定檔案該放哪裡，優先考慮放在 `claude_plant` 的某個子目錄下。**

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
