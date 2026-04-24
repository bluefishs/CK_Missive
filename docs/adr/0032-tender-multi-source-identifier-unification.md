# ADR-0032: Tender 多源識別碼統一策略

- **Status**: Accepted
- **Date**: 2026-04-24
- **Deciders**: Aaron (jujuiacc@gmail.com)
- **Related**: ADR-0013 (case_code), ADR-0028 (error contract)

---

## Context

CK_Missive 的 `/tender` 模組整合三個外部資料源：

| 來源 | 識別模型 | 原生主鍵 |
|---|---|---|
| **PCC 政府採購網** (g0v API) | 複合鍵 | `(unit_id, job_number)` e.g. `("A.15.3.2", "115-703")` |
| **ezbid.tw** (爬蟲) | 單一數字 ID | `ezbid_id` e.g. `"2227632"` |
| **g0v 補充 API** | 同 PCC 複合鍵 | 併入 PCC |

v5.5 之前只有 PCC，v5.5.x 加入 ezbid 以補當日即時資料（PCC API 延遲 1-5 天）。
加入時選擇最小侵入路線：**把 `ezbid_id` 複製到 `unit_id` 欄位、`job_number` 留空**，
塞進同一張 `tender_records` 表共用 route `/tender/:unit/:job`。

### 症狀與代價（2026-04-24 盤點）

五輪修復後仍出 bug，追其源頭都指向同一道裂縫：

| # | 症狀 | 位置 |
|---|---|---|
| 1 | hook `enabled: !!u && !!j` 擋掉 ezbid（j 為空） | `useTender.ts:21` |
| 2 | `overviewTab: latest ? ... : <Empty/>` 把 ezbid 打到空 | `TenderDetailPage.tsx:252` |
| 3 | `rowKey = u-j-d` 雙空造成 React key 重複警告 | `SearchTab.tsx:183` |
| 4 | `TenderDetail` type 只描述 PCC shape | `types/tender.ts:59` |
| 5 | `SELECT ezbid_url` 欄位不存在 + `except: pass` | `search.py:193` |
| 6 | `save_search_results` 寫入 `unit_id=''` 累積 9,567 筆壞資料 | `tender_cache_service.py:96` |
| 7 | `isdigit()` 啟發式判別後端分派邏輯 | `search.py:185` |
| 8 | `/tender/` 404（兩空 segment URL 不匹配） | `router/types.ts:167` |
| 9 | Route 用 `:jobNumber?` optional hack | `router/types.ts:167` |

**根因**：PCC-centric 設計 + ezbid 後加時偽裝成 PCC 結構，造成 URL / DB / API / 前端型別四層架構斷層。

---

## Decision

採用 **URL namespace 分流 + discriminated union** 兩階段整合方案：

### Phase 1 — Runtime type 明確化（本次）
- 後端 `/api/tender/detail` response **加 `kind: 'pcc' | 'ezbid'`** 欄位
- 前端 `TenderDetail` 改 discriminated union：
  ```ts
  type TenderDetail =
    | { kind: 'pcc'; unit_id; job_number; title; events; latest }
    | { kind: 'ezbid'; ezbid_id; title; unit_name; budget; status; ezbid_url };
  ```
- 前端 `TenderDetailPage` 依 `detail.kind` 分派到 `<PccDetailView>` / `<EzbidDetailView>` 子元件

### Phase 2 — URL 分流（本次一起做）
- 新路由：
  - `/tender/pcc/:unitId/:jobNumber` — PCC 案件
  - `/tender/ezbid/:ezbidId` — ezbid 案件
- 舊路由 `/tender/:unitId/:jobNumber?` 改為 `<LegacyTenderRedirect>`，單點 heuristic 轉址：
  - 純數字 + 無 jobNumber → `/tender/ezbid/:unitId`
  - 其他 → `/tender/pcc/:unitId/:jobNumber`
- 集中導航 util `getTenderDetailPath(record)`，所有 navigate 呼叫均經此函式

### Phase 3 — 不做（**暫不處理 opaque ID**）
拒絕方案：用 `tender_records.id` 當 URL 識別（如 `/tender/8526`）。
理由：犧牲 URL 可讀性，用戶看 `/tender/2227632` 能立即辨識是 ezbid，
看 `/tender/A.15.3.2/115-703` 能立即辨識是 PCC，保留這個認知成本很低的 cue。

---

## Consequences

### 正向
- 前端型別系統可**編譯期偵測 shape 不匹配**，不再靠 runtime `<Empty>` 才暴露 bug
- URL namespace 語意清楚，外部分享連結可辨識來源
- 後端不用 `isdigit()` 啟發式，依 `kind` 或 URL namespace 明確分派
- 導航邏輯集中在 `getTenderDetailPath`，未來加第 3 源只改一處

### 負向 / 成本
- 8 處 navigate 呼叫點需改寫（util 封裝後為一次性）
- 舊 URL 需 legacy redirect 相容期（外部分享連結仍可用）
- 前端元件拆出 `<PccDetailView>` / `<EzbidDetailView>`，單一元件複雜度下降但檔案數增加

### 遷移路徑
| 舊 URL | 新 URL |
|---|---|
| `/tender/A.15.3.2/115-703` | `/tender/pcc/A.15.3.2/115-703` |
| `/tender/2227632/` | `/tender/ezbid/2227632` |
| `/tender/:u/:j?` (既有 Route) | `<LegacyTenderRedirect>` 自動分派 |

---

## Alternatives Considered

### A. Opaque ID (`/tender/:id`)
拒絕。失 URL 可讀性，用戶排障時無法從 URL 看出資料來源。

### B. 保留現狀 + 加 runtime 防禦
拒絕。治標不治本，未來加第 3 源（如市府標案網）會繼續累積 hack。

### C. 僅 Phase 1（不改 URL）
拒絕。ezbid URL `/tender/2227632/` 的尾斜線奇觀仍在，對外分享不專業。

---

## Verification

- Regression tests：
  - `test_tender_detail_path_util.ts` — util 正確決策 PCC vs ezbid
  - `test_tender_detail_kind_response.py` — 後端兩類 response 都含 `kind`
- 手動驗證：
  - `/tender/A.15.3.2/115-703` → 200 PCC view
  - `/tender/ezbid/2227632` → 200 ezbid view
  - `/tender/2227632/` → 301 redirect → `/tender/ezbid/2227632`

---

**關聯文件**：
- ADR-0013 case_code 跨模組橋樑（類似「明確 namespace」思路）
- ADR-0028 錯誤合約化（本次修 silent-fail 符合該政策）
- `frontend/src/utils/tenderPath.ts`（本次新增）
