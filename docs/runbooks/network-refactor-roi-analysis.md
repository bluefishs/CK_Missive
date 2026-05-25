# 4 層分網路重構 ROI 分析（DEFER 決策依據）

> **版本**：v1.0 / 2026-05-25
> **觸發**：對 `4-layer-network-refactor-plan.md` 提出實質效益質疑
> **結論**：**DEFER 到 v6.12**（觀測棧 L0 就緒後再做），改採折衷 2 層版本作為過渡

---

## 一、原規劃聲稱效益 vs 真實環境

| 規劃聲稱 | CK_Missive 當前環境（單機 Windows Docker）的實際狀況 |
|---|---|
| postgres 不對 frontend 暴露 | **效益小** — postgres 已有密碼 + listen 127.0.0.1。frontend 是 nginx static serve（無 RCE 風險），攻擊面有限 |
| 觀測棧 scrape 範圍精準 | **效益空中樓閣** — `ck_platform_obs_net` 在 CK_AaaP 端尚未存在；觀測棧 L0 仍在規劃 |
| 故障隔離 | **效益薄** — docker bridge driver 不做硬隔離，網路分層是邏輯非 firewall |
| ADR-0043 合規 | **純治理價值** — Audit GREEN 但 0 使用者體驗改進 |
| 跨 repo 範本價值 | **真實但機會成本** — 需 2+ repo 同步做才攤平；目前其他 4 RED repos 無積極需求 |

---

## 二、真實成本

| 項目 | 數字 |
|---|---|
| 工程時間 | 4-5h（owner 在場） |
| 公網 downtime | 60-120 秒（必須選離峰）|
| Metrics history reset | Grafana 短暫 0 / Prometheus rate 重算 |
| 維運複雜度 | 5 個 network 定義 + service 多接線 |
| 風險點 | R1-R6（DNS / race / metrics / external 不存在 / cloudflared / port mapping）|

---

## 三、同 4-5h 預算的替代任務 ROI

| 替代 | Effort | 實質效益 | ROI |
|---|---|---|---|
| A. 4 層分網路 | 4-5h | 0 UX 改進 + ADR GREEN | 1x（基準）|
| **B. PM2 廢除** | 3-4h | 解 L43 路由迷宮 + hot-patch 永遠生效 | **3x** ⭐ |
| **C. step 42 anti-pattern 修法**（lvrland+pile 5 處）| 30 min | L44 lesson 真正落地 + 跨 subdomain login 體驗修正 | **5x** ⭐⭐ |
| **D. owner SSO E2E**（L41 真活驗收）| 5 min | L41 6 天 dormant 事故正式關閉 | **10x** ⭐⭐⭐ |
| E. v7.0 baseline 推進 | 2-3h × 多 | ADR-0030 GO 條件達標 | 2x |
| F. cross-file-ssot-governance 擴散到其他 repo | 2h | L41-L45 防禦立基擴散 | 2x |

---

## 四、決策

### 建議：DEFER 到 v6.12（2026-06-17+）

**為什麼**：
1. **沒有事故驅動** — 不像 L41/L43/L44/L45 是事故驅動；4 層是 audit RED 驅動（治理債）
2. **觀測棧依賴未就緒** — `ck_platform_obs_net` external 不存在，做完無實質觀測流
3. **真實安全增益小** — postgres 密碼防護是 critical layer，網路分層是 defense-in-depth 第 N 層
4. **ROI 高的替代任務多** — PM2 廢除 / step 42 修法 / owner E2E 都是 3-10x ROI

### 何時應該做完整 4 層

- ✅ 觀測棧 L0（CK_AaaP）正式啟用 Prometheus scrape 跨 repo
- ✅ 至少 2 個 repo 也排程做（攤平範本投資）
- ✅ 進入 multi-host 部署（目前單機）
- ✅ 外部 audit / compliance 要求

---

## 五、折衷方案（v6.11 W3-W4 過渡）

達 50% 效益、20-40% 成本：

```yaml
networks:
  ck_missive_backend_net:  { name: ck_missive_backend_net, driver: bridge }
  ck_missive_data_net:     { name: ck_missive_data_net, driver: bridge }
  # 不建 frontend_net / worker_net (YAGNI)
  # ck_platform_obs_net: external (待觀測棧就緒，v6.12)

services:
  postgres:  [ck_missive_data_net]
  redis:     [ck_missive_data_net]
  backend:   [ck_missive_backend_net, ck_missive_data_net]
  frontend:  [ck_missive_backend_net]
  adminer:   [ck_missive_data_net]
```

- **Effort**：1.5-2h（vs 4-5h）
- **滿足**：step 37 命名 GREEN（`ck_<repo>_<layer>_net`）+ postgres/redis 隔離
- **跳過**：frontend_net / worker_net / obs_net（YAGNI）
- **未來保留**：v6.12 觀測棧就緒後再切 frontend/worker

---

## 六、修正後 v6.11 Sprint 1 路線

```
W1 W2 (2026-05-26~06-02)
  P0  owner SSO E2E 跨 subdomain 真活驗收              (5 min)   ⭐⭐⭐
  P0  step 42 anti-pattern 修法 lvrland+pile           (30 min)  ⭐⭐
  P1  PM2 廢除 (依 pm2-deprecation-sop.md)             (3-4h)    ⭐
  P2  Ghost volume 清理                                (30 min)
  P2  B 方案 PowerShell hook 補回                      (30 min)

W3 W4 (2026-06-03~06-16)
  P3  4 層分網路（折衷 2 層）                          (1.5-2h)
  P3  其他 RED repos 同步（範本）                       (2h)

v6.12 (2026-06-17+)
  P4  完整 4 層（若觀測棧 L0 就緒）                    (+2-3h delta)
```

---

## 七、本決策的「測試」

如果以下任一條件變了，本決策需重新評估：

1. 觀測棧 L0（CK_AaaP）排程 Prometheus scrape 跨 repo → 4 層 ROI 大幅上升
2. 公司 / 客戶 要求外部安全 audit → 4 層成為必要
3. lvrland 或 pile 排程 4 層重構 → 範本價值出現
4. 多機部署計畫成型 → defense-in-depth 必要性提升

---

> **核心精神**：**治理債不一定要立刻還，但要算清楚利息**。
> 4-5h 工時的機會成本比 GREEN audit 重要；ROI 8x 的替代任務優先。
