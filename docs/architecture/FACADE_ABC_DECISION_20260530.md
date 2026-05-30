# Facade A/B/C 抉擇評估 (Sprint 2.P1.7 收口)

> **日期**：2026-05-30
> **狀態**：待 owner 決策
> **背景**：v6.10 P1 建 12 facades (後加 TenderFacade = 13)，30 天累積 caller 6 個（平均 0.46）
> **參考**：L31 「ROI = entities × usage_rate」+ feedback_stop_overengineering

---

## 現況數據（fitness step 61 audit）

| Facade | importer | 狀態 | 設計目的 vs 真活 |
|---|---|---|---|
| MemoryFacade | 3 | 🟢 healthy | crystallizer / agent / kg 真用 |
| IntegrationFacade | 2 | 🟡 low | LINE/Telegram push 真用 |
| WikiFacade | 1 | 🟡 low | wiki compile cron 用 |
| CalendarFacade | 0 | 🔴 zero | 設計：行事曆統一介面；真活：services/calendar/ 直 import |
| ContractFacade | 0 | 🔴 zero | 設計：合約聚合；真活：repository 層直查 |
| DocumentFacade | 0 | 🔴 zero | 設計：公文 CRUD 收口；真活：endpoints 直接呼 service |
| NotificationFacade | 0 | 🔴 zero | 設計：通知統一；真活：notification dispatcher 直呼 |
| AgencyFacade | 0 | 🔴 zero | 設計：機關查詢統一；真活：agency_service 直呼 |
| VendorFacade | 0 | 🔴 zero | 設計：廠商統一介面；真活：vendor_service 直呼 |
| AIFacade | 0 | 🔴 zero | 設計：AI 統一入口；真活：orchestrator 直呼 |
| ERPFacade | 0 | 🔴 zero | 設計：ERP 聚合；真活：分散 service 直呼 |
| AuditFacade | 0 | 🔴 zero | 設計：audit log 統一；真活：mixin 直接寫 |
| TenderFacade | 0 | 🔴 zero | 設計：標案統一；真活：endpoints 直呼 service |

**Summary**：
- 13 facades / 6 total importers / 平均 0.46
- 10 zero (30 天無人用) / 2 low (1-2) / 1 healthy (≥3)
- 12 facade 平均行數 ~70L（estimate） × 10 zero = ~700L dormant code

---

## 三條路徑

### A — 全力推 facade 採用 (4.5d / Sprint 2.P1.7 原計畫)

**範圍**：13 facade × 平均 3 caller 目標 = 39 importer
- 找直接 import service 的端點改走 facade
- 補 facade 缺的 method
- 加 facade-only-import enforcement rule

**預估**：
- 改 ~30-50 個 endpoint
- 補 ~20 個 facade method
- ~4.5 天 dedicated 開發

**風險**：
- 改完後若仍 < 3 caller/facade → 治理債翻倍（既改散戶又留 facade）
- L31 風險：強推 usage_rate 但 entities 設計不對 → ROI 仍低
- feedback_stop_overengineering 風險：3 caller 是任意門檻，不一定提升維護性

### B — 補強有 momentum 的 3 facade，其餘廢棄 (2d)

**範圍**：
- Memory/Integration/Wiki 3 facade 補完 method + 加 2-3 caller 升到 ≥5
- 其餘 10 zero facade 廢棄
  - 移除 13 個 facade .py
  - 清空 contracts/__init__.py 的 re-export
  - 改 fitness step 61 baseline = 3 facades

**預估**：
- ~600-700L 程式碼移除
- 補 ~5-10 caller 到 active facade
- ~2 天

**優點**：
- L31 ROI：留 entities=3 × usage_rate↑ 比 entities=13 × usage_rate↓ 高
- 承認設計失誤但不放棄已驗證有效的 3 個

### C — 全廢，回到 service 直呼 (0.5d / 推薦)

**範圍**：
- 移除 backend/app/services/contracts/ 整目錄
- 3 active facade caller 改回直接 import service
  - MemoryFacade 3 caller → 3 import 改寫
  - IntegrationFacade 2 caller → 2 import 改寫
  - WikiFacade 1 caller → 1 import 改寫
- 移除 fitness step 61 + facade_adoption_audit.py
- 留下 ADR-0036 標 "rejected after 30d trial"
- 寫 lesson：「Facade 抽象需先看 demand，不是先建供給」

**預估**：
- ~24 個檔案接觸（13 facade + 4 port + 4 adapter + 3 caller 改寫）
- ~0.5 天

**優點**：
- 最徹底承認設計失誤
- 對齊 feedback_stop_overengineering
- ADR-0036 變成 "negative example" 教材
- 釋放維護負擔

**缺點**：
- MemoryFacade 真的活用 — 廢掉等於否定該抽象有效
- 重複造輪子風險

---

## 決策矩陣

| 指標 | A 4.5d | B 2d | C 0.5d |
|---|---|---|---|
| 投入成本 | 高 | 中 | 低 |
| 程式碼增減 | +500L | -600L | -700L |
| 30 天後預期 caller | 39 | 15 | N/A |
| ROI per investment | 不確定 | 中高 | 高 |
| 對齊 L31 | 弱 | 強 | 最強 |
| 對齊 stop_overengineering | 弱 | 中 | 強 |
| 風險 | 治理債翻倍 | 中等 | 失去 Memory 抽象 |

---

## 推薦：B (含 escape hatch 升 C)

**理由**：
1. MemoryFacade 3 caller = 真活 — 完全廢掉浪費既有 momentum
2. Integration/Wiki 也有 momentum 但 borderline — 補完値得試
3. 給 60 天 trial：若 12/24 → ≥5 caller/facade 才繼續，否則升 C 全廢
4. 對齊 L31 但保留 reversible

**60 天驗收條件**（2026-07-30 重評）：
- MemoryFacade ≥ 5 caller ✓
- IntegrationFacade ≥ 5 caller ✓
- WikiFacade ≥ 3 caller ✓
- 任一未達 → 自動升 C 廢棄該 facade

---

## Action Items (給 owner 圈選)

- [ ] **選 A** — Sprint 2.P1.7 4.5d 全推（高風險）
- [ ] **選 B** — 補強 3 active + 廢 10 zero（推薦，2d）
- [ ] **選 C** — 全廢回 service 直呼（0.5d，最徹底）
- [ ] **選 D** — 推延，下一輪覆盤再決定

---

> **元洞察**：facade adoption audit 自身揭發 ADR-0036 抽象層 over-engineered。
> 這就是「治理本身 metric 化」的價值 — 連設計失誤都能 metric 出來。
