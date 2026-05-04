# ADR-0020 Hermes 角色終局決策提案 v3 (5/20 會議用)

> **Status**: PROPOSAL（待 5/20 會議決議）
> **建立**：2026-05-04（v3.0 覆盤洞察 13 派生）
> **承接**：
> - ADR-0020 原案（CK_AaaP platform）
> - ADR-0030（Hermes GO/NO-GO）
> - SYSTEM_INTEGRATION_REVIEW_v3.md 洞察 13
> **決議者**：5/20 owner 會議

---

## 0. 一頁摘要

`v6.6 phase c (commit 713b30a3)` 用「Hermes skill 加 3 read-only tools」**暫時繞**
ADR-0020 阻塞，但讓 Hermes 變「半厚 client」，違反 v2.0 洞察 8「Hermes = 跨通道介面、不該有獨立記憶層」。

5/20 須三選一定案，不再 drift：
- **方案 a**：等 ADR-0020 Phase 1 完成（被動）
- **方案 b**：read-only 3 tools 標臨時繞道（明確 sunset）
- **方案 c**：放棄 ADR-0020，Hermes 升正式 toolset gateway（戰略反轉）

**作者推薦：方案 b**（短期穩定 + 5/20 會議重評 ADR-0020 完成期）。

---

## 1. 決策背景（5/20 必看）

### 1.1 ADR-0020 原案

CK_AaaP 升級為「實質平臺基礎」(Platform-as-a-Platform)：
- Phase 1: Hermes 擴 4 bridge skills（query / memory / evolution / graph）
- Phase 2: Showcase 治理 API 遷入 AaaP
- Phase 3: DigitalTunnel 觀測棧遷入

**現狀**：Phase 1 阻塞 — CK_AaaP 端排程未明，無 owner、無 deadline。

### 1.2 v6.6 phase c 繞道（commit `713b30a3`）

為解 v3.0 洞察 7「Hermes 與 evolution loop 完全斷鏈」，本人加了
ck-missive-bridge skill 3 個 read-only tools（無需 ADR-0020 Phase 1）：
- `get_recent_diary` — 讀近 7 天 diary
- `get_evolution_journal` — 讀 agent_critic 紀錄
- `get_proposal_status` — 列 pending crystal proposal

**但這違反 v2.0 設計原則**：Hermes 不該有業務 endpoint 知識，應該保持 thin gateway。

### 1.3 v3.0 洞察 13 暴露的副作用

- Hermes 現變「半厚 client」— 知道 Missive evolution 路徑
- 每加新 skill 都要在 hermes-agent + Missive 兩處改
- ADR-0020 Phase 1 永遠 push 不動（短期繞道讓 owner 沒急迫感）

---

## 2. 三方案對比

| 方案 | 短期 | 長期 | 風險 | 工作量 |
|---|---|---|---|---|
| **a 等** | hermes evolution 仍斷 | ADR-0020 完成後通 | Phase 1 可能再延 6+ 個月 | 0（被動）|
| **b 文件化臨時** | 維持 v6.6 read-only 3 tools，標 sunset 條件 | 觸發 ADR-0020 Phase 1 後撤 | 低（明確 contract）| 1 天（寫 sunset 文件）|
| **c 戰略反轉** | Hermes 升正式 toolset gateway | 放棄 ADR-0020 | 高（推翻 4/15 決策）| 1-2 月（重設計）|

---

## 3. 推薦：方案 b + 5/20 會議重評 ADR-0020

### 3.1 短期決策（5/20 即定）

1. **明定 v6.6 phase c sunset 條件**：
   - `ck-missive-bridge` 3 read-only tools 標 `experimental: true`
   - 註明「臨時繞道，待 ADR-0020 Phase 1 完成後撤」
   - 加 `expected_sunset_date: 2026-08-31`（v6.6 後 4 個月，給 ADR-0020 推進緩衝）

2. **8/31 前若 ADR-0020 仍未動工**：自動觸發方案 c 評估會議

### 3.2 5/20 會議須回答（不只此案）

- ADR-0020 Phase 1 owner 是誰？（目前空缺）
- CK_AaaP repo 4/15 後 commit 數？（驗證活躍度）
- 是否願意接受方案 c 為「替代方案」（解除心理負擔）？

---

## 4. dogfooding 數據（若有）

為支援決策，以下指標可幫忙：

| 指標 | 取數來源 | 預期門檻 |
|---|---|---|
| Hermes 跨通道 baseline 累積數 | `synthetic-baseline-inject.py` 30 天 | ≥ 50（ADR-0030 GO #1）|
| read-only 3 tools 月使用次數 | hermes-agent log | ≥ 100（驗證有需求）|
| ADR-0020 Phase 1 ETA | CK_AaaP project board | 明確 deadline |
| Hermes vs Missive 重複 endpoint 數 | 程式碼 audit | 0（驗證 thin gateway）|

5/20 會議前 owner 應跑：
```bash
node scripts/checks/shadow-baseline-report.cjs
bash scripts/checks/run_fitness.sh
python scripts/checks/v7_metrics_report.py
```

---

## 5. 對應 v3.0 review

本提案直接回應：
- 洞察 13「A2 受 ADR-0020 阻塞的繞道有副作用」
- 8 接觸面 ❼「Hermes ↔ evolution」🟡 → 5/20 後定案 → 🟢 / 🔴

不解此案，v6.7 後每次 commit 都會增加 Hermes 半厚 debt。

---

## 6. 待 5/20 會議補充

- [ ] CK_AaaP 4/15 後 commit 統計
- [ ] Phase 1 預估工時（若認真做）
- [ ] 方案 c 反推估（若做反轉，hermes toolset gateway 工作量）

---

> **作者立場**：方案 b 是工程務實。但方案 c 戰略大膽，5/20 會議若 owner 願意承擔
> 推翻 4/15 決策的成本，方案 c 反而能釋放 v6.7+ 整合速度（Hermes 直接是
> Missive 的 dispatcher，不必繞 ck-missive-bridge skill）。
