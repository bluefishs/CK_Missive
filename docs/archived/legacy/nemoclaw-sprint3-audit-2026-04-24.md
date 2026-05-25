# NemoClaw Sprint 3 — 程式碼引用審計報告（2026-04-24）

**Sprint 時程**：2026-05-06 ~ 05-12（計劃）— 提前執行
**審計類型**：盤點 + 分類 + 建議，**不改程式碼**
**關聯**：`docs/archive/nemoclaw-archival-checklist.md`（總 checklist）
**Blocker**：Hermes GO/NO-GO 決策（ADR-0030，2026-05-20 決策日）

---

## 審計結果統計（2026-04-24 掃描）

**backend/app/** 內 25 個檔案仍含 `nemoclaw|openclaw` 引用，**合計 73 處**（扣除 pyc）。

| 引用類型 | 檔案數 | 引用數 | 處理優先 |
|---|---|---|---|
| A. Federation 系統 legacy | 4 | 27 | **高**（需 Hermes GO）|
| B. Domain/Label 字串 | 8 | 12 | 低（批次 rename）|
| C. Re-export stubs | 2 | 5 | **Blocked on Hermes GO**（Sprint 4）|
| D. Docstring / Comment | 5 | 6 | 低（批次改，無風險）|
| E. 工具 / 邏輯引用 | 6 | 13 | 中（個案判斷）|
| **合計** | **25** | **63** | — |

---

## 類別 A — Federation 系統 legacy（27 處，阻塞中）

### A.1 `federation_discovery.py`（14 處）

```python
_REGISTRY_URL = os.getenv(
    "NEMOCLAW_REGISTRY_URL", "http://nemoclaw_tower:9000/api/registry"
)

_FALLBACK_REGISTRY = {
    "openclaw": { "name": "CK_OpenClaw", ... },
    ...
}
```

**說明**：跨 repo 聯邦服務發現 fallback — NemoClaw Registry + 靜態
"openclaw"/"lvrland"/"tunnel" fallback map。**ADR-0015 廢止 NemoClaw
Registry** 但 fallback map 仍被 proactive triggers 呼叫（見 pm2 log
`Federation fallback 'openclaw': ...`）。

**建議**：
1. 等 Hermes GO（ADR-0030）確認後，將 `_FALLBACK_REGISTRY` 改
   為以 `missive / lvrland / tunnel` 三個 domain 為主，刪 openclaw key
2. `NEMOCLAW_REGISTRY_URL` env 保留（向後相容），但預設可設為
   `http://hermes_gateway:8642/registry`
3. log 訊息「NemoClaw Registry unreachable」改為更中性如
   「Federation registry unreachable, using fallback」

### A.2 `federation_client.py`（8 處）/ `federation_delegation.py`（4 處）/ `__init__.py`（1 處）

同源 legacy — delegation 呼叫時的 upstream name 仍用 `openclaw` 作
identifier。重命名需配合跨 repo 契約（對 Missive 自身無影響）。

---

## 類別 B — Domain / Label 字串（12 處）

| 檔案 | 引用 | 內容推估 |
|---|---|---|
| `tool_definitions.py` | 5 | Tool label / description 含 OpenClaw 字樣 |
| `digital_twin_service.py` | 1 | Label |
| `provider_resolver.py` | 1 | Channel mapping `"openclaw": "haiku-openclaw"` |
| `shadow_logger.py` | 1 | Provider label constant |
| `token_usage_tracker.py` | 1 | Provider enum 值 |
| `schemas/ai/rag.py` | 1 | Enum 值 |
| `sender_context.py` | 1 | Channel enum |
| `line_flex_builder.py` | 1 | 文案 |

**建議**：
- `provider_resolver.py:25` `"openclaw": "haiku-openclaw"` 可刪（OpenClaw
  已廢，haiku provider 也退場 — 改為 Hermes 路徑）
- 其他 enum / label 字串做 grep + sed 批次 rename：openclaw → missive
- 驗證：跑 backend unit tests 確認無 enum mismatch

---

## 類別 C — Re-export Stubs（5 處，Blocked）

| 檔案 | 引用 | 內容 |
|---|---|---|
| `services/ai/misc/nemoclaw_agent.py` | 3 | class NemoClawAgent (re-export to MissiveAgent) |
| `services/ai/misc/__init__.py` | 2 | `from .nemoclaw_agent import NemoClawAgent` |

**狀態**：Hermes GO 後（ADR-0030，2026-05-20）才可刪除。
刪除前需確認所有 `from .nemoclaw_agent import` 皆遷移完畢。

grep 檢核命令：
```bash
grep -rn "nemoclaw_agent\|NemoClawAgent" backend/ --include="*.py" --include="*.md" | grep -v __pycache__
```

---

## 類別 D — Docstring / Comment（6 處）

| 檔案 | 內容 |
|---|---|
| `missive_agent.py` | Docstring 說明 renamed from NemoClawAgent |
| `skill_scanner.py` | Comment |
| `federation/__init__.py` | Module docstring |
| `__init__.py` (ai endpoints) | Comment |

**建議**：純文件性 rename，**可立即執行**，無風險。
但為避免 sprint 3 scope creep，**本次不改**，留待 Sprint 4 一併做。

---

## 類別 E — 工具 / 邏輯引用（13 處）

| 檔案 | 引用 | 類型 |
|---|---|---|
| `skill_evolution_service.py` | 4 | 可能含 skill ref 或 token usage label |
| `digital_twin.py` endpoint | 4 | Endpoint mapping / response label |
| `agent_query_sync.py` | 3 | Provider label |
| `proactive_triggers.py` | 1 | Channel enum |
| `tender_subscription_scheduler.py` | 1 | 推播通道 |
| `agent_capability.py` | 1 | 已 renamed from nemoclaw（保留註記） |

**建議**：逐檔 code review 確認具體引用性質；**保留於 Sprint 4**。

---

## 推進建議

### 立即可做（本輪不做，降低 scope drift）
- 無

### Hermes GO 後（Sprint 4，2026-05-20+）
- 類別 A federation legacy 改名
- 類別 B enum/label 批次 rename
- 類別 C re-export stub 刪除
- 類別 D/E docstring/comment 批次改

### Repo archive（Sprint 5，2026-05-26）
- GitHub 端 archive CK_NemoClaw + CK_OpenClaw repo
- 各放 `ARCHIVED.md`

---

## 驗收條件（2026-05-26，同 checklist）

- [ ] `grep -rn "nemoclaw\|openclaw" backend/app/ --include="*.py"` 只剩 test
- [ ] `grep -rn "nemoclaw\|openclaw" frontend/src/` 僅剩註解
- [ ] federation log 訊息不再含 "NemoClaw" / "openclaw"
- [ ] provider label 全 missive / hermes

---

## 本次審計結論

**Sprint 3 升級為「審計已完成，執行延後至 Hermes GO 後」**：

1. 73 處引用分 5 類定位完畢
2. 每類處理優先級明確（A/C 阻塞、B/D 低風險、E 需個案）
3. 驗收腳本已就緒（見 checklist §驗收條件）
4. 預期 Sprint 4 工期：1-2 days（批次 sed + test + commit）

**風險提示**：
- 若 Hermes NO-GO，類別 A federation 改名會變得微妙（NemoClaw 仍在 run）
- 類別 B 的 `provider_resolver.py` 若 `"openclaw": "haiku-openclaw"` 仍
  被呼叫，刪除會 break shadow_logger 老 traces
- 建議 Sprint 4 前先跑 `shadow-baseline-report` 確認 openclaw channel
  已無新流量

---

_本審計報告由 CK_Missive session 2026-04-24 產出，作為 NemoClaw
archival checklist Sprint 3 的成果文件。_
