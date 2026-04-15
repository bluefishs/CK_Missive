# Cloudflare Access Bypass 政策 — 公網 webhook / ACP 必要豁免

> **背景**：ADR-0016 啟用 CF Access SSO 後，預設所有 `missive.cksurvey.tw` 路徑需登入。
> 但機器流量（webhook / ACP）不能走人員登入，需設 Bypass policy。

## Dashboard 操作路徑

```
Zero Trust → Access → Applications → CK Platform → Edit → Policies
  → Add a policy
```

## 建立 Bypass Policy

| 欄位 | 填入 |
|---|---|
| Policy name | `Machine Traffic Bypass` |
| Action | **Bypass** |
| Session duration | Same as application |

**Include** 區塊新增多條 path 規則（每條一個 Include row）：

| Selector | Value |
|---|---|
| Path | `/api/health` |
| Path | `/api/health/detailed` |
| Path | `/api/ai/agent/tools` |
| Path | `/api/ai/agent/query_sync` |
| Path | `/api/hermes/acp` |
| Path | `/api/hermes/feedback` |
| Path | `/api/telegram/webhook` |
| Path | `/api/discord/interactions` |
| Path | `/api/line/webhook`（LINE 下線前過渡期保留） |

> 這些路徑走 `X-Service-Token` 或平台自身 webhook 驗證，不需人員登入。

## Policy Order（重要）

CF Access 依序評估：
```
1. Bypass Machine Traffic  ← 先擋下機器流量
2. Allow Team              ← 再檢查登入
```

Bypass 必須排第一順位，否則機器流量會被 Allow policy 的 Email OTP 阻擋。

## 驗收

```bash
# 人員路徑應彈 OTP 登入頁
curl -I https://missive.cksurvey.tw/
# 預期: 302 redirect to https://<team>.cloudflareaccess.com/

# Webhook/ACP 應直接透傳
curl -I -X POST https://missive.cksurvey.tw/api/health
# 預期: 200（不含 CF_Authorization cookie 仍通）

curl -X POST https://missive.cksurvey.tw/api/hermes/acp \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","messages":[{"role":"user","content":"x"}]}'
# 預期: 401/403（因缺 X-Service-Token；非 CF Access 的 302）
```

如 `curl -I` 於 webhook path 回傳 302 → Bypass policy 失效或順序錯。

## 多專案套用

同一 Access Application 可關聯多 hostname：
```
Applications → CK Platform → Edit → Application Configuration
  Domains:
    missive.cksurvey.tw
    lvrland.cksurvey.tw
    pile.cksurvey.tw
```

Bypass path 規則全域套用到所有 hostname（因 path 結構設計一致）。
