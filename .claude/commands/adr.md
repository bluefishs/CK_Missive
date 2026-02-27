# /adr - Architecture Decision Record 管理

管理架構決策記錄（ADR）的建立、查詢與維護。

## Usage

```
/adr new "決策標題"     # 建立新的 ADR
/adr list              # 列出所有 ADR 及狀態
/adr check             # 檢查近期變更是否需要 ADR
/adr update NNNN 狀態   # 更新 ADR 狀態
```

## 子命令

### `new` - 建立新 ADR

1. 讀取 `docs/adr/README.md` 取得目前最大編號
2. 從 `docs/adr/TEMPLATE.md` 複製模板
3. 設定編號為 max + 1，填入標題和今天日期
4. 建立檔案 `docs/adr/NNNN-kebab-case-title.md`
5. 更新 `docs/adr/README.md` 索引表，狀態設為 `proposed`
6. 提示使用者填寫背景、決策、後果

### `list` - 列出所有 ADR

1. 讀取 `docs/adr/README.md`
2. 以表格顯示所有 ADR 的編號、標題、狀態、日期
3. 用顏色區分狀態：accepted (綠), proposed (黃), deprecated/removed (灰)

### `check` - 檢查是否需要 ADR

1. 執行 `git log --oneline -20` 查看近期 commits
2. 檢查是否有觸及架構檔案的變更：
   - `backend/app/extended/models/` — DB 模型變更
   - `backend/app/core/dependencies.py` — 依賴注入變更
   - `backend/app/services/ai/` — AI 服務架構變更
   - `frontend/src/router/` — 路由架構變更
   - `frontend/src/types/` — 型別架構變更
   - `docker-compose*.yml` — 部署架構變更
   - `.env` 新增環境變數 — 配置架構變更
3. 對每個觸及架構檔案的 commit，判斷是否為：
   - 新增服務/模型/端點 → 建議 ADR
   - 修改認證/授權邏輯 → 建議 ADR
   - 新增外部依賴/基礎設施 → 建議 ADR
   - Bug 修復/小調整 → 不需要 ADR
4. 輸出建議清單

### `update` - 更新 ADR 狀態

1. 驗證 NNNN 對應的 ADR 檔案存在
2. 更新檔案中的狀態欄位
3. 更新 `docs/adr/README.md` 索引表
4. 有效狀態：proposed, accepted, deprecated, superseded, removed, rejected

## ADR 建立時機指引

**應建立 ADR 的情況：**
- 選擇新的技術或框架
- 改變系統架構或資料流
- 新增外部服務整合
- 改變認證/授權策略
- 新增 Feature Flag 或部署模式
- 建置大型功能（>4 小時工作量）

**不需 ADR 的情況：**
- Bug 修復
- 小型 UI 調整
- 程式碼重構（不改變架構）
- 更新依賴版本
- 文件更新

## 參考

- ADR 模板：`docs/adr/TEMPLATE.md`
- ADR 索引：`docs/adr/README.md`
- 架構圖：`docs/diagrams/`
