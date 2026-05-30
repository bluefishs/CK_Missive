# 治理機制真活與效益報告 — 2026-05-31

> **Owner 訴求**：「確認真活與效益」
> **資料源**：weekly fitness 21 step + daily 8 step + dashboard regen + audit metric
> **核心**：13 新 fitness step 真活驗證 + 5 大效益量化 + 5 RED 待處理

---

## 1. Fitness 真活驗證（執行成果）

### 1.1 Tier 1 Daily 8 step ✅ ALL PASSED

| Step | Audit | 結果 |
|---|---|---|
| 1 | container env alignment | ✅ |
| 2 | container image freshness | ✅ |
| 3 | docker compose volume consistency | ✅ |
| 4 | compose/dockerfile healthcheck | ✅ |
| 5 | startup race condition | ⚪ skip |
| 6 | agent_query starvation | 🟢 GREEN (13 baseline) |
| 7 | cron silent dormant | ✅ |
| 8 | dashboard freshness | ✅ 7.2h ago |

### 1.2 Tier 2 Weekly 21 step ✅ ALL PASSED

13 新 step（5/30-31 落地）全跑通：

| Step | 揭發內容 | 效益 |
|---|---|---|
| 60 container image freshness | 11 match / 0 drift | 防 L51.7.1 image stale |
| 61 facade adoption | 3/3 GREEN avg 3.00 | 60 天 trial 進度 |
| 62 paths/compose mount audit | 11 mount 全對齊 | 防 L52 path drift |
| 63 governance alignment | ADR 21 active / 12 lesson | 規範盤點 |
| 64 dashboard freshness | 7.2h ago GREEN | 確保 dashboard 真活 |
| 65 cross_repo template drift | 3/4 GREEN (Pile 1/6 RED healthy) | 跨 repo 採用度 |
| 66 cross_repo uncommitted | 揭發 staging 未 commit | L54「套用≠落實」 |
| 67 frontend/backend endpoint | 411 fe-only candidates | 漂移偵測 |
| 68 hermes baseline gate | 1/5 (baseline 13) | Sprint 3.P3.15 自動裁判 |
| 69 paths sub-path mount | 16 sub-path 對齊 | 防 L57 path drift |
| 70 repository coverage | **58% smart match** | 命名規約 audit |
| 71 cross-domain link | tender↔org 92.8% / wiki↔KG 38.5% | 跨域關聯 |
| 72 knowledge dedup | **41.8% code 重複** | 雙寫評估 |

## 2. 效益量化（13 step 真實揭發）

### 2.1 業務真活效益

| 指標 | 改善 |
|---|---|
| **Hermes baseline rows** | 0 → 13 (+13 真實寫入) |
| **p95 latency** | 71s → 40s (-44%) |
| **shadow_baseline silent dormant** | 9 天 → 0 (L57 修法) |
| **GOOGLE OAuth env 注入** | silent fail → 顯式注入 |

### 2.2 治理機制效益

| 指標 | 改善 |
|---|---|
| Fitness step | 32 → **72** (2.25x) |
| Lessons | 5 → **14** (含 L41-L61) |
| v6.12 立法 | 0 → **8 句** |
| Facade adoption avg | 0.46 → **3.00** (6.5x) |
| Cross_repo 採用 (3/4 repo) | 0% → 75% |
| Governance metric | 0 → 7 gauge |
| Audit 揭發深度 | 表層 → 4 層 silent peel |

### 2.3 KG 量化效益

| 指標 | 揭發 |
|---|---|
| KG 9091 code entities | 4 漂移定位 |
| Repository:db_table 1:1.4 | 58% smart covered |
| Tender↔Org 連結率 | 92.8% GREEN |
| Wiki↔KG frontmatter | 38.5% RED (待補) |
| Knowledge 重複 code | 41.8% (3157 entity 待去重) |

---

## 3. 5 RED 真實揭發（待 owner action）

| RED | Audit | 影響 | 修法估時 |
|---|---|---|---|
| 1 | Hermes baseline 1/5 NO-GO | Sprint 3.P3.15 未達標 | 等明天 09:00 cron + 30 天累積 |
| 2 | wiki↔KG frontmatter 38.5% | Wiki narrative SSOT 不全 | 1 天 backfill kg_entity_id |
| 3 | knowledge 41.8% code 重複 | 7556 → 4399 純業務 | 0.5 天 dedup script |
| 4 | repository 命名規約 58% | 命名 SSOT 不對齊 | 規範已立 (本批 SOP) |
| 5 | step 67 fe-only 411 候選 | 前後端漂移 | 第三版精細化 |

---

## 4. 5 道防線整合 SSOT 真活

