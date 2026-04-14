---
name: ck-missive-bridge
version: 1.0.0
description: 將查詢/指令轉送至 CK_Missive 後端 Agent API，取得公文、案件、行事曆、ERP、知識圖譜等領域回覆。
author: CK_Missive Team
license: MIT
---

# CK Missive Bridge — Hermes Skill

將 Hermes Agent 作為**通道前端**，所有領域查詢委派給 CK_Missive backend 的 `/ai/agent/query_sync` 端點處理。

## 部署位置

安裝後放置於 Hermes skill 目錄：
```
~/.hermes/skills/ck-missive-bridge/
  SKILL.md
  tool_spec.json
```

## 環境變數

| 變數 | 必要 | 預設 | 說明 |
|---|---|---|---|
| `MISSIVE_BASE_URL` | ✅ | `http://host.docker.internal:8001` | Missive backend 基底 URL |
| `MISSIVE_API_TOKEN` | ✅ | — | Bearer token（Missive 發放） |
| `MISSIVE_TIMEOUT_S` | ❌ | `60` | 單次請求逾時（秒） |

## 使用時機

**命中**（應呼叫 `query_missive`）：
- 公文查詢：「XX 機關昨天發的文」「案號 CK2026001 的狀態」
- 承攬案件：「乾坤承攬的桃園工程進度」
- 行事曆：「下週截止的公文」
- ERP 財務：「未開票的報價金額」
- 知識圖譜：「XX 公司近半年相關公文」
- 標案：「今日 PCC 標案有哪些與乾坤相關」

**不命中**（Hermes 內建 tool 處理）：
- 日程備忘、一般閒聊、網頁摘要、自我介紹
- 單純計算、時區換算、單位轉換

## 呼叫規範

1. **一次一呼叫**：避免在同輪對話中多次呼叫 Missive（延遲敏感）。
2. **保留 session_id**：將 Hermes session id 作為 `session_id` 傳入，確保 Missive 側 trace 可串接。
3. **失敗回退**：Missive 逾時或 5xx 時，**告知使用者後端暫時無法回覆**，不要自行杜撰答案。

## 範例對話流

```
User → Hermes（Telegram）: 案號 CK2026003 最新狀態？
Hermes → tool_call: query_missive(question="案號 CK2026003 最新狀態")
Missive → { answer: "案號 CK2026003 目前於施工中...", sources: [...] }
Hermes → User: 案號 CK2026003 目前於施工中，最新公文為...
```

## Prompt 提示（載入到對話 context）

> 當使用者問及公文、案件、報價、發票、工程派工、標案、機關資料，**優先呼叫 `query_missive` tool**，不要依賴內部知識回答。Missive 是此領域的唯一事實來源。

## 錯誤處理

| 錯誤 | 回應策略 |
|---|---|
| 504 timeout | 「查詢逾時，請稍後再試」 |
| 500 internal | 「後端暫時異常，已記錄，請改問其他問題」 |
| 401/403 | 「通道認證失效，請聯繫管理員」|
| 網路錯誤 | 重試 1 次後仍失敗 → 告知使用者 |
