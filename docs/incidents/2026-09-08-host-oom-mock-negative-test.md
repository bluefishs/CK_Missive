# 事件報告 — 主機記憶體耗盡硬當，觸發者是本 repo session 的 MagicMock 負向測試（2026-09-08）

> **登記處**：`CK_AaaP/platform/CROSS_SESSION_BLOCKERS.md` → `B-MISSIVE-MOCK-OOM`（P1）。
> **交辦**：CK_Missive owner；請同步登入 `docs/architecture/LESSONS_REGISTRY.md`。
> **影響**：CK-AARON 21:26:57 硬當（事件 41），公文系統、地價平台、樁位管理等全部容器一併中斷，直到 21:27 重開機。

## 事件鏈（本地時間）

| 時間 | 事實 | 證據 |
|---|---|---|
| 19:08:20 | 本 repo 的 Claude Code session 執行 `timeout 60 python -c "from unittest.mock import MagicMock; s=MagicMock(); del s.__iter__; set(s) ..."` | `~/.claude/projects/D--CKProject-CK-Missive/b71a8773-d57d-4e17-bea9-b35fabca668f.jsonl` |
| 19:09:23 | 回報「completed with no output」——Git Bash `timeout` 在 Windows 殺不掉子 python，該行程（PID 18916）繼續成長 | 同上；事件 2004 19:15 列 PID 18916 = 36 GB |
| 19:09:32 | 同一腳本寫成 `nc.py` 再執行，19:10:35 被移到背景 | 同上 |
| 19:15:32 | 事件 2004 首次觸發：PID 23708 = 79 GB、PID 18916 = 36 GB | System log |
| 19:18:13 | 背景輸出檔寫入 traceback，最後一行 `MemoryError`，堆疊在 `unittest/mock.py:1193 _increment_mock_call → self.mock_calls.append` | `%LOCALAPPDATA%\Temp\claude\D--CKProject-CK-Missive\b37ae564-…\tasks\bwl260a2w.output` |
| 20:09 | PID 23708 仍占 162 GB（MemoryError 後釋放上百 GB 已換頁物件極慢） | 事件 2004 |
| 21:26:57 | 硬當 | 事件 41 |

## 機制

`del s.__iter__` 後 `set(s)` 走舊式序列協定：`MagicMock.__getitem__(0, 1, 2, …)` 永遠回傳新的 MagicMock、永不拋 `IndexError` ⇒ 無限迭代，每一步新建一個 MagicMock 並 append 一筆 `_Call` 到 `mock_calls`。成長速率約 1.4 GB/分鐘。

## 已落地的防線（host 層，非本 repo）

- `C:\Tools\pyguard\sitecustomize.py`：每個 python.exe 啟動時套 Job Object 每行程 16 GB 上限；同一段腳本在 4 GB 封頂下實測直接拋 MemoryError 結束。
- `~/.claude/rules/memory-safety.md`：所有 repo 的 Claude session 皆載入的硬規則。

## 本 repo 要辦的

1. 測試規範（`docs/DEVELOPMENT_STANDARDS.md` 或 `.claude/rules/`）加一條：負向測試**不得**用「刪 dunder 再呼叫內建協定」；要驗 `TypeError` 用 `MagicMock(spec=[...])` 或 `m.__iter__ = Mock(side_effect=TypeError)`。
2. 對話或腳本中一次性執行的 python 必須帶 `PYGUARD_MAX_GB=<小值>` 與真正的逾時（`subprocess.run(timeout=)` 或 PowerShell `Wait-Process -Timeout` + `Stop-Process`）；不得依賴 Git Bash `timeout`。
3. 登入 LESSONS_REGISTRY：「架構風險清單不能替代證據」——本事件前兩次誤判（vmmem、:5201 洩漏）都來自架構推論，定案靠的是 traceback、Prometheus RSS、排程器事件三份原始證據。

## 處理狀態（2026-09-09，CK_Missive）

| 交辦 | 狀態 |
|---|---|
| ① 測試規範加負向測試寫法限制 | ✅ `.claude/rules/testing.md`「負向測試的記憶體邊界」（常駐載入） |
| ② 一次性 python 的記憶體邊界與真正的逾時 | ✅ 同上；主機層 `~/.claude/rules/memory-safety.md` 全 repo 載入、pyguard 16 GB 封頂已落地（AaaP） |
| ③ 登入 LESSONS_REGISTRY | ✅ L150 |

**刻意不做成檢核**：違規形狀是「一段對話裡執行的指令」，不在 repo 檔案裡，靜態掃描抓不到；真正的護欄是 host 層封頂。
與 A127（WSL 核心層段錯誤）分家：本事件是 host 層 OOM，成因已定，不列入 A127 的未解故障。
