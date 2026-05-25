# 可模組化功能/服務盤點 — v6.10 P1

> **狀態**: accepted（v6.10 P1 收尾）
> **日期**: 2026-05-18
> **目的**: 盤點 CK_Missive 內可被打包成跨 repo 共用單元的 module，給「移轉部署 + 統一架構管理」具體 roadmap
> **配套**: ADR-0036 / CONTRACTS_LAYER_GUIDE / NAMING_CONVENTIONS / module_portability_audit

---

## 一、盤點方法

對每個候選 module 跑 `scripts/checks/module_portability_audit.py`：

| Score 區間 | Verdict | 解讀 |
|---|---|---|
| 1.000 | PORTABLE | 可直接打包，0 業務耦合 |
| 0.7–0.99 | PORTABLE_WITH_NOTES | 清 docstring 即可上 1.000 |
| 0.4–0.7 | NEEDS_RENAME | 含 high keyword，須改業務 vocabulary |
| 0.0–0.4 | NOT_PORTABLE | 含 critical 業務耦合，需大重構 |

---

## 二、Tier 1：可立即打包（5 個 score 1.000）

| Module | 行數 | 用途 | 建議 package name |
|---|---|---|---|
| `core/domain_whitelist.py` | 131 | 跨域白名單偵測 | `ck-auth` 內（已 packed） |
| `core/security_headers.py` | 92 | HSTS / CSP / X-Frame middleware | `ck-auth` 內（已 packed） |
| `core/cache.py` | 233 | Redis cache 基礎類 | **`ck-cache` v1.0**（新） |
| `core/event_bus.py` | 70 | Domain events 廣播 | **`ck-events` v1.0**（新） |
| `core/admin_push_metrics.py` | 94 | Admin push Prometheus counter | **`ck-observability` v1.0**（新組合） |

**合計 5 檔 / 620 行可立即模組化**。

---

## 三、Tier 2：清 docstring 即可上 1.000（2 個 0.7）

| Module | 行數 | 阻礙 keyword | Effort |
|---|---|---|---|
| `services/security/*.py` | 2 檔 | "vendors" 等 docstring example | 15 min（改 docstring） |
| `core/cache_manager.py` | 323 | 同上 | 15 min |

修法：與今日 contracts/ 從 0.000 → 1.000 同模式（改 docstring 業務範例為通用詞）。

---

## 四、Tier 3：含 high keyword 需重新封裝（0.4 區間）

| Module | 行數 | 阻礙 | 建議 |
|---|---|---|---|
| `services/audit/` (mixin) | 4 檔 (0.380) | docstring 範例含「公文」「派工」業務 | **改用 AuditPort + DefaultAuditAdapter**（contracts/ 已有） |
| `core/csrf.py` | 215 (0.400) | 註解內提 missive.cksurvey.tw 公網 | 已搬到 ck-auth (已修 critical) |
| `core/structured_logging.py` | 328 (0.400) | 業務 example log line | 改通用 → 列入 `ck-observability` |

---

## 五、Tier 4：含 critical 業務耦合 0.000（重構成本高）

| Module | 檔數 | 業務深度 | 建議 |
|---|---|---|---|
| `services/notification/` | 6 | 「派工」/「公文」「截止」散落 | **不單獨打包** — 走 NotificationFacade 抽象 |
| `services/backup/` | 7 | DB 名 ck_documents / 表名 official_documents | 業務專屬 — 不打包 |
| `services/integration/` | 11 | LINE/Telegram/Discord wrapper 含 ck-missive token 變數 | 走 MessagingPort/Adapter |
| `services/base/` | 9 | ImportBaseService 業務模板 | 不打包 |
| `services/common/` | 4 | 業務 helpers | 不打包 |
| `services/io_import/` | 4 | CSV/Excel 業務匯入 | 不打包 |
| `core/prometheus_middleware.py` | 203 | 業務 metric 名（v7_*  / dispatch_*） | **拆分**：通用 middleware → `ck-observability`，業務 metric 留 CK_Missive |

---

## 六、推薦 Package Roadmap（按 ROI 排序）

### Phase 0（已 done — v6.10 P1）

```
✅ ck-auth v1.0  (16 檔 / 3998 lines / portability 1.000)
✅ ck-contracts (內嵌 backend/app/services/contracts/, 24 檔)
```

### Phase 1（**下批最高 ROI** — 1 sprint 內可做）

```
🎯 ck-observability v1.0    （新組合 4 檔）
   - core/event_bus.py             ✓ 1.000
   - core/admin_push_metrics.py    ✓ 1.000
   - core/prometheus_middleware.py 拆通用部分
   - core/structured_logging.py    清通用部分
   
🎯 ck-cache v1.0            （新 2 檔）
   - core/cache.py                 ✓ 1.000
   - core/cache_manager.py         須清 docstring
```

### Phase 2（v6.11 後評估）

```
🟡 ck-paths v1.0       （從 contracts 抽出，已有 76 行 SSOT）
🟡 ck-fitness-helpers  （6 個 fitness step 含 yaml）
🟡 ck-events v1.0      （event_bus 已 1.000，但 consumer 少）
```

