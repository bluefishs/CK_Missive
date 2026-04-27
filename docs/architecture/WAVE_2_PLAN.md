# Wave 2 Services DDD 遷移 — 計畫（待 Owner 拍板）

> **狀態**：ready-to-execute（待 owner 排執行時段）
> **預估**：1.5~2 小時（Wave 1 經驗壓縮 SOP，預期更快）
> **風險**：LOW-MEDIUM（playbook v1.3 已收錄 4 次踩雷 SOP）
> **依賴**：Wave 1 100% 完成（v5.10.0-rc，2026-04-27 已達成）
> **適用對象**：Owner 排程後可由 dynamic /loop 自我執行

---

## 0. 執行前檢查

```bash
# Wave 1 已穩定運行 ≥ 3 天（觀察 stub DeprecationWarning 是否引發新 bug）
git log --oneline | head -10  # 確認 v5.10.0-rc 後無回退

# 開新分支
git checkout -b refactor/services-ddd-wave2

# Baseline test
cd backend && pytest tests/ -q --tb=no 2>&1 | tail -3
```

---

## 1. Wave 2 範圍：ERP 收斂

### 1.1 為什麼選 ERP

- 已有 `services/erp/` 子目錄（8 檔）+ `services/einvoice/` 子目錄（2 檔）
- **但頂層還有 9 個 expense/invoice/finance 散戶**屬於 erp domain
- 業務獨立性高（與 PM/document 互動少），遷移風險可控
- 完成後 erp 達 17 檔集中，是 services/ 第二大子包

### 1.2 9 檔遷移範圍

```
頂層散戶 → services/erp/ 子包：
- expense_invoice_service.py        → erp/expense_invoice.py        (Facade v2.0)
- expense_approval_service.py       → erp/expense_approval.py       (審批工作流)
- expense_import_service.py         → erp/expense_import.py         (QR+Excel+電子發票)
- finance_ledger_service.py         → erp/finance_ledger.py         (統一帳本)
- finance_export_service.py         → erp/finance_export.py         (Excel/CSV 報表)
- invoice_recognizer.py             → erp/invoice_recognizer.py     (QR+OCR Facade)
- invoice_ocr_parser.py             → erp/invoice_ocr_parser.py     (OCR 解析器)
- invoice_ocr_service.py            → erp/invoice_ocr_service.py    (Tesseract OCR)
- invoice_qr_decoder.py             → erp/invoice_qr_decoder.py     (QR 解碼器)
```

### 1.3 影響面

- **import 點**：54 處分佈於 25 檔（透過 stub 機制走 backward compat）
- **mock.patch 字串**：6 處（已用 ripgrep --multiline 預掃）
  - 5 處 in `test_invoice_ocr.py` (single-line)
  - 1 處 in `test_finance_agent_tools.py` (multi-line)

### 1.4 注意事項

- `invoice_recognizer.py` 是 **Facade**，內部 import `invoice_ocr_parser` + `invoice_qr_decoder`
  - 屬於 §4.5 內部循環 import 風險點
  - **必改 relative import**: `from .invoice_ocr_parser import` 等
- `expense_invoice_service.py` 是 v2.0 Facade，類似結構
- 遷移時須先檢查內部互引用

---

## 2. SOP（沿用 Wave 1 經驗）

按 PLAYBOOK v1.3 標準 5 步驟，預期 1 commit 完成：

```bash
# 1. mkdir 已存在 (services/erp/)
# 2. git mv 9 檔
git mv backend/app/services/expense_invoice_service.py backend/app/services/erp/expense_invoice.py
git mv backend/app/services/expense_approval_service.py backend/app/services/erp/expense_approval.py
... (other 7)

# 3. 建/擴 erp/__init__.py 加新 services 的 explicit re-export
# 4. 在原路徑建 9 個 stub
# 5. 跑測試 + 修 patch 路徑

# 預掃 multi-line patch（PLAYBOOK §4.3 SOP）
rg --multiline 'patch\(\s*["\x27]app\.services\.(expense_|finance_|invoice_)' backend/tests/

# 批次替換
for old in expense_invoice expense_approval expense_import finance_ledger finance_export \
           invoice_recognizer invoice_ocr_parser invoice_ocr_service invoice_qr_decoder; do
  sed -i "s|app\\.services\\.${old}_service\\.|app.services.erp.${old}.|g" backend/tests/**/test_*.py
  sed -i "s|app\\.services\\.${old}\\.|app.services.erp.${old}.|g" backend/tests/**/test_*.py
done
```

---

## 3. DoD 驗證

- [ ] `pytest tests/` 全套件 = 19 failed (baseline) - 0 新增（Wave 1 已驗證 baseline 19 failed）
- [ ] `bash scripts/checks/run_fitness.sh` 6 step 全綠
- [ ] `python -c "from app.services.erp import ExpenseInvoiceService, FinanceLedgerService, ..."` 全 OK
- [ ] 9 條舊 import 路徑仍 work（隨機抽 3 個驗證）
- [ ] service entropy: 26.9% → 預期 24% 左右

---

## 4. Wave 3+ 候選（後續）

| Wave | 範圍 | 檔數 | 優先級 |
|---|---|---|---|
| **W2** | erp 收斂（本計畫） | 9 | **next** |
| W3 | integration 集中（line/telegram/discord 各檔進 integration/<channel>/） | 8 | medium |
| W4 | tender 入子包 | 9~10 | medium |
| W5 | calendar 收斂（已有 calendar/ 但鬆散） | 5 | low |
| W6+ | wiki / memory / taoyuan 等 | various | low |

最終目標：services/ 頂層散戶 < 20%（fitness step 1 GREEN）。

---

## 5. v6.0 stub 移除時間表（Wave 1+2 都涵蓋）

| 階段 | 時間 | 動作 |
|---|---|---|
| Wave 1 stub 移除 | 2026-Q3 | grep 確認 0 使用方後 rm 28 stub |
| Wave 2 stub 移除 | 2026-Q3 | 同上 9 stub |
| 全清理後 entropy 預估 | — | 26.9% → ~16%（達 fitness GREEN）|

---

## 6. 範本化等級

- 本 plan **L2 Reference**：其他 repo 可借用 SOP 結構但範圍須客製
- Wave 2 完成後可寫 **WAVE_2_RETROSPECTIVE.md**，補完範本化案例庫

---

## 7. 何時不該執行

- 距 release 窗口不到 1 週
- ERP 模組有 pending PR（避免 merge conflict）
- 開發團隊有人不在線
- Wave 1 的 28 stub 還沒被生產用戶測試足夠時間（建議 ≥ 3 天）

---

> 引用：`CK_Missive#WAVE_2_PLAN_v1.0`
> 待執行 owner 拍板後可由 dynamic /loop 自我執行（按 Wave 1 模式）
