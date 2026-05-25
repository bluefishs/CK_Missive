---
type: failure
id: generic-admin-regex-overmatch
detected: 2026-05-06
severity: medium
status: resolved
resolved_at: 2026-05-06
fqid: CK_Missive#failure-generic-admin-regex-overmatch
related_adr: [0025]
related_failure: [adr-0025-rls-half-wired]
related_lesson: L25
sibling_pattern: half-wired
---

# Failure：GENERIC_ADMIN_KEYWORDS regex 過寬誤殺業務公文

## 一句話摘要

`useDispatchWorkData.ts` 的「通用行政文件」過濾 regex 用了**業務術語**作為過濾關鍵字（系統建置 / 工作計畫 / 道路專案系統 / 教育訓練 / 議約 / 採購），導致 dispatch=157 的 5 筆業務公文全被當行政事項過濾，UI 顯示「公文對照 5 筆」但 list 為空。

## 時序

- **觸發點不明**：原 GENERIC_ADMIN_KEYWORDS pattern 從 dispatch workflow 設計初期就存在（commit 待考據），業務上一直沒人踩到「subject 含這些關鍵字」的 case。
- **2026-05-06 13:43–13:45**：dispatch=157「115年_派工單號000」被建立並 link 5 個業務公文（系統建置作業工作計畫書 / 道路專案系統建置工作計畫 等）。
- **2026-05-06 14:15+**：用戶訪問 `/taoyuan/dispatch/157?tab=correspondence`，title「公文對照 5 筆」但實際 list 1 筆（其實 0 筆，那 1 筆來自其他 component）。
- **2026-05-06 15:30**：根因定位 + 縮小 regex（commit 待補）。

## 根因鏈

```
useDispatchWorkData.unassignedDocs 過濾規則
    ↓
GENERIC_ADMIN_KEYWORDS = /契約書|保險|教育訓練|系統建置|議約|採購|印鑑|投標|工作計畫|道路專案系統/
    ↓
業務性詞「系統建置 / 工作計畫 / 道路專案系統 / 教育訓練 / 採購 / 議約」過於廣義
    ↓
本案件主題就是「系統建置作業工作計畫書」、「道路專案系統建置」
    ↓
5 筆 subject 全 match → 全 filter out → unassignedDocs.length = 0
    ↓
UI 顯示「5 筆」title (來自 stats.linkedDocCount，未過濾)
    但 list 為 0 (來自 unassignedDocs，過濾後)
    → 用戶感受「title 5 筆但實際看不到」
```

## 為何 dormant

「業務 vs 行政」分類這件事**用詞模糊**：
- 「系統建置作業工作計畫書」— 在這個案件叫業務（系統就是要建置的標的）
- 「保險作業工作計畫書」— 在別的案件可能叫行政（保險不是業務）

regex 是 word-level match，無法區分上下文，造成此類**業務術語撞詞 dormant bug**。

觸發條件（要全部成立才會踩到）：
1. dispatch link 多筆公文（單一筆即使被過濾也只是少 1 個 list item，不易發覺）
2. 公文 subject 中含**業務級**的「系統建置 / 工作計畫 / 道路專案系統」等
3. 用戶實際進入 `/correspondence` view 並對照 stats title 與 list 內容

本系統內第一個踩到這 3 個條件的 dispatch 就是 #157（所以剛建立當天就暴雷 — 沒 dormant 太久，但 pattern bug 本身已 dormant）。

## 補強措施（已落地）

### A. regex 縮小（commit 待補）
```
- 原: /契約書|保險|教育訓練|系統建置|議約|採購|印鑑|投標|工作計畫|道路專案系統/
+ 新: /契約書印鑑|履約保證|意外保險|投標保證|押標金|印鑑卡/
```

縮小邏輯：只保留**真正純行政、絕對不會與業務查估/丈量混淆**的單據詞彙。

### B. 5 筆 subject 都 PASS 新 pattern（驗證 commit 待補）
- 564 / 833：subject 含「系統建置」 → 新 pattern 不殺 ✓
- 824 / 846 / 858：subject 含「道路專案系統建置工作計畫」 → 新 pattern 不殺 ✓

## 補強措施（規劃中）

### C. Fitness step 19：generic_filter_audit
對所有「業務分類用 regex」做 false-positive rate audit：
- 給定該 regex 應用對象（如 documents.subject）
- 計算 match 比例
- match 比例 > 5% 視為 over-match suspect → warning
- 預期所有 GENERIC_ADMIN regex 命中率應 < 1%

### D. SOP §regex 保守原則
寫入 `.claude/rules/adr-anti-half-wired-sop.md`：
1. **過濾性 regex 必須極度保守**：寧可 false-negative（漏放）也不要 false-positive（誤殺）
2. **業務性 vs 行政性 詞彙必須明確區分**：契約書印鑑（純行政）vs 系統建置（可能業務）
3. **regex 過濾必須附「pattern 來源 + 預期 match 比例」註解**
4. **每加一個過濾關鍵字都要跑 false-positive 驗證**（用既有資料樣本）

## 元洞察：與 ADR-0025 半接通的對應關係

| 維度 | ADR-0025 半接通（5/06 早上） | GENERIC_ADMIN_KEYWORDS 過寬（5/06 下午） |
|---|---|---|
| 共通病灶 | 寫了某個邏輯但**驗證面**未對齊 | 寫了某個過濾但**業務面**未對齊 |
| dormant 條件 | 跨身份組合（staff + 多帳號 + alias）才觸發 | 跨主題組合（業務術語撞行政詞）才觸發 |
| 表象 | 用戶看不到自己的專案 | 用戶看不到自己的公文 |
| 修法本質 | 加 alias group 展開 | 縮小 regex 範圍 |
| 預防工具 | Fitness step 17 alias_rls_e2e | Fitness step 19 generic_filter_audit（規劃中）|

兩個都是「**程式邏輯沒錯，但對特定資料模式失效**」的 dormant bug 範本。

## Lesson L25（建議寫入 LESSONS_REGISTRY）

> **過濾性程式碼必須極度保守 — 特別是 regex / keyword match。**
>
> 「黑名單型」過濾（過濾掉 X）的 false-positive 代價很高（用戶資料消失）；
> 「白名單型」過濾（保留 X）的 false-negative 代價較低（多顯示無關項，但可見）。
>
> 設計過濾條件時的 default：用白名單，不用黑名單；
> 不得已用黑名單時，pattern 必須**極度精確**（含限定詞、不可單字 OR），
> 並附「false-positive rate 驗證」單元測試或 fitness check。

## 為什麼今天才被發現的元洞察

- pattern 從早期就存在；過去 dispatch link 的公文 subject 多用「函送 XXX」「函覆 YYY」等通用句型，少含業務術語
- 直到本案件主題「**系統建置作業工作計畫書**」被使用 → subject 撞 regex
- 與 ADR-0025 案例同樣是「**特定主題型用戶**首次踩到才暴露**通用配置型 bug**」 — 這是**單一身份體感不可被工程體感取代**的二次驗證

## 相關資產

- `frontend/src/components/taoyuan/workflow/useDispatchWorkData.ts` — 修復點
- `wiki/memory/failures/failure-adr-0025-rls-half-wired.md` — 同 day 半接通範本
- `.claude/rules/adr-anti-half-wired-sop.md` — 防範 SOP（regex 守則待加）
