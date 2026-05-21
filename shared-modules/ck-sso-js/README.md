# ck-sso-js

> Framework-agnostic SSO Bridge client for `*.cksurvey.tw` consumer frontends
> v1.0 — 2026-05-21（L41 + L42 + L43 lessons sealed）

抽自 CK_Missive frontend：
- `api/interceptors.ts attemptSSOBridge() v3.0`
- `services/authService.ts ssoBridge() v3.0`
- `pages/EntryPage.tsx useEffect 觸發邏輯`

**FQID**：`CK_Missive#ck-sso-js_v1.0`
**Companion**：`CK_Missive#ck-sso-py_v1.0`（後端 verifier）

---

## 為什麼需要

ck-sso-py（後端）已抽出且 4 個 subdomain 都有 sso-bridge endpoint。但 **lvrland / pile / digitaltwin 前端 grep 全 source 零 `ssoBridge` 字串** — 後端 dormant，用戶體驗等同未整合。

L41 教訓 sealed: install.sh 自動 check 1-3 通過 ≠ 真活。本 package 把「前端整合」工項顯式化 + 加 Check 5 ground-truth log assertion。

---

## API

```ts
import { attemptSSOBridge, resetSSOBridgeState, getSSOBridgeState } from 'ck-sso-js';
// React: import { useSSOBridge } from 'ck-sso-js/react';
```

### `attemptSSOBridge(config)` → `Promise<SSOBridgeResult>`

| Param | Type | 預設 | 說明 |
|---|---|---|---|
| `apiBaseURL` | string | (必填) | consumer API base，例 `'https://lvrland.cksurvey.tw/api'` |
| `endpoint` | string | `'/auth/sso-bridge'` | bridge endpoint path |
| `timeoutMs` | number | 8000 | fetch timeout |
| `cooldownMs` | number | 30000 | 同 session 內 retry 間隔 |
| `maxFail` | number | 3 | 連續 N 次 transient fail 永久鎖 |
| `storagePrefix` | string | `'ck_sso_bridge'` | sessionStorage key 前綴 |
| `logger` | Console / null | console | null = 靜默 |
| `onSuccess` | `(data) => void` | `location.reload()` | 200 後 callback |
| `fetchImpl` | typeof fetch | global fetch | 給測試 / axios adapter |

Result：

```ts
{
  ok: boolean;
  status?: number;
  data?: unknown;
  reason: 'locked' | 'cooldown' | 'success' | 'terminal' | 'transient' | 'network';
}
```

### `useSSOBridge(config)` (React)

```tsx
const { state, result, retry } = useSSOBridge({ apiBaseURL: '/api', onSuccess: () => navigate('/dashboard') });
// state: 'loading' | 'success' | 'failed' | 'skipped'
```

完整範例見 `examples/EntryPage-react.tsx` / `examples/vanilla.ts`。

---

## 三層防禦邏輯（從 missive frontend v3.0 沿用）

1. **Cooldown 30s**：解決「401 不設 flag → 無限刷」(v2.0 死循環)
2. **maxFail 3**：連續 transient 失敗 → 永久 lock（保護 backend）
3. **Terminal lock**：200 success / 403 / 404 → `sessionStorage.flag = '1'` 永不重試

| HTTP | reason | sessionStorage 動作 |
|---|---|---|
| 200 | success | flag=1, fail-count cleared |
| 403 | terminal | flag=1 (帳號無此系統權限) |
| 404 | terminal | flag=1 (帳號未在子系統建立) |
| 401 | transient | fail-count++ |
| 429 | transient | fail-count++ |
| 5xx | transient | fail-count++ |
| network err | network | fail-count++ |
| (locked / cooldown) | locked / cooldown | (skip fetch) |

---

## 安裝

```bash
cd <target-frontend-dir>          # e.g. CK_lvrland_Webmap/frontend
bash <ck-sso-js-path>/install.sh --target=. --framework=react
# 自動：
#   1. 複製 src/ → <target>/src/lib/ck-sso-js/
#   2. 5 acceptance check（含 Check 5 backend-log ground-truth）
#   3. 提示在 EntryPage useEffect 加 useSSOBridge
```

手動步驟（install.sh 不會做的）：
1. 在 React app 入口 page（EntryPage / LoginPage / `/` route）useEffect 加：
   ```tsx
   const { state } = useSSOBridge({
     apiBaseURL: import.meta.env.VITE_API_BASE_URL || '/api',
     onSuccess: () => navigate('/dashboard'),
   });
   ```
2. Rebuild frontend + redeploy
3. **跑 owner E2E real test**（不可省略 — L41/L42/L43 教訓）
4. **檢查 backend log 有 `[SSO-BRIDGE] received cookies=` 字串**（Check 5 ground-truth）

---

## L41-recurrence 防護（Check 5）

> 2026-05-21 中午 lvrland + pile 「ck-sso-py 裝完」狀態 docs 標 ✅，
> 但 backend log `[SSO-BRIDGE]` 字串 0 hits — 因為前端從沒呼叫 backend。
> 即「裝完 ≠ 真活」反模式復發。

install.sh Check 5：

```bash
# 5. backend log 真實出現過 SSO-BRIDGE 字串？
docker logs <consumer-backend> 2>&1 | grep -q "\[SSO-BRIDGE\] received cookies" \
  && echo "✓ Check 5 PASS (ground-truth log found)" \
  || echo "❌ Check 5 FAIL — backend 從沒被呼叫過。前端整合可能 dormant。"
```

Check 5 fail ≠ install fail，但 install.sh 會顯式提示 owner 跑 E2E 才能宣稱真活。

---

## 測試

```bash
node tests/sso-bridge.test.mjs   # 13 cases, 含 sessionStorage 三層防禦
```

---

## 變更紀錄

| 日期 | 版本 | 變更 |
|---|---|---|
| 2026-05-21 | v1.0 | 初版抽出 — 從 CK_Missive frontend authService.ssoBridge v3.0 + interceptors.attemptSSOBridge v3.0 + EntryPage useEffect。L41+L42+L43 sealed |
