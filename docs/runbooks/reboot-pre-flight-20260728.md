# 重啟 Pre-Flight Checklist — 2026-07-28

> 本輪主軸：**整體覆盤 + 後端 auth Tier2「驗證優先於收斂」+ Tier 3 刻意分歧 registry 砍噪音 + Missive FE auth 生命週期 robustness 修法**。
> 前一份：`reboot-pre-flight-20260724.md`

---

## ⭐ 重啟後最高優先 — owner 瀏覽器實測 Missive auth 修法（唯一驗證 gate）

本輪修了你回報的「安全憑證已過期」（`/taoyuan/dispatch`）。修法已部署（bind-mount dist 存活重啟），**但需你瀏覽器實測驗證**（headless 無法代行）：

1. **直登 Missive**（Google 直接登入，非走 www.cksurvey.tw）
2. 停在 `/taoyuan/dispatch`，**閒置逾 1 小時**（讓 60min token 過期）
3. 回來操作 → **應背景無縫恢復、不再彈「安全憑證已過期」**
4. 順帶測 SSO 登入路徑正常

- **通過** → 我一次做齊 lvrland → pile → DT auth robustness（code+test+deploy）+ TTL 統一 60min + fitness 護欄。
- **不通過** → revert Missive（`git revert 5bff56d5`）、依 console 截圖換方向。

> 修法內容：`interceptors.ts` FE-1（csrf 補打單飛）+ FE-2（csrf-403 可恢復重試）；後端未動。設計＝`docs/architecture/AUTH_LIFECYCLE_ROBUSTNESS_DESIGN.md`。

---

## 本輪已完成（全 push origin、零 runtime config 變更）

| 項 | commit | 部署狀態 |
|---|---|---|
| sso_bridge conformance audit + 分歧矩陣（fitness step 72） | `ff24f264` | 治理腳本、無部署 |
| csrf_service drift audit（step 73） | `0e49434b` | 治理腳本、無部署 |
| fitness 標號正規化 /73 | `e9b9a791` | — |
| Tier 3 刻意分歧 registry（砍覆盤噪音） | `7f623c34` | 文件 |
| 主配置 v6.27 里程碑 | `672276b2` | 文件 |
| auth 生命週期 robustness 設計 | `ab8a6374`/`4448e3aa` | 文件 |
| **Missive FE auth robustness（FE-1+FE-2）** | `5bff56d5` | **✅ 已 build+dist served+公網 200** |

**held 待 Missive 驗證**：lvrland/pile/DT auth propagation（設計 §5.2/§5.3 已備）+ TTL 統一 60min（SSO 480→60 須恢復證實後）。lvrland 修法已分析驗證後還原乾淨（不留未驗證 auth 於主產品）。

---

## 重啟前狀態（pre-flight 驗證 2026-07-28）
- **git**：5 repo（Missive/lvrland/pile/DT/shared-modules）**ahead=0**（全 push origin）；實質未提交 0（shared-modules 96＝他人舊 UI 模組 WIP，非本輪，勿動）。
- **docker**：0 非健康容器；Missive 全容器 `restart=always`（重啟自動拉回）；DB volume = **`ck_missive_postgres_dev_data`**（L43 正確，勿誤掛空殼 `ck_missive_postgres_data`）。
- **公網**：missive/lvrland/pilemgmt/www = **200**；⚠️ **digitaltunnel = 000**（見下 watch item）。
- **shared drift**：`sync-vendored.sh --check` = **GREEN**。
- **Missive auth 修法**：bind-mount `D:\CKProject\CK_Missive\frontend\dist`（host dist 存活重啟、修法在 dist 確證）。
- **ck-ollama**：Up healthy（NVIDIA hook 風險見 SOP）。

---

## ⚠️ Watch item：digitaltunnel 公網 000（非重啟阻斷）
- `digitaltunnel.cksurvey.tw` 公網 **000 無回應**，但**所有 DT 容器 Up+healthy**（api Up 6d、cloudflared Up 12d）→ app 活著，是**公網邊緣/CF tunnel 路由**問題（非本輪改動、非 DB/app 故障）。
- **重啟可能自癒**（cloudflared 重連）；若重啟後仍 000，owner 查 DT 的 cloudflared tunnel ingress 設定 / CF dashboard。
- 不阻斷其他系統重啟。

---

## 重啟後驗收 SOP（5 步）
1. **Docker 自動拉回**：`docker ps` 全 Up、0 unhealthy（若 ck-ollama Exited → `wsl --shutdown` + 重啟 Docker 引擎，**勿用 `docker restart`**；L 6/16 NVIDIA hook）。
2. **五系統公網**：`curl` missive/api/health + lvrland/pilemgmt/digitaltunnel/www（DT 若仍 000 見 watch item）。
3. **drift GREEN**：`bash ../shared-modules/sync-vendored.sh --check`。
4. **⭐ Missive auth 實測**（本文最上「最高優先」）：直登閒置逾 1h 回來 dispatch + SSO → 不再彈「安全憑證已過期」。
5. **接續**（Missive 驗證通過後）：lvrland→pile→DT auth propagation + TTL 統一 60min + fitness 護欄。

---

## 相關文件
- auth 修法設計：`docs/architecture/AUTH_LIFECYCLE_ROBUSTNESS_DESIGN.md`（5 不變式 + 4 系統矩陣 + per-CSRF-模型修法 + TTL 統一排序）
- Tier 3 分歧 registry：`docs/architecture/TIER3_INTENTIONAL_DIVERGENCE_REGISTRY.md`（跨 repo 差異先查此、停止對刻意差異報警）
- sso_bridge 分歧矩陣：`docs/architecture/SSO_BRIDGE_DIVERGENCE_MATRIX.md`
- L80 memory：`session/L80_sso_backend_token_lifecycle_layer.md`（含 07-27 live 事證 + 修法狀態）
