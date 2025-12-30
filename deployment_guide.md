# 🚀 增強版公文管理系統 - 部署指南

## 📋 部署檢核清單

### ✅ **階段一：資料庫遷移**

1. **執行 Alembic 遷移**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **執行資料遷移腳本**
   ```bash
   cd backend
   python data_migration_script.py
   ```

3. **驗證遷移結果**
   ```sql
   -- 檢查新增的外鍵欄位
   SELECT column_name, data_type, is_nullable
   FROM information_schema.columns
   WHERE table_name = 'documents'
   AND column_name IN ('contract_project_id', 'sender_agency_id', 'receiver_agency_id');

   -- 檢查關聯統計
   SELECT
     COUNT(*) as total_documents,
     COUNT(contract_project_id) as with_project_link,
     COUNT(sender_agency_id) as with_sender_link,
     COUNT(receiver_agency_id) as with_receiver_link
   FROM documents;
   ```

### ✅ **階段二：後端部署**

1. **更新依賴套件**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **驗證新增的 API 端點**
   ```bash
   # 測試承攬案件下拉選項
   curl http://localhost:8001/api/documents-enhanced/contract-projects-dropdown?limit=5

   # 測試政府機關下拉選項
   curl http://localhost:8001/api/documents-enhanced/agencies-dropdown?limit=5

   # 測試整合搜尋
   curl http://localhost:8001/api/documents-enhanced/integrated-search?limit=10
   ```

3. **檢查 API 文件**
   - 訪問：http://localhost:8001/api/docs
   - 確認新增的「增強版公文管理」分類

### ✅ **階段三：前端部署**

1. **更新前端依賴**
   ```bash
   cd frontend
   npm install
   ```

2. **編譯前端應用**
   ```bash
   npm run build
   ```

3. **測試新功能**
   - 訪問：http://localhost:3000/documents-enhanced
   - 測試 AutoComplete 功能
   - 測試表格排序與篩選
   - 驗證承攬案件搜尋準確性

### ✅ **階段四：整合測試**

1. **功能完整性測試**
   - [ ] 承攬案件搜尋正確對應 `contract_projects` 表
   - [ ] 發文單位搜尋正確對應 `government_agencies` 表
   - [ ] 所有篩選欄位具備 AutoComplete 功能
   - [ ] 表格支援欄位排序
   - [ ] 表格支援欄位篩選
   - [ ] 批次操作功能正常

2. **效能測試**
   ```bash
   # 測試大量資料查詢效能
   curl "http://localhost:8001/api/documents-enhanced/integrated-search?limit=1000" -w "@curl-format.txt"

   # 測試 JOIN 查詢效能
   curl "http://localhost:8001/api/documents-enhanced/integrated-search?contract_case=測試&sender=桃園" -w "@curl-format.txt"
   ```

3. **向後相容性測試**
   - [ ] 原有公文查詢功能正常
   - [ ] 現有資料可正常顯示
   - [ ] 無資料遺失或損壞

## 🔧 **設定檔案**

### **curl-format.txt** (效能測試用)
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

## 📊 **預期效果**

### **修復前問題**
- ❌ 承攬案件搜尋「桃園」會顯示南投案件
- ❌ 搜尋條件無法精確匹配資料表
- ❌ 缺乏多表整合查詢機制
- ❌ 篩選欄位無 AutoComplete 功能

### **修復後效果**
- ✅ 承攬案件精確對應 `contract_projects` 表
- ✅ 發文單位精確對應 `government_agencies` 表
- ✅ 支援多表 JOIN 查詢
- ✅ 所有篩選欄位具備 AutoComplete
- ✅ 表格支援欄位排序與篩選
- ✅ 向後相容現有功能

## 🚨 **注意事項**

1. **資料備份**
   - 執行遷移前請備份資料庫
   - 建議在測試環境先行驗證

2. **效能考量**
   - JOIN 查詢可能影響效能
   - 建議監控資料庫查詢時間
   - 必要時可加入更多索引

3. **錯誤處理**
   - 如遇到外鍵約束錯誤，檢查參照完整性
   - 如遇到 API 404 錯誤，確認路由註冊正確

## 📞 **技術支援**

如遇到部署問題，請檢查：

1. **後端日誌**
   ```bash
   tail -f backend/logs/api.log
   tail -f backend/logs/errors.log
   ```

2. **前端控制台**
   - 打開瀏覽器開發者工具
   - 檢查 Network 和 Console 標籤

3. **資料庫連接**
   ```bash
   # 測試資料庫連接
   python -c "from app.db.database import engine; print('Database connection OK')"
   ```

---

🏢 **乾坤測繪科技有限公司** - 增強版公文管理系統 v2.1