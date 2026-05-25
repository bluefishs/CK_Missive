# 跨檔 SSOT 治理規範（Cross-File Single Source of Truth Governance）

> **強制等級**：高 — L41/L43/L44/L45 同族事故反覆觸發後立法
> **適用**：所有跨檔資源宣告（env vars / secrets / volumes / ports / endpoints / session keys / network names / image tags）
> **建立日期**：2026-05-25
> **觸發事件**：L43 family 4 連發（5/15~5/22）

---

## 為何需要這份規範

過去 7 天連續發生 4 起「跨檔資源不一致」事故：

| 事故 | 失效層 | Dormant | 影響 |
|---|---|---|---|
| **L41** JWT secret 跨 repo drift | ck-sso-py vs missive backend secret 不同 | 6 天 | SSO 全 chain silent 401 |
| **L43** docker volume name 雙軌 | `ck_missive_postgres_data` vs `ck_missive_postgres_dev_data` | 10 小時 | 業務 API 全 500，dormant 直到 owner login |
| **L44** SSO frontend session lock | sessionStorage hard-coded vs cookie storage 不同步 | < 1 天 | 跨 subdomain 認證失敗 |
| **L45** compose healthcheck override Dockerfile | compose `:80` vs Dockerfile `:3000` | 18 分鐘 | frontend container unhealthy FailingStreak=36 |

**共通模式**：
1. 同一資源在多個檔分別宣告
2. 沒 audit script 強制一致性
3. 修一處沒同步另一處
4. silent fail（部分功能正常 → 不觸發 alert）

**共通防禦**：
1. **single source** — 把資源宣告集中在一個檔（SSOT 檔），其他檔 reference 而非 copy
2. **enforce 一致** — fitness audit script 跨檔對比，drift 即 RED
3. **dual-validation** — runtime healthcheck 驗證業務量 / 連線真活，不只看 process up

---

## 規則 1：每個跨檔資源必須指定 SSOT

決定 SSOT 的優先順序（高到低）：

| 資源類型 | 推薦 SSOT 位置 | 範例 |
|---|---|---|
| Secrets | `.env` (gitignored) + `secrets/` Docker Secrets | DB password / JWT key |
| Env vars | `.env.example` (committed) | `BACKEND_PORT=8001` |
| Docker volumes | `docker-compose.production.yml` `name:` field | `name: ck_missive_postgres_dev_data` |
| Container ports | `Dockerfile EXPOSE` + nginx.conf listen | `:3000`（不在 :80）|
| Healthcheck | `Dockerfile HEALTHCHECK`（image 自帶）| `wget http://127.0.0.1:3000/nginx-health` |
| Endpoint URLs | `frontend/src/api/endpoints/*.ts` 常數 | `AUTH_ENDPOINTS.LOGIN` |
| Network names | `docker-compose.production.yml` `networks:` | `ck_missive_backend_net` |
| Image tags | `docker-compose.production.yml` `image:` | `cloudflare/cloudflared:2026.5.0`（pin 版本，不用 `latest`）|

**禁止**：
- 同一 secret 寫在多個 .env / config 檔
- 同一 volume name 在 production / dev compose 不一致
- compose `healthcheck:` override Dockerfile HEALTHCHECK（除非有環境特異性且註解理由）
- 用 `latest` tag 跨 repo 共用 image（會 silent 升版）

---

## 規則 2：跨檔資源變更必須有 audit enforce

每個跨檔資源類型必須有對應的 fitness audit script，月跑驗證 drift = 0：

| 資源 | Audit Script | Fitness Step |
|---|---|---|
| Docker volumes | `docker_compose_volume_consistency.py` | step 38 |
| Docker networks | `network_audit.py` | step 37 |
| Compose healthcheck vs Dockerfile | `compose_dockerfile_healthcheck_ssot.py` | step 40 |
| Manifest drift（shared-modules）| `manifest_drift_audit.py` | step 33 |
| Toolkit sync drift | `toolkit_sync_audit.py` | step 34 |
| Naming convention | `naming_convention_audit.py` | step 31 |
| Module portability | `module_portability_audit.py` | step 30 |
| Cross-repo secret 待補 | `cross_repo_secret_audit.py`（L41 配套）| step 41+（v6.11）|
| Cross-domain auth state 待補 | `cross_repo_auth_state_audit.py`（L44 配套）| step 42+（v6.11）|

**強制**：新增任一跨檔資源類型，**必須**同時新增對應的 audit script + 接進 `run_fitness.sh`。

---

## 規則 3：Runtime healthcheck 必須驗證業務量

不只 process up / connection ok，必須驗證業務真活。

**反例**（L43 揭發）：
```
postgres healthcheck: pg_isready -U postgres
→ 空殼 DB（17 tables / 0 docs）也回 200
→ silent 不告警
```

