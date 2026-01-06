# CK_Missive 開發指引與架構維護機制

## 🛠️ 自動化架構維護機制

### 1. 結構驗證工具
**Python 驗證器**: `claude_plant/development_tools/validation/validate_structure.py`
```bash
# 執行結構檢查
python claude_plant/development_tools/validation/validate_structure.py
```

**PowerShell 驗證器**: `claude_plant/development_tools/scripts/structure_check.ps1`
```powershell
# 僅檢查
.\claude_plant\development_tools\scripts\structure_check.ps1

# 檢查並自動修復
.\claude_plant\development_tools\scripts\structure_check.ps1 -Fix
```

### 2. 開發前檢查流程
每次開始開發或添加新文件前：

1. **閱讀架構規範**: 查看 `STRUCTURE.md`
2. **執行結構檢查**: 運行驗證工具確認當前狀態
3. **按規範放置文件**: 新文件必須放在正確位置
4. **提交前再檢查**: 確保沒有違反架構規範

### 3. 文件放置決策樹

```
新增文件時請問自己：
├─ 是測試文件？ → claude_plant/development_tools/tests/
├─ 是腳本工具？ → claude_plant/development_tools/scripts/
├─ 是部署相關？ → claude_plant/development_tools/deployment/
├─ 是維護工具？ → claude_plant/development_tools/maintenance/
├─ 是備份文件？ → claude_plant/development_tools/backup/
├─ 是開發文檔？ → claude_plant/development_tools/docs/
├─ 是核心後端代碼？ → backend/app/
└─ 是前端代碼？ → frontend/src/
```

## 📋 開發檢查清單

### 新增文件前：
- [ ] 確認文件類型和用途
- [ ] 檢查 STRUCTURE.md 規範
- [ ] 選擇正確的目錄位置
- [ ] 使用描述性文件名

### 提交代碼前：
- [ ] 執行 `validate_structure.py` 檢查
- [ ] 確保沒有在禁止位置添加文件
- [ ] 確認 backend/ 目錄保持純淨
- [ ] 檢查是否有臨時或測試文件留在不當位置

### 週期性維護：
- [ ] 每週執行一次結構檢查
- [ ] 清理不需要的臨時文件
- [ ] 整理歸檔舊的開發文件
- [ ] 更新開發工具和腳本

## 🚨 常見違規情況與解決方案

### 1. Backend 目錄污染
**問題**: 在 backend/ 中添加測試或工具文件
**解決**: 移動到 `claude_plant/development_tools/` 對應子目錄

### 2. 根目錄雜亂
**問題**: 在專案根目錄添加臨時文件
**解決**: 刪除或移動到適當位置

### 3. 開發工具散落
**問題**: 腳本和工具分散在各處
**解決**: 統一歸類到 `claude_plant/development_tools/`

## 🔧 自動化集成

### Git Hooks (建議)
在 `.git/hooks/pre-commit` 中添加：
```bash
#!/bin/sh
echo "🔍 檢查專案結構..."
python claude_plant/development_tools/validation/validate_structure.py
if [ $? -ne 0 ]; then
    echo "❌ 專案結構檢查失敗，請修正後再提交"
    exit 1
fi
```

### CI/CD 集成
在 CI 流程中添加結構檢查步驟：
```yaml
- name: Validate Project Structure
  run: python claude_plant/development_tools/validation/validate_structure.py
```

## 📚 學習資源

1. **架構規範**: `STRUCTURE.md` - 完整的目錄結構說明
2. **驗證工具**: `validate_structure.py` - 自動化檢查腳本
3. **修復腳本**: `structure_check.ps1` - PowerShell 自動修復工具
4. **本指引**: 開發流程和最佳實踐

## ⚡ 快速命令

```bash
# 結構檢查
python claude_plant/development_tools/validation/validate_structure.py

# PowerShell 檢查和修復
.\claude_plant\development_tools\scripts\structure_check.ps1 -Fix

# 查看架構規範
cat STRUCTURE.md

# 查看本指引
cat .claude/DEVELOPMENT_GUIDELINES.md
```

---

## 🛡️ 資料品質管理 Skills

本專案提供以下 Claude Code Skills 來管理資料品質：

### 可用 Skills

| Skill | 說明 | 指令 |
|-------|------|------|
| `/data-quality-check` | 資料品質檢查 | 執行公文資料完整性檢查 |
| `/db-backup` | 資料庫備份管理 | 備份、還原、排程設定 |
| `/csv-import-validate` | CSV 匯入驗證 | 驗證並匯入公文 CSV |

### 快速使用

```bash
# 資料品質檢查
在 Claude Code 中輸入: /data-quality-check

# 資料庫備份
在 Claude Code 中輸入: /db-backup

# CSV 匯入驗證
在 Claude Code 中輸入: /csv-import-validate
```

### Skill 檔案位置

```
.claude/commands/
├── data-quality-check.md   # 資料品質檢查
├── db-backup.md            # 資料庫備份管理
└── csv-import-validate.md  # CSV 匯入驗證
```

---

💡 **記住**: 保持架構規範不僅讓專案更整潔，也讓團隊協作更順暢！