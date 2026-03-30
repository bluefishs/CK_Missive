# CK_Missive v5.3.0 系統復盤與發展藍圖

> **日期**: 2026-03-29
> **版本**: v5.3.0
> **審查範圍**: 全棧架構、品質指標、技能樹、發展建議

---

## 一、專案統計快照

| 維度 | 數值 |
|------|------|
| 總提交數 | **546** (3月: 169, 佔 31%) |
| 前端檔案 (.ts/.tsx) | **891** |
| 後端檔案 (.py) | **517** |
| 測試檔案 | **356** (前端 218 + 後端 138) |
| DB 遷移 | **85** |
| AI 服務模組 | **77** |
| Agent 工具 | **78** (28 真工具 + 50 Skills) |
| KG 實體 | **4,398** 實體 / 5,693 關係 |
| 推理 Profile | **5** (vLLM/Groq/Ollama/NVIDIA/NIM) |

---

## 二、品質指標 (2026-03-29 重構後)

### 2.1 程式碼行數控管

| 類別 | 閾值 | 最大值 | 狀態 |
|------|------|--------|------|
| 後端 AI 服務 | 600L | 584L (tool_executor_search) | 合規 |
| 後端根服務 | 600L | 523L (audit_service) | 合規 |
| 前端頁面 | 500L | 499L (UnifiedFormDemoPage) | 臨界 |
| 前端元件 | 500L | 463L (KnowledgeGraph) | 合規 |
| 前端 Hooks | 500L | 364L (useDocumentCreateForm) | 合規 |

### 2.2 本次重構成果

| 檔案 | 前 | 後 | 降幅 |
|------|---|---|------|
| useDocumentCreateForm.ts | 676L | 364L | -46% |
| types/ai.ts | 1535L | 28L (barrel) | -98% |
| AIStatsPanel.tsx | 473L | 320L | -32% |
| DispatchWorkflowTab.tsx | 493L | 380L | -23% |
| ContractCaseDetailPage.tsx | 478L | 263L | -45% |

---

## 三、P2 議題現狀修正

### Layer 3 行為改變層 — 已運作

| 元件 | 行數 | 狀態 |
|------|------|------|
| agent_evolution_scheduler.py | 421L | 運作中 (50次/24h) |
| agent_learning_injector.py | 179L | 整合中 |
| agent_planner.py | 492L | 使用進化信號 |

### Inference Profiles — 就緒

5 個 Profile 配置完成，per-task routing 就緒。

### RolePermissionDetailPage — BLOCKED

前端 215L 完成，後端 API 未實作。

---

## 四、NemoClaw Agent 技能樹

```
核心推理 (5 模組) ⭐⭐⭐⭐⭐
├── ReAct Loop + 3-Layer Router + 意圖修正 + 答案合成 + 閒聊偵測

工具執行 (7 模組) ⭐⭐⭐⭐⭐
├── 搜尋/分析/PM-ERP/文件 工具 + Chain-of-Tools + 工具健康監控

學習進化 (6 模組) ⭐⭐⭐⭐
├── 模式學習 + 跨會話注入 + 自動進化 + 自我評分 + 種子 + 壓縮

知識圖譜 (9 模組) ⭐⭐⭐⭐
├── 7-Phase建構 + 正規化實體 + 入圖管線 + 合併 + 查詢 + CodeGraph + 聯邦

搜尋引擎 (5 模組) ⭐⭐⭐⭐
├── RAG v2.4 + 意圖解析 + 同義詞 + Reranker + 規則引擎

安全合規 (5 模組) ⭐⭐⭐⭐⭐
├── OWASP 掃描 + MFA + Tunnel Guard + CSRF/CORS + 雙 Token

多通道 (4 模組) ⭐⭐⭐
├── LINE Flex + Discord Embed + Telegram (via OpenClaw) + Channel Adapter

ERP 財務 (5 模組) ⭐⭐⭐
├── 費用報銷 + 帳本 + 彙總 + 電子發票 + 報價

數位分身 (5 模組) ⭐⭐⭐
├── 自我檔案 + 主動掃描 + 能力雷達 + 技能進化 + Trace 瀑布
```

---

## 五、發展建議

### 短期 (1-2 週)

1. **RolePermissionDetailPage 後端 API** — 3 端點 (list/update/check)
2. **CI 行數檢查** — >480L 頁面自動警告
3. **後端測試覆蓋率門檻** — 設定 70% 最低標準

### 中期 (1-2 月)

1. **Agent 自主報告** — 進化結果推送 LINE/Discord 週報
2. **RAG v3 多模態** — PDF 附件內容索引
3. **Graph-RAG 深度融合** — KG traversal 作為 RAG context
4. **表單智能預填** — 歷史模式預測

### 長期 (3-6 月)

1. **Multi-Agent 協作** — PM/ERP/Doc Agent 並行
2. **知識圖譜聯邦 v2** — 跨專案統一查詢
3. **離線推理** — vLLM 完全替代雲端

### 建議新增 Claude Code 指令

| 指令 | 用途 |
|------|------|
| `/health-dashboard` | 系統健康報告 (行數/測試/覆蓋率/遷移) |
| `/refactor-scan` | 掃描超閾值檔案 + 拆分建議 |
| `/agent-status` | Agent 進化狀態 + 工具健康 + 學習統計 |
| `/dep-audit` | 依賴安全性 + 過時版本掃描 |
| `/perf-baseline` | 效能基準記錄 (API/頁面/Agent 延遲) |

---

## 六、整體評級

| 維度 | 評級 |
|------|------|
| 模組化 | A+ |
| 型別安全 | A+ |
| 安全性 | A+ |
| 自動化護欄 | A+ |
| Agent 智能 | A |
| 效能 | A |
| 測試覆蓋 | A |
| 文件同步 | A |
| 多通道 | B+ |

**整體成熟度: A (企業級生產就緒)**
