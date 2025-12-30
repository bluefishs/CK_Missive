# 乾坤測繪公文管理系統 - 版本管理策略

## 目的
解決專案中反覆出現的版本衝突問題，避免新舊版次問題造成系統反覆檢測修正事宜。

## 版本衝突問題分析

### 已識別的問題檔案

#### Backend 主程式檔案衝突
- `backend/main.py` ✅ **當前使用版本**
  - 完整的 FastAPI 應用程式
  - 包含 CORS 設定、路由掛載、中間件
  - 支援 PostgreSQL 資料庫
  
- `backend/simple_main.py` ❌ **舊版本 - 需要清理**
  - SQLite 版本的主程式
  - 包含內嵌的 CSV 匯入功能
  - 造成 Port 8001 衝突

- `backend/optimized_main.py` ❌ **過時版本 - 需要清理**
  - 中間優化版本
  - 功能已整合到當前 main.py

- `backend/main.py.backup` ❌ **備份檔案 - 需要歸檔**
  - 手動備份檔案
  - 應移動到指定備份目錄

#### 其他重複檔案
- 多個 archive 目錄中的重複檔案
- claude_plant 目錄中的開發階段檔案
- .backup 後綴的檔案

## 版本管理規範

### 檔案命名規範

#### 1. 主要程式檔案
- **生產環境**: 使用標準檔名 (如 `main.py`, `App.tsx`)
- **開發測試**: 添加明確的描述性後綴
  - `main_dev.py` (開發版)
  - `main_testing.py` (測試版)
  - `main_experimental.py` (實驗版)

#### 2. 備份檔案
- **自動備份**: 移至 `claude_plant/development_tools/backup/` 目錄
- **手動備份**: 使用時間戳格式
  - `main_20250910_v1.py`
  - `models_20250910_before_schema_change.py`

#### 3. 歸檔檔案
- **舊版本**: 移至 `claude_plant/archive/` 目錄
- **階段檔案**: 依開發階段分類歸檔

### 目錄結構規範

```
CK_Missive/
├── backend/           # 生產程式碼
├── frontend/          # 生產程式碼
├── claude_plant/
│   ├── archive/       # 歸檔舊版本
│   │   ├── v1.0/
│   │   ├── phase1/
│   │   └── deprecated/
│   ├── development_tools/
│   │   ├── backup/    # 自動備份
│   │   ├── scripts/   # 開發腳本
│   │   └── docs/      # 開發文件
│   └── staging/       # 暫存開發中檔案
```

## 開發流程規範

### 1. 檔案修改流程
1. **修改前**: 自動備份到 backup 目錄
2. **開發中**: 使用 staging 目錄測試
3. **完成後**: 替換生產檔案，歸檔舊版本

### 2. 功能整合流程
1. **新功能**: 在獨立分支或目錄開發
2. **測試**: 完整測試後再整合
3. **整合**: 確保不影響現有功能
4. **清理**: 移除臨時開發檔案

### 3. 衝突解決流程
1. **識別**: 檢查 Port 衝突、路由衝突
2. **停止**: 停止衝突服務
3. **整合**: 合併有用功能到主版本
4. **清理**: 刪除或歸檔衝突檔案

## 工具支援

### 自動化腳本
- `structure_check.ps1` - 檢查檔案結構
- `version_cleanup.py` - 自動清理重複檔案
- `backup_automation.py` - 自動備份機制

### Git 管理
- 使用 `.gitignore` 排除臨時檔案
- 使用分支管理大型功能開發
- 定期 commit 避免檔案丟失

## 立即清理計畫

### Phase 1: 緊急清理 (立即執行)
1. 停止 `simple_main.py` 程序
2. 移除 Port 衝突
3. 確保只有一個 backend 服務運行

### Phase 2: 檔案歸檔 (本週內)
1. 移動 `simple_main.py` 至 archive
2. 移動 `optimized_main.py` 至 archive  
3. 移動所有 .backup 檔案至 backup 目錄

### Phase 3: 結構優化 (下週內)
1. 整理 claude_plant 目錄結構
2. 建立自動備份機制
3. 建立檔案清理腳本

## 預防措施

### 開發規範
1. **單一主程式**: 每個服務只有一個主要執行檔案
2. **明確命名**: 所有非生產檔案使用描述性命名
3. **及時清理**: 完成整合後立即清理臨時檔案
4. **文件記錄**: 重大變更記錄在 CHANGELOG.md

### 監控機制
1. **定期檢查**: 每週檢查重複檔案
2. **Port 監控**: 自動檢查 Port 衝突
3. **日誌監控**: 監控 404、500 錯誤模式

## 成功指標
- 無 Port 衝突錯誤
- 無路由重複定義錯誤
- CSV 匯入等功能穩定運行
- 開發效率提升，減少除錯時間

---
*建立日期: 2025-09-10*
*版本: 1.0*
*負責人: Claude Code Assistant*