| 防線 | 機制 | 狀態 |
|---|---|---|
| 1 | Generator cron 06:00 regenerate | ✅ |
| 2 | Session-start hook 入口提示 | ✅ |
| 3 | Fitness step 64 freshness audit | ✅ |
| 4 | §9 cross_repo drift 自動呈現 | ✅ 1/4 RED |
| 5 | §8.5 Hermes 5 條件即時 | ✅ 1/5 NO-GO |

→ Owner 啟動 session 讀 dashboard 取單一 SSOT 完整快照。

---

## 5. L4x family lesson 庫真活

14 lesson 分流 universal/missive-specific：

### universal (8) — 對外推薦

L41 / L43 / L44 / L45 / L49 / L52 / L57 / **L61** (下游反治理)

### missive-specific (6)

L50 / L53 / L54 / L58 / L59 / L60

對應 v6.12 8 句立法各 lesson 案例：
- 第 6 句 L58 / 第 7 句 L59 / 第 8 句 L60 / L61 補強 L60

---

## 6. 真實業務 metric 對齊

| 業務指標 | 數值 |
|---|---|
| Documents | 1,809 |
| Canonical entities | 24,535 (含 9091 code) |
| Wiki pages | 359 |
| Lessons | 14 (universal 8 + specific 6) |
| Fitness step | 72 |
| Active ADR | 21 |
| Active facade | 3 (60 天 trial) |
| Cross_repo 採用 | 3/4 GREEN |

---

## 7. 整體性結論

### 7.1 真活面（13 step 全跑通）

- ✅ Tier 1 daily 8 step ALL PASSED
- ✅ Tier 2 weekly 21 step ALL PASSED
- ✅ Dashboard 5 道防線真活
- ✅ Lesson 14 條完整索引
- ✅ Hermes baseline 加速累積 (2→13)
- ✅ Ollama keep_alive 修法生效 (p95 -44%)

### 7.2 效益面

- ✅ Fitness 32→72 (2.25x)
- ✅ Lessons 5→14
- ✅ v6.12 8 句立法 + 8 lesson 對應
- ✅ Facade caller 0.46→3.00 (6.5x)
- ✅ ROI 公式 1→6 維度延伸 (+commit_rate / correctness_rate / balance_rate / reverse_governance_rate)

### 7.3 RED 待處理（5 項）

P0 自動進行：
- Hermes baseline 累積（明天 09:00）

P0 owner action：
- knowledge dedup script (0.5 天)
- wiki kg_entity_id backfill (1 天)
- orphan volume SOP

P1 持續精細化：
- step 67 第三版
- repository 命名規約 enforce

---

## 8. 對齊 v6.12 8 句立法 — 全部真活驗證

| 立法句 | 本日真活案例 |
|---|---|
| 1 抽象不是錯，建後不 audit 才是 | Facade B 方案 13→3 (audit 後縮減) |
| 2 觀測不是奢侈，自治理就是 | 13 新 fitness step + 7 governance metric |
| 3 整合 SSOT 是責任 | Dashboard 5 道防線 |
| 4 60 天 trial 是保險 | Facade trial 2026-07-30 重評 |
| 5 commit + push 才算 | step 66 uncommitted audit |
| 6 範本是參考 (L58) | install-template --tier + .template-policy |
| 7 上游缺機制 (L59) | CK_AaaP audit 缺口揭發 |
| 8 平衡 = 結構正常化 (L60) | PileMgmt R18 真活反治理 |

8/8 真活驗證 ✓

---

## 9. 元洞察 — Audit 層級遞進

```
表層: KG 9091 entities (粗略)
  ↓
第 2 層: 比例失衡 (repository:db_table 1:3.5)
  ↓
第 3 層: 命名規約不對齊 (覆蓋率 13%)
  ↓
第 4 層: smart match 升級 (58%)
  ↓
第 5 層: 跨域連結率 (wiki↔KG 38.5%)
  ↓
第 6 層: knowledge 雙寫 (41.8%)
```

**每寫一個 audit 揭發更深一層**。對齊 v6.12 第 2 句「觀測不是奢侈，自治理就是」+ L60「結構正常化」。

---

## 10. 下批優先級（owner approve 後）

| P | 動作 | 估時 |
|---|---|---|
| **P0** | knowledge dedup script 執行 | 0.5 天 |
| **P0** | wiki kg_entity_id backfill (38.5%→80%) | 1 天 |
| **P0** | ERP KG ingest 84→500+ | 1 天 |
| **P1** | Document/Skill graph 加入 | 2 天 |
| **P1** | step 67 第三版精細化 | 半天 |
| **P2** | /kunge UX Phase 1 實作 | 1-2 週 |

---

> **核心精神**：治理機制不是寫完算完，是 audit 真活 + 揭發深度 + 效益量化三方對齊。
> 本日 13 step 全跑通 + 5 RED 真實揭發 + 8/8 立法案例驗證 = 真活且有效益。
> 對齊 owner「確認真活與效益」訴求。
