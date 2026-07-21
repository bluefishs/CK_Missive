# Tier 1 共享套件 SOP — import 式模組化（vendored wheel，過 Docker）

> **建立**：2026-07-21（Phase 0 spike PASS）
> **策略**：`docs/architecture/MODULARIZATION_CROSS_PROJECT_STRATEGY.md`
> **驗證**：ck-auth 0.1.0 wheel → CK_Missive backend `import ck_auth` 容器內成立、health 200、公網 200
> **定位**：後端 Tier 1 共享套件的「打包→引用→更新」單一機制。取代 copy 式 vendoring（`.template`+install.sh），
> 讓「改一次共享套件、全 consumer 版本 bump 同步」，且相容 Docker per-repo build context。

---

## 為何 vendored wheel（而非 `pip install -e ../..`）

各 repo 後端在**容器**內跑、build context = `./backend`（sibling `shared-modules/` **不在 context**）→
`pip install -e ../shared-modules/ck-auth` 在 Docker build 內**必失敗**（過去 import 式後端做不成的隱形牆）。
**vendored wheel** 解法：把建好的 `.whl` 放進 repo `backend/vendor/`（進 build context）+ Dockerfile `pip install`，
既保 import 語意 + 版本釘選，又過 Docker。零 registry 成本。

---

## A. 套件端（`shared-modules/ck-auth-py/`）

```
shared-modules/ck-auth-py/
├── pyproject.toml          # name=ck-auth, version=X.Y.Z（SemVer）
├── src/ck_auth/__init__.py # __version__ + 公開 API
└── dist/                   # build 產出（.whl）
```

**建 wheel**（host，需 `python -m build`）：
```bash
cd shared-modules/ck-auth-py
python -m build --wheel        # 產出 dist/ck_auth-X.Y.Z-py3-none-any.whl
```

**版本規約**：SemVer；破壞性變更 → major + 遷移 note；consumer 釘 `ck-auth==X.Y.Z`（Phase 2 gate 偵測偏移）。

---

## B. Consumer 端（各 repo 後端，如 CK_Missive/backend）

1. **vendor wheel**：`cp shared-modules/ck-auth-py/dist/ck_auth-X.Y.Z-*.whl <repo>/backend/vendor/`（**入版控**＝釘版本、可重現 build）。
2. **Dockerfile**（builder stage，requirements 安裝後）：
   ```dockerfile
   # Tier 1 共享套件（vendored wheels）— import 式單一源
   COPY vendor/ ./vendor/
   RUN pip install --no-cache-dir ./vendor/*.whl
   ```
3. **程式**：`import ck_auth`（取代本地 copy）。
4. **驗證**：`docker exec <backend> python -c "import ck_auth; print(ck_auth.ping())"` + health 200 + L76（host 8001 + 公網 200）。

---

## C. 更新流程（「一次修、全同步」）

1. 改 `shared-modules/ck-auth-py/src/...` → bump `pyproject.toml` version → `python -m build --wheel`。
2. 每個 consumer：換 `backend/vendor/` 新 wheel（刪舊、放新）→ rebuild backend → 驗證（B-4）。
3. **Phase 2 gate**：`tier1_version_skew_audit` 偵測 consumer vendored wheel 版本落後 → 先 warn 一輪 → 再 pre-push block。

> vs 舊 copy vendoring：修法**只在套件一處**（非逐 repo 改 sso_bridge.py）；consumer 只換 wheel + rebuild。
> 這正是 2026-07-21 SSO 白填「手搬 4 repo」要根除的痛點。

---

## D. 邊界（避免 over-standardize / L58）

- 只把「跨 repo 真一致且穩定」的橫切能力升 Tier 1（auth/session、JWT 驗證、error 契約、observability client）。
- 耦合各 repo model 者走 **Tier 2 契約 + adapter + conformance test**（非塞進 wheel）。
- 各域業務 = **Tier 3 per-repo**，不打包、audit 不管。

---

## E. 已驗證 / 待辦

- ✅ Phase 0 spike：ck-auth 0.1.0 skeleton（`ping()`）過 Docker、CK_Missive 容器 import 成立。
- ⏳ Phase 1：ck-auth 併入 rotation/session/refresh-SSO-fallback + AsyncAuthAdapter/SyncAuthAdapter；Missive(async)+lvrland(sync) 改 import。
- ⏳ Phase 2：version_skew gate + conformance test。
