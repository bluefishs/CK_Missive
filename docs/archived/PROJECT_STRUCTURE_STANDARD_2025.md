> ⛔ **已作廢（2026-09-08）**：本檔描述的是 2025-09 規劃期的目錄樹（`claude_plant/` 規劃區、`data/database/` SQLite），
> 兩者現在都不存在。現行結構的權威是 `.claude/rules/architecture.md`（職責）與 `ls`（目錄）；
> 設定目錄只允許 `configs/` 與 `backend/config/`（weekly 96）。留檔是為了讓「舊附件回流」時能對照出它是哪一版。

# 📁 CK_Missive 專案結構標準

## 🎯 第一階段核心架構

```
CK_Missive/ (第一階段核心)
├── frontend/          # ⚛️ React前端應用
│   ├── src/
│   │   ├── components/   # React 組件
│   │   ├── pages/       # 頁面組件
│   │   ├── services/    # API 服務層
│   │   ├── hooks/       # 自定義 Hooks
│   │   ├── stores/      # Zustand 狀態管理
│   │   ├── router/      # 路由配置
│   │   ├── types/       # TypeScript 類型定義
│   │   └── utils/       # 工具函數
│   ├── public/          # 靜態資源
│   ├── package.json     # 前端依賴
│   ├── vite.config.ts   # Vite 配置
│   └── Dockerfile       # 前端容器化
│
├── backend/           # 🐍 FastAPI後端應用
│   ├── app/
│   │   ├── api/         # API 路由層
│   │   │   ├── endpoints/  # API 端點實現
│   │   │   └── routes.py   # 路由註冊
│   │   ├── core/        # 核心配置
│   │   │   ├── config.py      # 應用配置
│   │   │   ├── auth_service.py # 認證服務
│   │   │   └── logging_manager.py # 日誌管理
│   │   ├── db/          # 資料庫層
│   │   │   └── database.py    # 資料庫連接
│   │   ├── models/      # 資料模型
│   │   ├── schemas/     # Pydantic 資料驗證
│   │   ├── services/    # 業務邏輯層
│   │   └── integrations/ # 外部整合 (Google Calendar)
│   ├── alembic/         # 資料庫遷移
│   ├── requirements.txt # 後端依賴
│   ├── main.py         # 應用程式入口
│   └── Dockerfile      # 後端容器化
│
├── configs/           # ⚙️ 必要配置 (Docker, Nginx)
│   ├── docker-compose.yml  # 服務編排
│   ├── nginx.conf          # 反向代理配置
│   └── .env.*             # 環境變數配置
│
├── data/              # 💾 核心資料檔案
│   ├── imports/       # CSV 匯入檔案
│   ├── exports/       # 資料匯出檔案
│   └── templates/     # 範本檔案
│
├── claude_plant/      # 📋 開發規劃區 (統一管理開發工具)
│   └── development_tools/  # 統一開發工具管理
│       ├── tests/          # 🧪 測試檔案
│       │   ├── unit/       # 單元測試
│       │   ├── integration/# 整合測試
│       │   ├── e2e/        # 端到端測試
│       │   └── fixtures/   # 測試資料
│       ├── scripts/        # 🔧 自動化腳本
│       │   ├── build/      # 構建腳本
│       │   ├── deploy/     # 部署腳本
│       │   └── utils/      # 工具腳本
│       ├── deployment/     # 🚀 部署工具
│       │   ├── docker/     # Docker 相關
│       │   ├── k8s/        # Kubernetes 配置
│       │   └── nginx/      # Nginx 配置
│       ├── maintenance/    # 🔧 維護工具
│       │   ├── db/         # 資料庫維護
│       │   ├── logs/       # 日誌分析
│       │   └── monitor/    # 監控工具
│       ├── backup/         # 💾 備份檔案
│       │   ├── database/   # 資料庫備份
│       │   ├── config/     # 配置備份
│       │   └── files/      # 檔案備份
│       ├── docs/           # 📚 開發文檔
│       │   ├── api/        # API 文檔
│       │   ├── database/   # 資料庫文檔
│       │   └── guides/     # 開發指南
│       ├── validation/     # ✅ 驗證工具
│       │   ├── lint/       # 代碼檢查
│       │   ├── format/     # 格式化工具
│       │   └── security/   # 安全檢查
│       └── logs/           # 📝 開發日誌
│           ├── progress/   # 進度記錄
│           ├── issues/     # 問題追蹤
│           └── changes/    # 變更記錄
│
├── .env               # 主要環境變數
├── .env.ports         # 端口配置
├── .gitignore         # Git 忽略檔案
├── pytest.ini        # 測試配置
└── README.md          # 📖 專案說明
```

