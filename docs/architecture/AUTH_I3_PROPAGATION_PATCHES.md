# auth I3 propagation — lvrland / pile 預寫修法（**尚未套用**）

> **建立**：2026-07-29
> **狀態**：⏸ **預寫完成、刻意不套用**。等 owner Missive 瀏覽器實測 gate 通過才 apply。
> **為何不直接寫進那兩個 repo**：延續 07-28 決定「**不留未驗證的 auth 修法於主產品**」
> （當時 lvrland 分析後已還原乾淨）。本文＝可直接照抄的完整修法，apply 成本 < 10 分鐘。
> **上游設計**：`AUTH_LIFECYCLE_ROBUSTNESS_DESIGN.md` §2 不變式 I3 / §5.2（07-29 讀碼複核修正版）

---

## 0. 為何範圍比原估小（07-29 讀碼實證）

| 原估（07-25） | 實證（07-29） |
|---|---|
| lvrland 缺 401 單飛，要補 | ❌ **不必**——已有（`inFlightRefresh`，P161 2026-04-18）。原判定係 grep `isRefreshing` 未命中其命名（L25 關鍵字陷阱） |
| 後端 I4 待確認，可能要改 | ❌ **不必**——兩者 `auth.py` 共用 auth-response helper 已於 login/refresh/sso 全路徑重發 CSRF |
| 需比照 Missive 補「CSRF 自癒單飛」 | ❌ **做不到也不需要**——兩者無獨立 csrf 端點；csrf 僅由 auth 回應 header 補水 |

⇒ **真缺口只剩 I3**：CSRF-403 未被視為可恢復。**純前端、每 repo 一處、後端不動。**

---

## 1. 共用判別式（兩 repo 相同）

後端 `csrf_service.py` 兩種 403 detail（兩 repo 字串完全相同，對應 fitness step 73 已確認的單一源）：

- `缺少 CSRF Token，請求被拒絕` ← **重載後記憶體空**（csrfToken 不持久化）即觸發
- `CSRF Token 無效或已過期，請重新登入` ← Redis TTL 到期 / 不匹配

兩者**皆可恢復**（refresh 會重發 csrf）。判別式：

```ts
/** 403 是否為「CSRF 類」＝可恢復（非權限不足）。 */
function isRecoverableCsrf403(data: unknown): boolean {
  const detail =
    (data as { detail?: string; message?: string; error?: { message?: string } })?.detail ??
    (data as { message?: string })?.message ??
    (data as { error?: { message?: string } })?.error?.message ??
    '';
  return typeof detail === 'string' && detail.includes('CSRF Token');
}
```

> ⚠️ **不可**把所有 403 都當可恢復——`權限不足` / `帳戶尚待管理員啟用` 必須維持原行為。

---

## 2. lvrland 修法（`frontend/src/api/client.ts`）

**現況**（約 line 341）：
```ts
case 403:
  errorMessage = '沒有權限執行此操作';
  apiErrorBus.emit({ code: 403, message: '權限不足，請重新登入' });
  break;
```

**改為**：
```ts
case 403: {
  // I3（2026-07-29）：CSRF 類 403 視為「可恢復」——借用既有單飛 refresh 取新 csrf
  // （回應 header 由 response interceptor 自動寫回 authStore），再單次重試原請求。
  // 僅重試仍 403 才彈錯。涵蓋兩情境：(a) 閒置逾 TTL 回來 (b) 重載後 csrfToken 記憶體空。
  const cfg403 = error.config as CustomAxiosRequestConfig;
  if (
    isRecoverableCsrf403(data) &&
    !cfg403?._csrfRetry &&
    useAuthStore.getState().isAuthenticated &&
    !isAuthEndpoint(cfg403?.url)
  ) {
    cfg403._csrfRetry = true;
    if (!inFlightRefresh) {
      inFlightRefresh = apiClient
        .post('/auth/refresh', {}, { withCredentials: true })
        .finally(() => {
          inFlightRefresh = null;
        });
    }
    try {
      const r = await inFlightRefresh;
      if (r.status === 200) {
        return apiClient.request(cfg403 as AxiosRequestConfig);
      }
    } catch {
      /* 落到下方一般 403 處理 */
    }
  }
  errorMessage = '沒有權限執行此操作';
  apiErrorBus.emit({ code: 403, message: '權限不足，請重新登入' });
  break;
}
```

**配套**：`CustomAxiosRequestConfig` 加 `_csrfRetry?: boolean;`（與既有 `_retry` 分開，避免和 401 重試互相吃掉次數）。

---

## 3. pile 修法（`frontend/src/api/client.ts`）

pile 用 `isRefreshing` + `pendingQueue`（非 promise），故走佇列版：

```ts
case 403: {
  const cfg403 = error.config as CustomAxiosRequestConfig;
  if (
    isRecoverableCsrf403(data) &&
    !cfg403?._csrfRetry &&
    !refreshPermanentlyFailed &&
    useAuthStore.getState().isAuthenticated &&
    !(cfg403?.url || '').includes('/auth/')
  ) {
    cfg403._csrfRetry = true;
    const ok = await new Promise<boolean>((resolve) => {
      pendingQueue.push(resolve);
      if (!isRefreshing) {
        isRefreshing = true;
        apiClient
          .post('/auth/refresh', {}, { withCredentials: true })
          .then(() => resolveQueue(true))
          .catch(() => resolveQueue(false))
          .finally(() => {
            isRefreshing = false;
          });
      }
    });
    if (ok) return apiClient.request(cfg403 as AxiosRequestConfig);
  }
  errorMessage = data?.detail || data?.message || data?.error?.message || '沒有權限執行此操作';
  break;
}
```

**配套**：`CustomAxiosRequestConfig` 加 `_csrfRetry?: boolean;`。

---

## 4. Regression 測試（每 repo 一份，比照 Missive `authService.interceptor401.regression.test.ts`）

必測 4 case：
1. **CSRF-403 → refresh 成功 → 原請求重試成功**，且**不**觸發 `apiErrorBus` / 不彈錯（I1+I3）。
2. **非 CSRF 的 403（如「權限不足」「帳戶尚待管理員啟用」）→ 行為不變**（不重試、照常提示）。
3. **併發 N 個 CSRF-403 → 只發出 1 次 `/auth/refresh`**（I2 單飛；斷言 mock 呼叫次數 === 1）。
4. **refresh 失敗 → 只重試 1 次後正常彈錯**，無無限迴圈（`_csrfRetry` 旗標生效）。

---

## 5. Apply 順序（gate 通過後）

1. lvrland：apply §2 + §4 測試 → `tsc` → 測試綠 → build → **owner 登入實測**（閒置逾 TTL 回來操作 + 重載後操作）→ 不通過即 revert。
2. pile：同上（§3）。
3. **TTL 統一 60min**（恢復證實後才做）：lvrland `ACCESS_TOKEN_EXPIRE_MINUTES`（現寫法 `30 if prod else 480`）、pile `30` → **60**；backend 重啟 + **L76 公網 200 複驗**。
4. Missive SSO `480 → 60`（最後，且必須在 Missive 恢復已實測通過之後）。
5. **立通用護欄**：fitness audit 檢查各系統 FE 具備「401 單飛 + CSRF-403 可恢復重試」+ access TTL 對齊 60min。
6. DT：bearer/24h，本問題不適用，維持最低優先。
