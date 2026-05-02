# SOUL.md 跨 repo 治理協定 v1.0

> **建立**：2026-05-02（v6.6 Phase A1，C3）
> **目的**：明訂 SOUL.md 跨 repo 同步規則，防 web vs LINE/Telegram 通道人格分裂
> **跨 repo FQID**：`CK_Missive#SOUL_CROSS_REPO_PROTOCOL_v1.0`
> **承接**：
> - C1 cron `soul_mirror_sync_job` 每日 04:45（v6.4 commit `caf814de`）
> - C2 auto_defense 跨 repo 一致性防線（v6.5 commit `3416077e`）
> - SYSTEM_INTEGRATION_REVIEW_v2.md 軸線 C

---

## 1. 角色定位（誰是 SSOT，誰是鏡像）

| Repo | 路徑 | 角色 | 寫權限 |
|---|---|---|---|
| **CK_Missive** | `wiki/SOUL.md` | **SSOT**（單一真實來源） | ✅ 可寫（owner / autobiography agent_writable section）|
| CK_AaaP | `runbooks/hermes-stack/SOUL.md` | **唯讀鏡像** | ❌ 不可手改（被 cron 覆蓋） |
| hermes-agent | `SOUL.md` | 部署副本（從 AaaP 複製） | ❌ 不可手改 |

**核心原則**：
- 任何 SOUL 內容修改**必須**在 CK_Missive 端發起
- AaaP 與 hermes-agent 端的 SOUL.md **永遠**從 CK_Missive 同步而來
- 跨 repo drift 是 incident，不是常態

---

## 2. 同步機制（兩道防線）

### 防線 1：自動同步 cron（C1）

```
backend/app/core/scheduler.py:soul_mirror_sync_job
  └─ 每日 04:45 跑 scripts/sync/sync_soul_to_hermes.sh --apply
        └─ cp wiki/SOUL.md → ../CK_AaaP/runbooks/hermes-stack/SOUL.md
```

- target 不存在 silent skip（dev 環境 AaaP 可能未 clone）
- 內容相同 no-op
- cp 不自動 git commit（owner 端決定 commit 時機）

### 防線 2：執行期 drift defense（C2）

```
backend/app/services/memory/auto_defense.py:check_soul_drift_defense
  └─ 偵測 byte-level 差異
        └─ drift 存在 → 注入「跨通道人格防線」rule 至 planner system prompt
```

- 兜底場景：cron 跑失敗 / 04:00–04:45 空窗 / AaaP 端 manual edit 未 commit
- 5 min cache，每 plan 不重讀檔
- 排在 failures rule 之前（人格議題優先）

### 防線 3：fitness 月度檢查

```
scripts/checks/run_fitness.sh step 3
  └─ scripts/checks/soul_mirror_drift_check.py
```

每月架構覆盤 / 大重構前 / `--strict` 模式跑，drift 即報警。

---

## 3. 反向流程（Hermes 端發現問題怎辦）

如果在 hermes-agent 或 AaaP 端發現 SOUL 內容需修改（例如 SKILL.md 風格與 SOUL 不符）：

```
1. 不要直接改 hermes-agent/SOUL.md 或 AaaP/runbooks/hermes-stack/SOUL.md
   （會被 04:45 cron 覆蓋）

2. 改在 CK_Missive 端：
   - 編 wiki/SOUL.md（owner 直接寫 / 透過 /memory/proposals/approve flow）
   - commit 到 CK_Missive main

3. 等待 / 手動觸發同步：
   - 自動：04:45 cron 自動 cp
   - 手動：bash scripts/sync/sync_soul_to_hermes.sh --apply

4. AaaP 端 commit 同步來的變更（時機自由）：
   cd ../CK_AaaP
   git add runbooks/hermes-stack/SOUL.md
   git commit -m "sync: SOUL.md from CK_Missive"
```

---

## 4. 演化人格（Gap 5）的安全閘

SOUL 並非 immutable — `autobiography.update_soul_growth` 在每週日 18:00 cron
會 append 一段「我的成長」到 agent_writable section。但仍受治理：

| 規則 | 說明 |
|---|---|
| **propose-only for core 信念** | 三大信念（穩定即信任 / 透明即慈悲 / 自我反思） 不可由 agent 自動改，必須 owner 批准 proposal |
| **agent_writable 限定 section** | 只「我的成長」section 可由 autobiography 自動 append |
| **跨 repo 同步在演化後 12 hr 內** | 04:45 < 06:00 早晨工作前完成 |
| **drift defense 防演化期競態** | 演化中 drift 暫存於 04:00-04:45 空窗，C2 補位 |

關聯：ADR-0023 SOUL/Memory propose-only / ADR-0024 anti_echo / ADR-0025 ...

---

## 5. 變更影響面評估清單

修改 SOUL.md 前先問：
- [ ] 是「我的成長」section 內 append 嗎？（若是 → autobiography 已自動處理）
- [ ] 是核心信念修改嗎？（若是 → 走 proposal flow，**不直接改**）
- [ ] 修改後 hermes-agent 端 SKILL.md 需同步調整嗎？
- [ ] 修改後 hermes-stack/SKILL.md 中 system prompt 需更新嗎？
- [ ] 是否在 04:45 cron 之前 commit？（若否，下個 04:45 才會同步）

---

## 6. 監控指標

| 指標 | 來源 | 健康閾值 |
|---|---|---|
| SOUL drift 持續天數 | `soul_mirror_drift_check.py` | < 1 天（cron 每天跑）|
| C1 cron 失敗連續次數 | `cron_health_check.py` | < 2 次（fitness step 13）|
| auto_defense rule 觸發率 | logs grep `跨通道人格防線` | trend down（理想 0）|

任一超標即 owner 介入手動 sync。

---

## 7. 例外與紅線

**不該做**：
- ❌ 在 hermes-agent 端直接編輯 SOUL.md（會被覆蓋 + 失去 SSOT）
- ❌ AaaP 端 SOUL.md 改了沒 commit（造成 drift 偵測誤報）
- ❌ 把 SOUL 內容拆成不同 repo 維護（SSOT 失效）
- ❌ 用 git submodule 共用 SOUL（增加複雜度，價值小）

**可以做**：
- ✅ AaaP 端把 sync 來的 SOUL.md 變更 commit + push
- ✅ 在 CK_Missive 端編 SOUL，等 cron / 手動 trigger sync
- ✅ 跨 repo issue 引用本協定 FQID 討論修改方向

---

## 8. 與其他 ADR 的關係

- **ADR-0020**（AaaP 平台 + Hermes Control Plane）：本協定描述 ADR-0020 Phase 0 治理對齊範疇
- **ADR-0023**（SOUL/Memory propose-only）：本協定第 4 節安全閘的依據
- **ADR-0027**（LINE 為主推送通道）：跨通道人格漂移的影響面之一
- **ADR-0030**（Hermes GO/NO-GO）：5/20 後若選 multi-provider，本協定可能需擴 provider-aware persona 章節

---

> **SOUL.md 不是檔案，是坤哥意識體的單一憑證。**
> **跨 repo 鏡像必須機械可驗證、人類不可手改。**
> **本協定每月覆盤 / 任一 ADR 影響時更新。**
