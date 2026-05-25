# ADR-NNNN: 標題

> **狀態**: proposed | accepted | deprecated | superseded by ADR-XXXX | removed
> **日期**: YYYY-MM-DD
> **決策者**: [參與決策的人員]
> **接通完整度**: L1 | L2 | L3 | L4 （見下方分級）
> **關聯**: ADR-XXXX, CHANGELOG vX.XX.0, docs/specifications/XXX.md

## 背景

什麼問題或需求驅動了這個決策？描述當時的情境和限制條件。

## 決策

採取了什麼方案？具體描述技術選型或架構變更。

## 後果

### 正面
- 帶來了什麼好處？

### 負面
- 增加了什麼複雜度或限制？

## 替代方案

考慮過但未採用的方案及其被排除的原因。
（大型架構決策必填，小型可省略）

---

## §How to Apply（強制；新 ADR 從 proposed → accepted 前必走）

> **依據**：[`.claude/rules/adr-anti-half-wired-sop.md`](../../.claude/rules/adr-anti-half-wired-sop.md)
> **起因**：ADR-0025 dormant 13 天事故（2026-04-21 上線 → 5/4 觸發暴露）；ADR-0028 「3 守護假基線」事故（2026-04-22 加守護 → 5/15 揭發未進 pre-commit）

### A. 程式碼接通完整度
- [ ] 主路徑實作（service / API / UI / DB schema）
- [ ] 下游消費端對齊：哪些既有模組需要感知這個新概念？逐一列出 + 修
- [ ] 讀取 / 權限 / RLS 是否有變動？若是，全部 endpoint + repository 重新檢視
- [ ] 寫入面 vs 讀取面是否對稱？例如 merge 寫了 canonical_user_id 但 RLS 沒展開 = 半接通

### B. 自動驗證機制
- [ ] 至少 1 個 unit test 鎖定核心邏輯
- [ ] 至少 1 個 integration test 涵蓋邊角組合
- [ ] fitness function 月跑驗證（若邏輯可能 silent stale）
- [ ] Prometheus alert rule（若邏輯產生 metric）
- [ ] **新守護腳本必須附 proof of execution**（pre-commit log / scheduler add_job grep / startup hook 名稱）— 避免重蹈 ADR-0028 覆轍

### C. 邊角組合識別（防 dormant）
- [ ] 列出本 ADR 的「最不容易繞過」用戶身份組合
- [ ] 該組合有對應 fitness / integration test
- [ ] Owner 切到該身份實測 1 次 + 寫 wiki diary 紀錄體感

### D. 上線後 7 天追蹤
- [ ] 第 7 天 owner check-in
- [ ] 觀察相關 metric / alert 有無觸發
- [ ] 無 friction 7 天 → 真活宣告 + 寫 evolution

### E. 文件對齊
- [ ] 寫入 `wiki/memory/diary/` 上線當天紀錄
- [ ] 更新 `docs/architecture/ADR_HALF_WIRED_AUDIT_*.md` 對應條目
- [ ] CHANGELOG 標明本 ADR 接通完整度級別

---

## 接通完整度分級（自評）

| 級別 | 描述 | 範例 |
|---|---|---|
| **L1** | 文件型不需驗證（純 governance / convention） | ADR-0011 教訓性文件 |
| **L2** | 完整接通：程式碼 + 自動驗證 fitness/E2E + **守護腳本經 proof of execution 驗證** | ADR-0028（須修正後驗證 .git/hooks/pre-commit 真呼叫 3 守護） |
| **L3** | 半接通風險：程式碼接通但無自動驗證 | ADR-0014 Hermes 取代 OpenClaw |
| **L4** | 高風險：複雜邊角 + 無/不足驗證 | ADR-0022 Memory Wiki / ADR-0033 |

**目標**：所有新 ADR 必須達 L2，否則需在 ADR 內註明「待補驗證」+ owner 14 天內補完。