**正解**（L43 修法 commit `097cdf68`）：
```python
# backend/main.py /health endpoint
@app.get("/health")
async def health():
    docs = await db.scalar("SELECT COUNT(*) FROM documents")
    kg = await db.scalar("SELECT COUNT(*) FROM canonical_entities")
    biz_ok = docs >= 100 and kg >= 1000
    if not biz_ok:
        raise HTTPException(503, "business_data_not_present")
    return {"business_data": {"ok": True, "documents": docs, "canonical_entities": kg}}
```

→ cloudflared healthcheck fail → traffic 不打進空殼 instance

**強制**：所有面向公網的服務 `/health` endpoint 必須包含**業務量檢查**（row count threshold）。

---

## 規則 4：dual-write 場景必須 atomic 或 dual-validation

當業務邏輯需要寫兩處（e.g. DB + Redis cache），必須其一：

- **Atomic transaction** — 用 `BEGIN; ... COMMIT;` 包起兩個寫入
- **Dual validation** — 寫完讀回兩處比對

**反例**（L29 揭發）：
```python
# 寫 redis domain_scores
await redis.set("domain:score", new_score)
# 寫 DB（silent fail，except 吞掉）
try:
    await db.update_score(new_score)
except Exception:
    pass  # ← silent
```

→ redis 有新值但 DB 沒，下次重啟丟資料

**正解**：
```python
async with db.transaction():
    await db.update_score(new_score)
    await redis.set("domain:score", new_score)
# 若兩處任一失敗 → 整體 rollback
```

---

## 規則 5：版本化 + ADR 必走三件套

任何「跨 repo 共用」資源必須走 **ADR + Registry + Audit Script** 三件套：

- **ADR** — `docs/adr/00XX-<topic>.md` 宣告決策
- **Registry** — `CK_AaaP/runbooks/*-registry.md` 跨 repo dashboard
- **Audit Script** — `scripts/checks/<topic>_audit.py` enforce

已有範例：
- ADR-0043（cross-repo docker network standard）+ `docker-network-registry.md` + `network_audit.py`
- ADR-0044（single SSOT for docker volumes）+ volume consistency audit

**強制**：跨 repo standard 不走三件套 = 必然失血（L42 隱式 lesson）。

---

## 修法 SOP（事故發生後）

1. **判定 family** — 是否為 L41/L43/L44/L45 同型？ 看「兩個檔分別寫，沒 audit enforce 一致」
2. **第一手修法** — 對齊兩處宣告
3. **第二手修法** — 寫 audit script + 接進 fitness
4. **第三手修法** — 寫 ADR（若跨 repo）
5. **第四手修法** — 寫 lesson 入 LESSONS_REGISTRY + memory

---

## 與既有規範的關係

| 規範 | 強調點 | 與本規範關係 |
|---|---|---|
| `adr-anti-half-wired-sop.md` | ADR 級半接通防範 | **互補** — 本規範強調「跨檔資源 SSOT」，那規範強調「ADR 上線完整接通」 |
| `MANDATORY_CHECKLIST.md` | 開發前路徑/型別檢查 | **承接** — 本規範把「跨檔資源一致」也納入 |
| ADR-0028 錯誤合約 | silent failure 政策 | **延伸** — 跨檔 SSOT 失效常觸發 silent dormant |
| ADR-0043 跨 repo network | network 標準化 | **配套** — 本規範把 network 列為一個跨檔資源類型 |
| ADR-0044 single SSOT volumes | volume SSOT | **配套** — 同上 |

---

## L41-L45 family 修法資產索引

| Lesson | 修法 commit | Audit | ADR |
|---|---|---|---|
| L41 jwt secret drift | `bb1ca4ec` ck-sso-js v2.0 | 待補 cross_repo_secret_audit | 配套 ADR-0008 W3/W4 |
| L43 volume mount drift | `097cdf68` `ad4451b8` | step 38 docker_compose_volume_consistency | ADR-0044 |
| L44 sso session lock | ck-sso-js v2.0 移除 lock | 待補 cross_repo_auth_state_audit | 配套 ADR-0046 |
| L45 healthcheck drift | `505ee9d2` `5cf400b5` | step 40 compose_dockerfile_healthcheck_ssot | （無，單 repo）|

---

## 自查清單

在新增/修改跨檔資源時：

- [ ] 該資源的 SSOT 位置在哪？（依規則 1 表格）
- [ ] 是否有對應 audit script？（依規則 2 表格）
- [ ] 若是 runtime 服務，是否有業務量 healthcheck？（規則 3）
- [ ] 若是 dual-write，是否 atomic 或 dual-validation？（規則 4）
- [ ] 若是跨 repo，是否走 ADR + Registry + Audit 三件套？（規則 5）

---

> **核心精神**：**寫程式碼很容易；保持跨檔資源一致才是工程治理的真正功夫。**
> 跨檔 SSOT 失效對使用者是 silent dormant 災難，對團隊是技術債滾雪球。
