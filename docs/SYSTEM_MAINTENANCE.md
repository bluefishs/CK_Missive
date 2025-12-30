# 系統維護與故障預防指南

## 📝 文件更新完成清單

### ✅ 已完成的文件更新

1. **README.md** - 主要系統說明文件
   - 更新了正確的端口資訊 (前端: 3006, 後端: 8001)
   - 添加了詳細的故障排除章節
   - 新增API端點對照表
   - 包含重要提醒和配置說明

2. **STRUCTURE.md** - 專案架構文件
   - 更新了資料庫架構說明 (PostgreSQL)
   - 詳細說明了模型與資料庫對應關係
   - 新增API架構說明
   - 強調關鍵欄位名稱對應

3. **docs/DATABASE_SCHEMA.md** - 資料庫結構說明
   - 完整的表格結構文檔
   - 欄位名稱對照表
   - 常用查詢範例
   - 維護指令說明

4. **docs/DEVELOPMENT_GUIDE.md** - 開發流程指南
   - 新開發者上手指南
   - 常見問題解決方案
   - 程式碼規範說明
   - 測試與驗證流程

5. **check_model_db_consistency.py** - 自動化檢查工具
   - 檢查模型與資料庫一致性
   - 自動發現欄位不匹配問題
   - 提供詳細的檢查報告

## 🔧 關鍵修復點總結

### 1. 表名與模型對應
```python
# 正確對應
class OfficialDocument(Base):
    __tablename__ = "documents"  # ✅ 對應實際表名
```

### 2. 欄位名稱統一
```python
# 正確欄位名稱
sender = Column(String(200))     # ✅ 不是 sender_agency
receiver = Column(String(200))   # ✅ 不是 receiver_agency  
priority = Column(Integer)       # ✅ 不是 priority_level
```

### 3. API路徑規範
```javascript
// 正確API調用
fetch('/api/documents/documents-years')  // ✅
// 路徑格式: /api/{prefix}/{endpoint}
```

### 4. 資料類型處理
```python
# 正確處理方式
"doc_type": str(doc.doc_type) if doc.doc_type else ""  # ✅
# 避免: doc.doc_type.value (當欄位是字串時)
```

## 🛡️ 預防措施

### 1. 定期執行檢查
```bash
# 每次重大修改後執行
cd claude_plant/development_tools/scripts
python check_model_db_consistency.py
```

### 2. 開發前檢查清單
- [ ] 閱讀 `docs/DEVELOPMENT_GUIDE.md`
- [ ] 確認模型與資料庫對應關係
- [ ] 測試API端點路徑
- [ ] 驗證欄位名稱一致性

### 3. Git提交前驗證
```bash
# 後端測試
curl http://localhost:8001/health
curl "http://localhost:8001/api/documents/?skip=0&limit=5"

# 前端測試  
curl http://localhost:3006

# 資料庫檢查
docker exec CK_Missive_postgres psql -U ck_user -d ck_documents -c "\dt"
```

### 4. 文檔維護規範
- 新增API端點時更新 `README.md` 中的API端點對照表
- 修改資料庫結構時更新 `docs/DATABASE_SCHEMA.md`
- 新的常見問題添加到 `docs/DEVELOPMENT_GUIDE.md`

## 🚨 緊急故障處理流程

### 步驟1: 快速診斷
```bash
# 檢查服務狀態
docker ps | grep postgres  # 資料庫
curl http://localhost:8001/health  # 後端
curl http://localhost:3006  # 前端
```

### 步驟2: 檢查日誌
```bash
# 後端日誌 (查看terminal輸出)
# 前端日誌 (查看terminal輸出)
# 瀏覽器控制台 (F12 → Console → Network)
```

### 步驟3: 執行自動檢查
```bash
cd claude_plant/development_tools/scripts
python check_model_db_consistency.py
```

### 步驟4: 參考文檔
1. 檢查 `README.md` 的故障排除章節
2. 查看 `docs/DEVELOPMENT_GUIDE.md` 的常見問題
3. 對照 `docs/DATABASE_SCHEMA.md` 確認結構

## 📚 文檔導覽

| 文檔 | 用途 | 使用時機 |
|------|------|----------|
| `README.md` | 系統概覽、快速啟動 | 初次使用、故障排除 |
| `STRUCTURE.md` | 專案架構理解 | 開發規劃、架構確認 |
| `docs/DATABASE_SCHEMA.md` | 資料庫結構詳情 | 資料庫操作、欄位確認 |
| `docs/DEVELOPMENT_GUIDE.md` | 開發指南 | 日常開發、問題解決 |
| `docs/SYSTEM_MAINTENANCE.md` | 維護指南 | 系統維護、預防措施 |

## 🔄 定期維護任務

### 每週任務
- [ ] 執行模型一致性檢查
- [ ] 檢查系統服務狀態
- [ ] 更新文檔 (如有變更)

### 每月任務  
- [ ] 備份資料庫
- [ ] 檢查依賴更新
- [ ] 審查系統效能

### 重大更新後
- [ ] 更新所有相關文檔
- [ ] 執行完整測試
- [ ] 通知團隊變更內容

---

**維護者**: 系統開發團隊  
**最後更新**: 2024年9月11日  
**下次檢查**: 建議每週執行一次自動檢查