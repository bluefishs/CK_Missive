> ⛔ **已作廢（2026-09-08）**：2025-09 規劃期目錄樹（`claude_plant/`、SQLite），現況見 `.claude/rules/architecture.md` 與 `docs/CONTRIBUTING.md`。

# CK Missive 專案架構 - 第一階段核心

## 🏗️ 專案目錄結構 (已優化)

```
CK_Missive/ (第一階段核心)
├── frontend/          # ⚛️ React前端應用
│   ├── src/
│   │   ├── components/    # React 元件
│   │   ├── pages/         # 頁面元件  
│   │   ├── api/          # API 服務
│   │   ├── types/        # TypeScript 型別
│   │   ├── stores/       # 狀態管理 (Zustand)
│   │   ├── hooks/        # 自訂 Hooks
│   │   ├── utils/        # 工具函數
│   │   └── styles/       # 樣式設定
│   ├── package.json      # 依賴管理
│   ├── tsconfig.json     # TypeScript 設定
│   ├── vite.config.ts    # Vite 建構設定
│   └── .env.development  # 環境變數
├── backend/           # 🐍 FastAPI後端應用
│   ├── app/
│   │   ├── api/          # API 路由
│   │   │   ├── endpoints/    # 各模組API端點
│   │   │   └── routes.py     # 路由註冊中心
│   │   ├── core/         # 核心設定 (cache, config)
│   │   ├── db/           # 資料庫連接與會話
│   │   ├── extended/     # ⚠️ 實際模型位置
│   │   │   └── models.py # SQLAlchemy模型 (OfficialDocument)
│   │   ├── services/     # 業務邏輯層
│   │   └── schemas/      # Pydantic 結構
│   ├── alembic/          # 資料庫遷移
│   ├── main.py           # 應用入口
│   ├── requirements.txt  # Python 依賴
│   └── .env              # 環境設定
├── configs/           # ⚙️ 必要配置 (Docker, Nginx)
├── data/              # 💾 核心資料檔案
│   ├── imports/          # CSV匯入資料
│   ├── exports/          # 匯出資料
│   └── database/         # 資料庫備份
│   # 注意: 使用Docker PostgreSQL，不再使用SQLite
├── claude_plant/      # 📋 開發規劃區 (統一管理開發工具)
└── README.md          # 📖 專案說明
```

## 📦 開發工具統一管理 (claude_plant/development_tools/)

```
claude_plant/development_tools/
├── tests/             # 🧪 測試檔案
├── scripts/           # 🔧 自動化腳本
├── deployment/        # 🚀 部署工具
├── maintenance/       # 🛠️ 維護工具
├── backup/            # 💾 備份檔案
├── docs/              # 📚 開發文檔
└── validation/        # ✅ 結構驗證工具
```

## 🚫 禁止事項

### Backend 目錄禁止項目：
- ❌ 測試文件 (應放在 `claude_plant/development_tools/tests/`)
- ❌ 腳本工具 (應放在 `claude_plant/development_tools/scripts/`)
- ❌ 維護工具 (應放在 `claude_plant/development_tools/maintenance/`)
- ❌ 臨時文件 (`temp_*.py`, `test_*.py` 等)

### 根目錄禁止項目：
- ❌ 空的 package.json 文件
- ❌ 亂碼或臨時文件 (`nul`, `temp` 等)
- ❌ 散落的腳本文件 (應統一到 claude_plant)

## ✅ 新增文件規則

### 測試文件：
- 📍 位置: `claude_plant/development_tools/tests/`
- 📝 命名: `test_*.py`, `*_test.py`

### 腳本工具：
- 📍 位置: `claude_plant/development_tools/scripts/`
- 📝 命名: 描述性名稱，如 `performance_analysis.py`

### 部署工具：
- 📍 位置: `claude_plant/development_tools/deployment/`
- 📝 內容: Docker 腳本, CI/CD 配置等

### 維護工具：
- 📍 位置: `claude_plant/development_tools/maintenance/`
- 📝 內容: 數據庫管理, 日誌清理等工具

## 🏛️ 資料庫架構 (PostgreSQL)

### 核心表格結構
| 表名 | 模型類名 | 主要欄位 | 說明 |
|------|----------|----------|------|
| `documents` | `OfficialDocument` | id, doc_number, subject, sender, receiver | 公文主表 |
| `users` | `User` | id, username, email | 用戶管理 |
| `cases` | `Case` | id, case_name, status | 承攬案件 |

### ⚠️ 關鍵對應關係
- **表名**: `documents` ↔ **模型**: `OfficialDocument`
- **欄位**: `sender`/`receiver` ✅ (不是 `sender_agency`/`receiver_agency`)
- **優先級**: `priority` (整數) ✅ (不是 `priority_level` 字串)

## 🔌 API架構

### 路由註冊模式
```python
# app/api/routes.py - 中央路由註冊
api_router.include_router(documents.router, prefix="/documents", tags=["公文管理"])

# 完整API路徑格式
/api/{prefix}/{endpoint}
例: /api/documents/documents-years
```

### 服務層架構
```python
# 三層架構
API端點 → 服務層 → 資料庫模型
endpoints/ → services/ → extended/models.py
```

## 🔄 架構維護

### 自動化檢查：
- 使用 `claude_plant/development_tools/validation/validate_structure.py`
- 定期執行結構檢查
- 集成到 CI/CD 流程中

### 開發流程：
1. 新增文件前檢查本規範
2. 按照規定目錄放置文件
3. 提交前執行結構驗證
4. 保持核心目錄乾淨整潔
5. **檢查模型與資料庫對應關係**

## 📋 檢查清單

開發人員在提交代碼前請確認：

- [ ] Backend 目錄只包含核心應用文件
- [ ] 測試文件已放置在正確位置
- [ ] 腳本工具已歸類到 claude_plant
- [ ] 沒有臨時或亂碼文件
- [ ] 目錄結構符合本規範

---

⚠️ **重要提醒**: 此架構規範旨在保持專案整潔和可維護性，請所有開發人員嚴格遵循。