# L41 — JWT Secret Drift Silent Fail（4 重疊加）

> **Lesson ID**: L41
> **Date sealed**: 2026-05-21
> **Category**: Auth / Cross-repo / Silent-fail anti-pattern
> **Severity**: CRITICAL
> **制度化於**: `shared-modules/ck-sso-py/install.sh` 的 4 acceptance check
> **跨 repo 真採用**: `CK_lvrland_Webmap/backend/app/core/ck_sso.py` / `CK_PileMgmt/backend/app/core/ck_sso.py`

---

## 一、事件梗概

員工 SSO Phase 1.5 整合 missive 時，backend `verify_ck_sso_jwt` 持續回 401 但無人察覺真因 — 因為：

1. **JWT secret drift**：backend `.env` 內 `CK_SSO_JWT_SECRET` 與 Cloudflare Pages 的 `JWT_SECRET` 不同步（owner 手動 copy hex 時打錯一字元）
2. **Silent fail log level**：`verify` 失敗時用 `logger.debug(...)`，production log level 是 INFO 所以**完全不會輸出**
3. **異常吞噬**：`try/except` 抓 `JWTError` 直接 return None，沒分辨四種 exception (SIGNATURE_INVALID / EXPIRED / ISSUER_INVALID / MISSING_CLAIM)
4. **缺真 E2E**：CI 用 mock JWT 跑單元測試全綠，但從未跑「真 CF Pages 簽發 → 真 backend 驗證」端到端

四個獨立反模式單獨都不致命，**疊加後構成「驗證永遠失敗、永遠靜默」的死區**。owner 花 6 小時逐項排除才找出第 1 條 secret 不同步。

---

## 二、根因鏈

```
CF Pages JWT_SECRET (Cloudflare Dashboard secret store)
  ↓ owner 手動 copy
backend .env CK_SSO_JWT_SECRET (hex 64 chars)
  ↑ 一字元打錯 = signature mismatch every time
  
verify_ck_sso_jwt():
  try:
    jwt.decode(...)  # → SIGNATURE_INVALID
  except JWTError:
    logger.debug("JWT invalid")  # ← 永遠不輸出
    return None
  ↓
caller 收 None → 401 → 前端 redirect 回 login → loop
```

---

## 三、制度化（ck-sso-py install.sh 的 4 acceptance check）

新 consumer repo 採用 ck-sso-py 時，install.sh **強制**跑 4 check，任一 fail 拒絕標記為「真活」：

| # | Check | 自動/手動 | 守護 |
|---|---|---|---|
| 1 | `.env` 含 `CK_SSO_JWT_SECRET=...` 且 owner 手動比對 hex 與 CF Pages | 半自動 | 反模式 1（secret drift） |
| 2 | `ck_sso.py` 的 4 種 JWT exception 用 `logger.warning` 非 `logger.debug` | 全自動 grep | 反模式 2+3（silent fail + 吞噬） |
| 3 | `curl -X POST /api/auth/sso-bridge -d '{}'` 回 401 + 「缺少 SSO cookie」（非 500/404/timeout） | 手動 | 反模式 3（區分 exception 類型） |
| 4 | 全新無痕視窗 → www login → 點系統卡片 → 自動進系統 + backend log 出現 `LOGIN_SUCCESS auth_provider=ck_sso_bridge` | 手動 E2E | 反模式 4（真 E2E 不可省） |

`install.sh` 退出碼：
- Check 1+2 任一 fail → exit 1（install 不算真活）
- 全綠 → exit 0 + 提示 owner 必跑 Check 3+4

---

## 四、反思題（給未來 session）

1. 下次新加任何「驗證型」endpoint，是否預設 `logger.warning` 而非 `logger.debug`？
2. 任何 `try/except` 抓多型 exception，是否要分辨子類型分別 log？
3. 任何「secret 跨環境同步」流程，是否有 hex 比對的 self-test？
4. CI 用 mock 跑 auth 測試時，是否強制要求**至少 1 個** real-roundtrip integration test？
5. 「採用」一個新模組的定義是什麼？「程式碼進 repo + import 不報錯」夠嗎？還是必須有 owner E2E pass？

---

## 五、相關資產

- **install.sh**：`D:/CKProject/CK_Missive/shared-modules/ck-sso-py/install.sh`（v1.0, 2026-05-21）
- **SSO runbook**：`D:/CKProject/CK_Website/docs/SSO-IMPLEMENTATION-STATUS.md` v1.2 (457 行跨 session 追蹤)
- **真採用範本**：
  - `D:/CKProject/CK_lvrland_Webmap/backend/app/core/ck_sso.py`
  - `D:/CKProject/CK_PileMgmt/backend/app/core/ck_sso.py`
- **預計未來採用**：`hermes-agent` / `CK_KMapAdvisor` / `CK_AaaP`

---

## 六、與其他 lesson 的關係

- **L37 — 平時保險反模式**：「平常 silent debug，出事才升 warning」的廣義版本（L41 是其 auth-specific instance）
- **L29 — dict-key contract drift**：tool 名稱 typo 導致 silent skip 的 invocation-time 反模式（L41 是 verify-time 變體）
- **L21 — 坤哥自我成長中斷**：silent fail 累積導致系統「假活」的元教訓