### Phase 3（v7.0+ 評估）

```
⚠️ ck-rls v1.0  - 與 ck-auth + contracts.RLSPort 整合（DB schema 抽象 + alias 展開）
⚠️ ck-audit v1.0 - 改 AuditableServiceMixin 為 DI 注入 + Port
```

### Not Recommended（業務深度耦合）

```
❌ notification / backup / integration / base / common / io_import
❌ document / contract / agency / vendor / erp / tender / calendar / wiki
   → 用 facade 跨 context 共用，不單獨打包
```

---

## 七、跨 repo 採用 Matrix（4 consumer × 5 package）

| Package | CK_AaaP | hermes-agent | CK_lvrland | CK_PileMgmt |
|---|---|---|---|---|
| **ck-auth** v1.0 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (83% dry-run) | ⭐⭐⭐⭐⭐ (91% dry-run) |
| **ck-observability**（規劃中） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **ck-cache** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **ck-paths** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **ck-contracts**（含 4 Port + 4 Adapter） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 八、Service 12 Bounded Contexts 模組化策略

| Context | Facade 已建 | 業務耦合度 | 跨 repo 採用方式 |
|---|---|---|---|
| document | DocumentFacade | 100% 業務 | 走 facade 不打包 |
| contract | ContractFacade | 100% 業務 | 走 facade 不打包 |
| agency | AgencyFacade | 100% 業務 | 走 facade 不打包 |
| vendor | VendorFacade | 100% 業務 | 走 facade 不打包 |
| audit | AuditFacade + AuditPort | 30% 業務 | **改用 ck-contracts.AuditPort** ✓ |
| notification | NotificationFacade | 80% 業務 | 走 facade 不打包 |
| erp | ERPFacade | 100% 業務 | 走 facade 不打包 |
| integration | IntegrationFacade + MessagingPort | 60% 業務 | **改用 ck-contracts.MessagingPort** ✓ |
| tender | (待寫) | 100% 業務 | 走 facade 不打包 |
| calendar | CalendarFacade | 60% 業務 | 部分走 facade |
| wiki | WikiFacade | 60% 業務 | 走 facade 不打包 |
| ai | AIFacade | 60% 業務 | 走 facade 不打包 |
| memory | MemoryFacade | 60% 業務 | 走 facade 不打包 |

**規則**：100% 業務 → 永不打包；30-60% 業務 → 走 facade；< 30% → 抽 package。

---

## 九、Frontend 模組化候選

| 元件 | 業務耦合 | 建議 |
|---|---|---|
| `components/auth/*` (LoginPanel + withAuth) | 0% | **ck-auth 已含** ✓ |
| `hooks/utility/useAuthGuard.ts` | 0% | ck-auth 已含 |
| `hooks/utility/useResponsive.ts` | 0% | 新 package `ck-react-utils` |
| `hooks/system/useStreamingChat.ts` | 30% | 半業務 — 走 facade |
| `hooks/taoyuan/useDispatchCacheInvalidator.ts` | 70% | 業務專屬 — 不打包但模式可學 |
| `api/client.ts` + `interceptors.ts` | 0% | 新 package `ck-api-client` v1.0 |

---

## 十、量化結論

| 指標 | 數值 |
|---|---|
| **已模組化（ck-auth + ck-contracts）** | 50 檔 / portability 1.000 |
| **Tier 1 可立即模組化**（待打包） | 5 檔 / 620 行（ck-observability + ck-cache） |
| **Tier 2 docstring 修即可** | 2 檔 / 326 行（15-30 min） |
| **Tier 3 走 Port/Facade** | 3 模組（audit/integration/csrf 已部分接通） |
| **業務專屬不打包** | 12 contexts（走 facade） |
| **預估可重用 code 總量** | **~6000 行**（auth + contracts + observability + cache + 規劃中） |

---

## 十一、下一步動作

### 本週可做（高 ROI）

1. **建 `shared-modules/ck-observability/`**（仿 ck-auth 結構）
   - 含 event_bus / admin_push_metrics / 部分 prometheus_middleware / 部分 structured_logging
   - install.sh + manifest.yml + README.md
   - 跑 step 30 audit + lvrland/pile dry-run

2. **修 Tier 2 docstring（security_scanner / cache_manager）**
   - 15 min 完成 → 升 1.000

3. **建 `shared-modules/ck-cache/`**
   - 含 cache.py + cache_manager.py (docstring 修後)
   - 對應 CachePort + DefaultCacheAdapter

### 月內可做

4. **跨 repo 試裝 ck-observability + ck-cache**（lvrland + pile dry-run）
5. **抽 frontend ck-api-client**（client.ts + interceptors.ts + errors.ts）

### v7.0 評估

6. **整合 ck-* packages 為單一 `ck-platform` meta-package**
7. **評估 internal PyPI 化條件**（前提：≥ 3 個 consumer 真採用）

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-18 | v1.0 | 初版（含 audit 結果 + 4 Tier 分類 + 跨 repo Matrix） |
