# ck-sso-py

> Cross-repo Single Sign-On bridge for `*.cksurvey.tw` subdomains
> v1.0 — 2026-05-21（L41 lesson sealed）

跨 repo SSO bridge backend Python package。驗證來自 `www.cksurvey.tw` 簽發的
`ck_employee` JWT cookie，自動建立子系統 session。

**FQID**：`CK_Missive#ck-sso-py_v1.0`
**Source repo**：CK_Missive
**Status**：production-ready（CK_Missive 5/21 E2E 真活驗證）

---

## 適用情境

任何 `*.cksurvey.tw` 子網域 backend 想接受 www dashboard 跳轉自動登入：
- `missive.cksurvey.tw` ✅ 已 production (5/21 owner E2E PASS)
- `lvrland.cksurvey.tw` ⏳ 待裝
- `pile.cksurvey.tw` ⏳ 待裝
- 未來新增子系統皆可用

---

## 安裝（依 SSO-IMPLEMENTATION-STATUS.md §跨 repo 套用 SOP）

```bash
cd <target-repo>
bash <path-to-ck-sso-py>/install.sh

# install.sh 會：
# 1. 拷貝 core/ck_sso.py → backend/app/core/
# 2. 從 sso_bridge.py.template 用 sed 生 sso_bridge.py（替換 SYSTEM_NAME）
# 3. 拷貝 test_ck_sso_verify.py → backend/tests/unit/
# 4. .env 範本：CK_SSO_ENABLED + CK_SSO_JWT_SECRET 加入 .env.example
# 5. 跑 4 acceptance check（L41 教訓制度化）
```

安裝後手動步驟：
1. backend `.env` 填入 `CK_SSO_JWT_SECRET=<與 CF Pages 同值 hex>`
2. register `sso_bridge_router` 到 FastAPI app（在 routes.py 或 main.py）
3. frontend 套 `authService.ssoBridge()` v3.0（複製自 CK_Missive frontend）
4. **跑 owner E2E real test**（L41 教訓：4 acceptance check 自動跑完還不算真活）

---

## L41 4 acceptance check（install.sh 自動跑）

```bash
# Check 1: backend secret 與 CF Pages 一致（owner 手動比對 hex）
# Check 2: verify 失敗 log 是 warning 非 debug（L37/L41 反模式守護）
# Check 3: SSO bridge endpoint 健康（curl 401 預期）
# Check 4: owner 真 E2E（www login → 點卡片 → backend log LOGIN_SUCCESS）
```

**Check 4 不可省略** — L41 教訓：「4 acceptance 自動跑完 ≠ 真活」。

---

## 設計原則

| 原則 | 實現 |
|---|---|
| Pure-function portability | `core/ck_sso.py` 無 missive-specific import，100% portable |
| Consumer 介面解耦 | `sso_bridge.py.template` 用 sed-replace `__SYSTEM_NAME__` |
| L41 silent fail 防範 | verify 失敗 4 種 exception 各自 `logger.warning` |
| 與既有認證共存 | feature flag `CK_SSO_ENABLED` 控制；不取代任何 Google/LINE/IP 路徑 |
| 可逆 100% | `CK_SSO_ENABLED=false` 立刻關閉，0 副作用 |

---

## 與 ck-auth 的關係

ck-auth (`CK_Missive#ck-auth_v1.0`) frontend 部分有 LR-015 風險（hardcode 30+
business ROUTES）。CK SSO + ck-sso-py 已**覆蓋 ck-auth 設想的 99% 場景**：

| 機制 | 真採用 | 維護成本 |
|---|---|---|
| ck-auth v1.0 frontend | 0 repo | 高（force install 必爆 LR-015） |
| **ck-sso-py + CK SSO** | 1 repo + 2 規劃中 | 低（純 stateless verify） |

建議：未來新 repo 整合身份認證**優先選 ck-sso-py + CK SSO**，避免 ck-auth 風險。

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-21 | v1.0 | 初版抽出 (CK_Missive Task 7-missive 100% 真活後)。含 L41 lesson sealed |
