# ADR-0016: 多專案平台級子網域策略（cksurvey.tw）

> **狀態**: accepted
> **日期**: 2026-04-15
> **決策者**: 專案 Owner
> **關聯**: ADR-0014（Hermes 取代 OpenClaw）, ADR-0015（CF Tunnel 取代 NemoClaw）
> **前提條件**: **全免費**（Cloudflare Free + Universal SSL + Access Free 50 users）

## 背景

組織維護多個 CK 專案：

- `CK_Missive` — 公文管理
- `CK_lvrland_Webmap` — 土地查估 Webmap
- `CK_PileMgmt` — 基樁管理
- `CK_Tunnel` — 既有於 federation 枚舉

且全面導入 Hermes + Cloudflare Tunnel 後，需要統一入口策略。單專案雙域（`api/app`）不夠用。

## 決策

採 **平坦專案分域** 模式：每專案獨立 subdomain，平台級服務獨立 subdomain，路徑分 API/UI。

### 網域規劃

| Subdomain | 用途 | 後端 | 開放對象 | 階段 |
|---|---|---|---|---|
| `cksurvey.tw` | 平台 Landing | CF Pages 靜態 | 公開 | 選用 |
| `missive.cksurvey.tw` | 公文系統（UI + /api/*） | `localhost:8001` | SSO 團隊 / webhook IP | **Phase 1** |
| `lvrland.cksurvey.tw` | 土地查估 | `localhost:8002` | SSO 團隊 | Phase 2+ |
| `pile.cksurvey.tw` | 基樁管理 | `localhost:8003` | SSO 團隊 | Phase 2+ |
| `hermes.cksurvey.tw` | Hermes Agent gateway | `localhost:8900` | 公開 (token 保護) | Phase 1 |
| `kg.cksurvey.tw` | 聯邦知識圖譜 Hub | Missive `/api/ai/federation/*` | Token 保護 | 選用 |
| `status.cksurvey.tw` | 公開狀態頁 | CF Pages 靜態 | 公開 | 選用 |
| `docs.cksurvey.tw` | 公開文件 | CF Pages 靜態 | 公開 | 選用 |

**禁用**兩層子網域（`api.missive.cksurvey.tw`）避免 Advanced SSL 付費需求。

### 三專案資料與認證策略

| 面向 | 策略 |
|---|---|
| **DB** | **獨立 Postgres instance per project**（per-project schema 或容器） |
| **KG 聯邦** | `/api/ai/federation/contribute` push + `/api/ai/federation/search` pull；跨專案資料僅在 KG 層聯通 |
| **SSO** | **Cloudflare Access Free**（50 user quota），一次登入通三專案 |
| **Service Token** | 各專案發獨立 `MCP_SERVICE_TOKEN`（不共用） |
| **Hermes Skills** | `~/.hermes/skills/ck-{project}-bridge/` 每專案一 skill |

### Hermes 多租戶配置

```
~/.hermes/skills/
  ├── ck-missive-bridge/    # 指向 missive.cksurvey.tw
  ├── ck-lvrland-bridge/    # 指向 lvrland.cksurvey.tw
  └── ck-pile-bridge/       # 指向 pile.cksurvey.tw
```

每 skill 各抓自己的 `/api/ai/agent/tools` manifest，註冊時加專案前綴：
```
missive_document_search
lvrland_parcel_search
pile_inspection_query
```

## 後果

### 正面

- **零費用**：Free 方案全覆蓋
- **三專案清楚隔離**：DB / auth token / hostname 全獨立
- **SSO 一次登入通三專案**：CF Access Email OTP / Google Workspace
- **聯邦 KG 不需資料物理遷移**：各專案 push 實體到共用 KG Hub
- **Hermes 跨專案工具編排**：一句話可穿透三系統（如「列出公文關聯土地與基樁」）
- **未來專案擴充零重構**：新增 `xxx.cksurvey.tw` 只需 CF Tunnel 加 hostname

### 負面

- **CF Access 50 user 天花板**：超過要升 Pay-as-you-go 約 USD 3/user/月
- **跨專案 JOIN 效能受限**：KG 聯邦查詢有網路延遲（可接受；Missive 已跑 federation 架構）
- **3 個獨立 DB 備份**：`scripts/checks/shadow-baseline-report` 類工具需各自執行
- **Hermes skill 維護 3 組**：manifest drift 風險 → 需合約測試覆蓋每專案

## 替代方案

| 方案 | 排除原因 |
|---|---|
| **單 DB 多 schema** | 耦合高、備份連動風險、不易切 project |
| **`api.xxx.cksurvey.tw` 兩層** | 需付費 Advanced SSL，違反零費用前提 |
| **自建 Keycloak SSO** | 維運成本 > CF Access；Free 50 user 已夠 |
| **Hermes 單一跨專案 tool namespace** | Tool 名稱衝突時難除錯；tool prefix 作法更清楚 |

## 實施順序

| 日期 | 項目 | 狀態 |
|---|---|---|
| 2026-04-15 | ADR-0016 通過（本日） | ✅ |
| 2026-04-17 | CF Dashboard tunnel hostname 改為 `missive.cksurvey.tw` | ⏳ |
| 2026-04-18 | Missive smoke test on new hostname | ⏳ |
| 2026-04-20 | CF Access 啟用（Email OTP）`missive.cksurvey.tw` | ⏳ |
| 2026-04-25 | Telegram webhook 指向 `missive.cksurvey.tw/api/telegram/webhook` | ⏳ |
| 2026-05-05 | Hermes gateway 上線 `hermes.cksurvey.tw`（localhost:8900） | ⏳ |
| 2026-06-01~ | `lvrland.cksurvey.tw` / `pile.cksurvey.tw` 接入 | 未定 |

## 驗收標準

- [ ] `https://missive.cksurvey.tw/api/health` 公網可達
- [ ] CF Access Email OTP 生效於 `missive.cksurvey.tw`
- [ ] Telegram/Discord webhook 經 `missive.cksurvey.tw` 正常收發
- [ ] Hermes gateway 登記三 skill 分別指向三專案
- [ ] 聯邦 KG search/contribute 跨專案驗證通過
- [ ] 無任何付費項目出現在 Cloudflare 帳單
