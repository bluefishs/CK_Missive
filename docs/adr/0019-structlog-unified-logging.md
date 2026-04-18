# ADR-0019: structlog 統一日誌格式

> **狀態**: accepted
> **日期**: 2026-04-18
> **決策者**: Aaron (CK_Missive maintainer)
> **關聯**: CHANGELOG v5.6.0, backend/app/core/structured_logging.py

## 背景

Backend 有 239 個 service 檔案使用 `logging.getLogger(__name__)`（stdlib），
另有 `structured_logging.py` 提供 structlog wrapper，但兩套系統並行。
Loki 觀測棧需要統一 JSON 格式日誌，否則 Promtail 無法正確解析。

手動逐檔改寫 239 個 service 不切實際且風險高。

## 決策

採用 **structlog stdlib bridge** 方案：
- `structlog.stdlib.ProcessorFormatter` 作為 root logger 的 formatter
- 所有 `logging.getLogger()` 輸出自動經由 structlog processor chain 格式化
- **零改動** 現有 service 檔案，向後相容

配置位於 `backend/app/core/structured_logging.py`，在 `main.py` 頂層 import 啟動。

### 日誌格式

```json
{
  "event": "REQUEST_END POST /api/...",
  "level": "info",
  "logger": "app.services.xxx",
  "timestamp": "2026-04-18T...",
  "app_name": "CK_Missive",
  "version": "3.0.1",
  "environment": "development"
}
```

### 環境策略

| 環境 | 格式 | 控制 |
|------|------|------|
| 生產/公網 | JSON（預設） | Loki 直接解析 |
| 開發 console | Colored console | `STRUCTLOG_CONSOLE=1` |

## 後果

### 正面
- Loki 原生 JSON 解析，無需 Promtail regex
- 全 backend 統一格式，便於搜尋和告警
- 零改動現有 service，風險最低
- request_id 自動注入，跨服務追蹤

### 負面
- structlog 24.1.0 成為硬依賴
- root logger formatter 被覆蓋，第三方庫日誌也走 JSON（已降噪 httpcore/httpx/watchfiles）
- PM2 log 輸出為 JSON 字串，肉眼閱讀需工具

## 替代方案

1. **逐檔改寫 logging → structlog.get_logger()** — 風險高、工期長、PR diff 巨大，否決
2. **只改 Promtail regex 適配現有格式** — 非結構化日誌難以穩定解析，否決
3. **使用 python-json-logger** — 功能較弱，不支援 context binding，否決
