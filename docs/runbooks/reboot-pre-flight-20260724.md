# 重啟 Pre-Flight Checklist — 2026-07-24

> 本 session 主軸：**跨 repo 前端共享套件模組化收斂**（owner「請統一，不然一直不同問題衍生修正導致分歧」）。
> 前一份：`reboot-pre-flight-20260720.md`

---

## ⭐ 重啟後最高優先（focused session）— 後端 auth Tier2 收斂

> **這是唯一剩餘的模組化收斂項，也是最深最高風險，重啟後另開 focused session 處理。**

| 項 | 風險 | 說明 |
|---|---|---|
| **後端 sso_bridge** | **高** | async(Missive)/sync(lvrland/pile) 分裂 + User model 耦合（策略文件缺口 D Tier2）；**4 backend rebuild 含主產品 Missive**；本 session DT outage 已證後端 auth 收斂風險真實嚴重 |
| 後端 csrf | 中 | lvrland↔pile 近乎相同（1 行 redis import 差），需 backend rebuild + redis client 注入 |
| DT bearer | 中高 | TokenManager bearer/XOR 獨立 paradigm，需 bearer adapter（DT 最後） |
| env.ts | 中 | lvrland/pile 散落非單檔，需先各自集中化 |

**執行紀律（feedback_rigor #1 + DT outage 教訓）**：逐一 repo（先 sync 非主產品 → Missive 最後）、每 repo **isolated 測 image（docker run --rm）+ 登入實測（含 SSO/MFA/LINE 全流程）+ revert-on-fail**。機制（ck_auth vendored wheel）就緒，設計見 `docs/architecture/MODULARIZATION_CROSS_PROJECT_STRATEGY.md` Phase 1（async/sync adapter）。

---

## ✅ 本 session 已完成（前端共享收斂全數 live 驗證）

**5 前端共享套件**（canonical＝`shared-modules/<pkg>`，vendored-in-context 進 lvrland/pile、Missive direct file:）：
- `@ck-shared/tokens`（設計 token）
- `@ck-shared/sso`（bridge + createAuthStore 2-state + createSessionStore tri-state）
- `@ck-shared/api-errors`（apiErrorHandler + errorBus）
- `@ck-shared/query-config`（createQueryClient）
- `@ck-shared/ws`（createUseWebSocket factory + Context primitives）

**順修的 latent bug**：pile authStore I2 / apiErrorHandler type-guard / queryClient cacheTime v4→v5 / theme 未 build 主幹。
**後端**：ck_auth(JWT verify) 4 repo 單一源 + sso_bridge helper + TTL 8h。
**機制**：`shared-modules/sync-vendored.sh`（通用 sync + `--check` drift）+ Missive fitness **step 71** drift enforcement（非 advisory）。
**變更傳播語意** FAQ：策略文件 §7.1（改 canonical 全同步、手改 vendored 被 step 71 抓、A 客製用 config 注入）。

---

## 重啟前狀態（pre-flight 驗證）
- **git**：5 repo（Missive/lvrland/pile/DT/shared-modules）**未推=0**（全同步 origin）；未提交僅 auto 產物（.claude/generated、wiki compile、governance dashboard、.agents/.codex/AGENTS.md）不影響。
- **drift**：`sync-vendored.sh --check` = **GREEN**（4 套件全同步）。
- **五系統公網**：全 **200**（missive/lvrland/pilemgmt/digitaltwin/www）。
- **驗證證據**：3 消費 repo 前端 `tsc --noEmit` EXIT=0；後端 `py_compile` 48/48；pile CI-LOCAL 全通過。
- **Docker**：容器 `unless-stopped`（重啟 Docker 自動拉回）；⚠️ Missive DB volume 須 `ck_missive_postgres_dev_data`（L43，勿誤掛空殼 `ck_missive_postgres_data`）。
- **NVIDIA hook 風險**（L, 6/16）：本機重啟後 NVIDIA Container Toolkit prestart hook 可能崩潰使 ck-ollama GPU 容器無法啟動（healthcheck 仍綠假象）→ 解＝`wsl --shutdown` 重啟 Docker 引擎，勿用 `docker restart`。

---

## 重啟後驗收 SOP（5 步）
1. **Docker 自動拉回**：`docker ps` 確認容器全 Up、0 unhealthy（若 ck-ollama Exited → `wsl --shutdown` + 重啟 Docker 引擎）。
2. **五系統公網 200**：`curl` missive/api/health + lvrland/pilemgmt/digitaltwin/www。
3. **drift GREEN**：`bash shared-modules/sync-vendored.sh --check`。
4. **瀏覽器 SSO 實測**：從 www.cksurvey.tw 登入 → 轉各系統（Missive/lvrland/pilemgmt/DT）確認登入態、dashboard、console 乾淨。
5. **接續 focused session**：後端 auth Tier2 收斂（見本文最上「最高優先」）。

---

## 相關文件
- 模組化路線圖：`docs/architecture/MODULARIZATION_NEXT_CANDIDATES_20260722.md`（§2.5-2.10 全收斂記錄 + 剩餘評估）
- 模組化策略：`docs/architecture/MODULARIZATION_CROSS_PROJECT_STRATEGY.md`（§6.1 vendored-in-context 標準、§7.1 傳播語意 FAQ、Phase 1 async/sync adapter）
- 共享套件 sync：`shared-modules/sync-vendored.sh`（+ `--check` drift gate）
