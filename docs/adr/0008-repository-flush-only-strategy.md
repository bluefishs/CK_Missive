# ADR-0008: Repository 層 flush-only 交易策略

> **狀態**: accepted
> **日期**: 2026-02-24
> **決策者**: 開發團隊
> **關聯**: CHANGELOG v1.60.0, memory/lessons-learned.md

## 背景

CK_Missive 系統在交易管理上曾經歷多次資料一致性問題：

1. **不一致的 commit 時機** — 部分 Repository 在方法內部呼叫 `commit()`，部分則不做，開發者難以預期交易邊界
2. **跨 Repository 原子性問題** — 當一個 Service 需要依序呼叫多個 Repository 時，若第一個 Repository 已 `commit()`，第二個 Repository 失敗時無法回滾第一個的變更，導致「部分提交」（partial commit）的資料不一致
3. **交易污染** — 審計日誌（AuditService）與業務邏輯共享同一個 `db` session，當審計寫入失敗時，連帶導致業務交易也被回滾
4. **併發問題** — 在 `asyncio.gather()` 中共用同一個 `db` session，導致 SQLAlchemy 的 `MissingGreenlet` 錯誤或不可預期的交易狀態

這些問題在系統規模擴大（87 個端點、10 個 Repository）後愈發頻繁，需要一個統一且明確的交易管理策略。

## 決策

採用 **flush-only** 策略，將交易控制權收歸上層：

### Repository 層規範
- Repository 方法只能呼叫 `flush()`（將 SQL 送至資料庫但不提交）
- **禁止**在 Repository 中呼叫 `commit()` 或 `rollback()`
- `flush()` 會觸發資料庫約束檢查（如唯一鍵衝突），但不會永久寫入

### 交易提交責任
- **API 端點層** 或 **Service 層** 負責呼叫 `commit()`
- 一個 HTTP 請求對應一個交易邊界，確保原子性
- Service 方法若需要多步驟操作，在最後統一 `commit()`

### 隔離 Session 模式
- `AuditService` 使用獨立的 `AsyncSession`，與業務交易完全隔離
- 審計日誌寫入失敗不影響業務交易
- 系統通知（SystemNotification）同樣使用獨立 session

### 併發安全
- 同一 `db` session 禁止在 `asyncio.gather()` 中共用
- 需要併發操作時，各任務使用各自的 session（透過 `session_factory` 建立）

## 後果

### 正面

- 跨 Repository 操作天然具備原子性，消滅了「部分提交」類型的 bug
- 審計日誌與業務邏輯完全解耦，互不影響
- 交易邊界清晰可見（grep `commit()` 即可找到所有交易提交點）
- 降低了新開發者犯錯的機率 — Repository 層的約束簡單明確
- `flush()` 仍會觸發資料庫約束檢查，問題可以提前發現而非延遲到 `commit()` 時

### 負面

- 開發者必須記得在端點或 Service 層呼叫 `commit()`，遺漏會導致資料未持久化
- `flush()` 拋出的約束違反例外（如 `IntegrityError`）仍需在呼叫處處理
- `AuditService` 需要獨立的 session factory 和依賴注入配置，增加了 DI 複雜度
- 現有 87 個端點中僅 18% 使用 Repository 層，其餘直接操作 ORM，規範尚未完全統一
- 長時間未 `commit()` 的交易可能持有鎖過久，需要設定 `statement_timeout`（目前 30 秒）

## 替代方案

| 方案 | 評估結果 |
|------|----------|
| **Unit of Work 模式** | 交易管理最完善，但對目前專案規模（10 個 Repository）過度工程化，引入額外抽象層 |
| **Auto-commit per Repository** | 最簡單直觀，但犧牲原子性，跨 Repository 操作無法保證一致性 |
| **Nested Transaction / Savepoint** | PostgreSQL 支援，可在交易內建立回滾點，但增加嵌套邏輯複雜度，除錯困難 |
| **每個 Repository 獨立 Session** | 完全隔離，但失去跨 Repository 的共享交易能力，需要分散式交易協調 |

最終選擇 flush-only 策略，在簡潔性與交易安全之間取得平衡，並透過獨立 session 解決交易污染問題。
