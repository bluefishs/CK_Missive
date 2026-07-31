# 專案自我檢核與進化機制 — 2026-07-31 強化後全貌

> **起因**：owner「連日反覆手動檢測才發現缺陷」「無法針對前後端與頁面 UI 等管控與檢測」。
> **本文**：統整當日所有規劃項的收尾狀態 + 強化後的檢核架構 + 仍存在的盲區。

---

## 1. 檢核層級全貌（強化後）

| 層 | 機制 | 看什麼 | 抓得到 / 抓不到 |
|---|---|---|---|
| **程式碼** | fitness 1–76 步 | 原始碼、設定、型別 SSOT、命名、路由註冊 | ✅ 結構違規　❌ 「跑起來是壞的」 |
| **資料/行為** | producer watchdog（15 producer） | job 有沒有真的產出東西 | ✅ 沉默成功　❌ 產出有沒有價值 |
| **服務** | `/health` + 五系統公網探針 + L76 | 服務活著、業務量門檻 | ✅ 服務死　❌ 單頁壞 |
| **🆕 頁面（深度）** | `ui_flow_smoke.cjs` 6 條流程 | owner 回報過的具體互動 | ✅ 特定功能消失/失效 |
| **🆕 頁面（廣度）** | `ui_page_sweep.cjs` 87 條路由 | 白畫面／錯誤字樣／致命 console error／被踢回登入 | ✅ 大面積崩壞、前後端契約不一致 |
| **🆕 檢核器自身** | producer registry + fitness step 77 | 檢核有沒有在跑、上次結果 | ✅ 「以為有在檢核」 |

### 為何要分深度與廣度

- **深度**回答「這個功能還在嗎」——當日多起缺陷是**功能消失**（ezbid 沒有建案鈕、
  verified 紀錄整列不可點），API 全部正常。
- **廣度**回答「有沒有整頁壞掉」——首跑即發現 `/ai/erp-graph` 的前後端契約不一致，
  **這個問題沒有人回報過，因為那張統計卡一直安靜地顯示 0**。

---

## 2. 自動化鏈路（不另建通知管道）

```
Windows 排程 04:15 / 04:30
   └─ run_ui_smoke.sh [--sweep]
        ├─ ui_smoke_auth.py     自簽 20 分鐘 admin session（不碰任何人登入）
        └─ ui_flow_smoke.cjs / ui_page_sweep.cjs
              └─ 寫 wiki/memory/integration-health/ui-{flow,sweep}.json
                    ├─ producer watchdog（file_fresh 30h）→ 既有每日 LINE 告警
                    └─ fitness step 77（新鮮度 + 上次是否 FAIL）
```

**刻意沿用既有 producer 契約而非新建告警**：新增第二套通知＝下一個異質同工。
且這符合契約規則 4「驗證型 job 也必須留下可驗產出」——
**檢核器自己停跑，會被既有機制抓到**（cf_tunnel_verify 空跑數月的教訓）。

安裝：`powershell -File scripts/deploy/install-ui-smoke-task.ps1`

---

## 3. 當日規劃項收尾狀態

| 項目 | 狀態 | 證據 |
|---|---|---|
| L1 ezbid 入口 | ✅ | 一鍵建案已上線，UI 檢核 PASS |
| L2 建案防重複 | ✅ | 候選偵測 + 409 擋下 + 關聯既有，實測通過 |
| L3 標案↔案件回指 | ✅ | migration `20260731a001`；187 `source_tender_id=8526` |
| L4 財務接續 | ✅ | 報價可由 URL 帶入預算 |
| L5 呈現一致性 | ✅ | `TenderActionBar` 兩分支共用 + regression |
| 方案 B（成案即創財務號） | ✅ | `ProjectService.create` 自動產號 + 財務容器（冪等、fail-soft） |
| **方案 A（補 188/190/191）** | ✅ | **fitness step 74 由 🟡 4 筆 → ✅ GREEN 0 筆** |
| R1 同名元件偵測 | ✅ | 異質同工審計新增 **H4**，現況 4 組真候選 |
| R2 清孤兒 DetailPageHeader | ✅ | 已刪 + 移除其測試 mock |
| R3 核實三組同名元件 | ✅ | 見 §4 |
| case-finance 契約 SSOT | ✅ | 後端 `CaseFinanceResponse` 綁 response_model + 前端 types/erp |
| 測試外送 LINE | ✅ | conftest 抽憑證式安全網（三版才對）+ 守護測試 |
| **UI 自我檢核** | ✅ | 深度 6/6、廣度 85/87 |
| **檢核自動化** | ✅ | Windows 排程 + producer registry + fitness step 77 |

---

## 4. R3 核實結果（驗證優先於收斂）

| 同名元件 | 核實 | 判定 |
|---|---|---|
| ExpensesTab ×2 | 一為唯讀彙總、一為 CRUD | 語意不同，**不強抽**；已用 regression 鎖住「都必須可鑽取」+ 型別 SSOT |
| MermaidBlock ×2 | props 不同（`chart` vs `code`）、219 vs 103 行 | **真候選**：同名同職責不同介面，收斂前需驗行為等價 |
| CategoryPieChart | **其實 3 份**（tender / erpDashboard / reports/BudgetCharts） | **真候選** |
| StaffTab ×2 | 223 vs 189 行、資料呼叫 0 vs 9（受控 vs 自主） | 職責不同，同名易混淆；建議改名而非合併 |
| ReportsPage 等 ×3 組 | 開檔確認為 re-export shim | **合理**（用「被引用數 0」判斷會誤報） |
| EvolutionTab ×2 | CLAUDE.md 已載明刻意分歧 | **合理** |

---

## 5. 仍存在的盲區（誠實列出）

1. **動態路由未納入廣度掃描**：87 條是靜態路由；`/documents/:id` 這類需要有效 ID，
   目前只有 flow smoke 用固定 ID 覆蓋少數幾條。
2. **只驗「看得到」，不驗「做得對」**：掃描不會送出表單、不會核銷一張發票。
   寫入型流程仍需 flow smoke 逐條擴充。
3. **LINE 登入無法自動驗到底**：需真實 OAuth，自動化只能驗到「正確導向 LINE」。
4. **`/admin/deployment` 的 503** 是環境未設 GitHub Token，非程式缺陷；
   目前會讓 step 77 恆紅，需 owner 決定補 token 或列入 allowlist。
5. **後端測試 52 個既有失敗**未處理（已用 stash 對照確認與當日改動無關）。

---

## 6. 元教訓（當日累積，補進紀律）

> **任何比對／相似度／統計工具，採信其輸出前必須先用「已知為真」與「已知為假」
> 各驗一次。驗不出鑑別力的工具，其輸出一律不得用於判斷。**

當日六次踩到「訊號存在 ≠ 訊號有效」：

| # | 工具 | 假訊號 |
|---|---|---|
| 1 | pg_trgm 對中文 | 量出假的「38% 案件重複」 |
| 2 | 嵌入相似度對前端元件 | 719 個 0.905 的無意義配對 |
| 3 | 背景測試空輸出檔 | 差點報成「0 個失敗」 |
| 4 | 測試命中自己的註解 | 假綠一次、假紅兩次 |
| 5 | 過期的 mock | 測試真的把告警推到 owner 手機 |
| 6 | **我自己寫的 UI 檢核器** | 5 項 SKIP 仍印「GREEN 全部通過」；另把自我限流 429 誤報成 4 頁壞掉 |

第 6 項最值得記：**我做來抓假綠的工具，自己就是假綠**。
所以 §2 的鏈路才刻意讓「檢核器自己停跑」也會被抓到。
