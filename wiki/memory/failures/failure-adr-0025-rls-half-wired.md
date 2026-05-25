---
type: failure
id: adr-0025-rls-half-wired
detected: 2026-05-06
incident_started: 2026-04-21
days_dormant: 13
severity: high
status: resolved
resolved_at: 2026-05-06
fqid: CK_Missive#failure-adr-0025-rls-half-wired
related_adr: [0025, 0028, 0030]
related_lesson: L24
---

# Failure：ADR-0025 Identity Unification「半接通」13 天

## 一句話摘要

ADR-0025 上線後執行了 3 筆初始 alias merge，但 RLS 從未展開 alias group → 對 staff/user 角色等同失效；admin/superuser 角色繞過 RLS 不感知此 bug，**13 天 dormant** 直到單一身份用戶實測才暴雷。

## 時序

- **2026-04-21 05:55** — SuperUser 執行 3 筆 `merge_alias`：王駿穠(13←7) / 張雅惠(17←12) / 李昭德(19←11)。notes 「ADR-0025 initial cleanup」。
- **2026-04-21 ~ 2026-05-06**（13 天）— 沒有任何單一身份（staff/user）用戶測試過跨 alias 訪問已 merge 帳號 PUA 對應的 document/project。所有 canonical 是 admin/superuser，走 admin path 跳過 RLS。
- **2026-05-06** — 用戶以「李昭德 gmail (id=19)」帳號訪問 `documents/2463`（project 21，PUA 在 alias id=11）。**修齊前 is_admin=False（雖 role='admin'）→ 走 RLS path → 不展開 alias → 拒絕 → 「找不到資料」**。
- **同日** — 雙線修復：
  - 修 (A)：DB role/flag 對齊（id=19 補 `is_admin=True`，立即解單 case）
  - 修 (B)：RLS 加 `get_alias_group_subquery` 三入口接通（永久解單一身份用戶 + 未來新 merge）

## 為何 13 天沒被發現（戰略洞察）

### 觸發條件需「**多重邊角組合**」同時成立
1. 用戶帳號是 **alias** 或 **canonical 的 alias 那端**（多帳號之一）
2. 用戶角色是 **staff/user**（不是 admin/superuser，不繞過 RLS）
3. 用戶實際**訪問 alias 另一端 PUA 對應的 document/project**

### 全系統符合條件的人
- 王駿穠：canonical=13 superuser → 不繞 RLS 又是 admin，永遠繞過
- 張雅惠：canonical=17 admin → 同上
- **李昭德：canonical=19 但 DB `is_admin=False`** ← 唯一觸發點

### 為何驗證沒抓到
- 單元測試 mock RLSFilter，沒測 merge 後 end-to-end 行為
- Integration test 沒有 alias 場景 fixture
- Fitness function 沒有「merge 後跨帳號讀取」smoke test
- Owner 體感驗證沒做（merge 後沒人切到 alias 帳號實測）

## 與 ADR-0028 / 0030 的關聯

**ADR-0028 silent failure 政策**只覆蓋「主流程吞錯」，沒覆蓋「**功能邏輯半接通的 dead code**」。
**ADR-0030 GO/NO-GO** 著重 P95 latency 與 baseline 成功率，沒覆蓋「**權限模型語意正確性**」。

兩個 ADR 都不會抓這類事故 — 屬於 v3.0 review 洞察 11「整合 commit ≠ 活體運轉」家族。

## 補強措施（已落地）

1. **`RLSFilter.get_alias_group_subquery`** — `COALESCE(canonical_user_id, id)` 為 root，雙向 OR 展開
2. **`get_user_accessible_project_ids` / `check_user_project_access` / `apply_project_rls`** 三入口統一改用 alias group subquery
3. **Regression tests**：`TestRLSFilterAliasGroupExpansion` 3 tests + 既有 19 共 22 全綠
4. **DB end-to-end 驗證**：李昭德 gmail (id=19) 對 project 21 access = True ✓

## 補強措施（待排期）

| 措施 | 優先 | 工時 |
|---|---|---|
| **Fitness step 17：alias_rls_e2e_check.py** — 對每個已 merge alias，模擬從 alias 端讀取 canonical PUA 對應 document 應 200 | P1 | 2 hr |
| **FK 轉移**：merge 時將 `project_user_assignments.user_id = alias` 自動 UPDATE 為 canonical（讀取已由 RLS 展開涵蓋，寫入面對齊預防 unmerge 混亂） | P2 | 4 hr |
| **重新驗證所有「真活」ADR**：清查 ADR registry 找其他可能半接通的 commit | P2 | 1 day |
| **Owner 體感 SOP**：每個 ADR 上線後，owner 用「最受影響的單一身份用戶」實測 1 次 → 寫 wiki diary | P1 | 永久 |

## Lesson L24（建議寫入 LESSONS_REGISTRY）

> **「初始 cleanup」一次跑完不等於功能落地** — 寫 service + UI + DB + 跑一次 ≠ 整體系統落實。
> 觸發條件需「多重邊角組合」同時成立的功能，必須補一個對該特定組合的 fitness/integration test，
> 否則只要日常使用者組合不命中就會 dormant 數週數月。

## 為什麼今天才被發現的元洞察

- 此 bug 觸發點極小：**全系統只有李昭德這 1 人**符合條件（canonical alias + 非 admin/superuser 真實判定）
- 只有當 owner 實測新事故鏈（5/04 認證 10 fix 後再實際登入訪問 document）才會踩到
- v6.8 認證鏈 10 fix 把用戶體感修順 → **暴露原本被 401/redirect 蓋住的下游 RLS bug**
- 這是「系統內病灶照亮鏈」典型：上層 bug 修了，下層 dormant bug 才被照出來

## 相關 commit

- 2026-04-21：原始 merge_alias 執行（commit hash 待查 user_merge_log.merged_by audit）
- 2026-05-06：TaskB RLS alias group 展開（本次修復）

## 關聯資料

- DB：`user_merge_log` 3 筆紀錄（id=1,2,3）
- 影響 endpoint：documents/{id}/detail、documents/list、projects/* 全 RLS path
- 影響使用者：實質僅李昭德 1 人感知（其他 alias canonical 都繞過 RLS）