## 🔧 技術架構對應

### 前端架構 (frontend/)
- **React 18 + TypeScript**: 現代化前端框架
- **Ant Design 5.x**: UI 組件庫 (繁體中文本地化)
- **Vite**: 高性能構建工具
- **React Router v6**: 路由管理 (懶載入)
- **Zustand + React Query**: 狀態管理和資料快取

### 後端架構 (backend/)
- **FastAPI**: 高性能非同步 Web 框架
- **SQLAlchemy 2.0**: 非同步 ORM
- **PostgreSQL 15+**: 企業級資料庫
- **JWT + Google OAuth**: 雙重認證機制
- **Alembic**: 資料庫版本控制

### 容器化部署 (configs/)
- **Docker Compose**: 多服務編排
- **Nginx**: 反向代理和靜態檔案服務
- **PostgreSQL Container**: 資料庫容器化
- **Adminer**: 資料庫管理工具

## 📊 目錄使用指南

### 🚀 開發流程
1. **前端開發**: 在 `frontend/src/` 目錄下開發
2. **後端開發**: 在 `backend/app/` 目錄下開發
3. **測試**: 使用 `claude_plant/development_tools/tests/`
4. **文檔**: 更新 `claude_plant/development_tools/docs/`

### 🔄 部署流程
1. **開發環境**: 使用 `configs/docker-compose.yml`
2. **生產環境**: 使用 `claude_plant/development_tools/deployment/`
3. **備份**: 定期備份到 `claude_plant/development_tools/backup/`

### 📝 文檔管理
- **API 文檔**: `claude_plant/development_tools/docs/api/`
- **使用指南**: `claude_plant/development_tools/docs/guides/`
- **系統架構**: `claude_plant/development_tools/docs/SYSTEM_ARCHITECTURE_ANALYSIS.md`

## 🛡️ 檔案命名規範

### 組件檔案 (frontend/src/components/)
```
ComponentName.tsx      # React 組件
ComponentName.test.tsx # 組件測試
index.ts              # 導出檔案
```

### API 端點 (backend/app/api/endpoints/)
```
module_name.py        # API 端點實現
```

### 資料模型 (backend/app/models/)
```
model_name.py         # SQLAlchemy 模型
```

### 測試檔案 (claude_plant/development_tools/tests/)
```
test_[module_name].py     # Python 測試
[module_name].test.ts     # TypeScript 測試
fixture_[data_type].json  # 測試資料
```

## 🔧 配置檔案管理

### 環境變數層級
```
.env                  # 主要配置 (優先級最高)
.env.ports           # 端口配置
configs/.env         # Docker 配置
configs/.env.production  # 生產環境配置
```

### Docker 配置
```
configs/docker-compose.yml    # 主要服務編排
frontend/Dockerfile          # 前端容器化
backend/Dockerfile           # 後端容器化
```

## 📋 維護檢查清單

### 日常維護
- [ ] 檢查 `claude_plant/development_tools/logs/` 中的日誌
- [ ] 更新 `claude_plant/development_tools/docs/` 中的文檔
- [ ] 執行 `claude_plant/development_tools/tests/` 中的測試

### 定期維護
- [ ] 備份資料到 `claude_plant/development_tools/backup/`
- [ ] 更新依賴項版本
- [ ] 檢查安全漏洞

### 部署前檢查
- [ ] 前端 TypeScript 類型檢查
- [ ] 後端 API 文檔更新
- [ ] 資料庫遷移腳本測試

## 🎯 優化建議

### 效能優化
1. **前端**: 組件懶載入、圖片最佳化
2. **後端**: API 回應快取、資料庫查詢最佳化
3. **資料庫**: 索引設計、查詢分析

### 開發體驗
1. **Hot Reload**: Vite 前端、FastAPI 後端
2. **Type Safety**: 完整 TypeScript 支援
3. **API Documentation**: Swagger UI 自動生成

### 生產部署
1. **容器化**: Docker 多階段構建
2. **反向代理**: Nginx 靜態檔案服務
3. **監控**: 健康檢查和日誌聚合

---

*此結構標準旨在提供清晰的開發指引，確保專案的可維護性和擴展性。*