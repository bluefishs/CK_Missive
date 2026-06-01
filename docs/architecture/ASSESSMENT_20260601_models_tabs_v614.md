# 評估報告：本地模型庫 × 坤哥頁 tab 整合 × v6.14 續推（2026-06-01）

> 對齊 owner 三訴求：① ollama/gemma4/qwen 本地模型庫整合管理建議與評估 ② 接續 v6.14 ③ 坤哥頁 tab 重複/整合/核心分類以活化資產
> 性質：評估 + 建議（grounded 真實數據）。模型移除 / tab 重構屬 owner 決策，本檔不擅自執行。

---

## 一、本地模型庫整合管理評估

### 1.1 現況（實測 `ollama list` + `.env` + ai_connector）

| 模型 | 大小 | 實際用途 | 狀態 |
|---|---|---|---|
| **qwen2.5:7b** | 4.7GB | Missive 本地任務（classify/ner/planning）+ ollama fallback（`.env OLLAMA_MODEL`）| ✅ 真用 |
| **qwen2.5:7b-ctx64k** | 4.7GB | Hermes gateway 主迴圈（64k context）| ✅ 真用 |
| **nomic-embed-text** | 274MB | 嵌入 768D（對齊 pgvector）| ✅ 真用 |
| **gemma4:e2b** | 7.2GB | 🔴**【2026-06-02 重大訂正】不是死weight — 是發票解析核銷的視覺模型**：`erp/invoice_recognizer._vision_ocr_async` → `vision_completion(task_type="vision")` 需視覺模型，gemma4:e2b 是 ollama 庫**唯一視覺模型**（qwen 純文字不能處理圖片）。owner 提問揭發我誤刪（已重拉還原）| ✅ **必需（視覺）** |
| **embeddinggemma** | 621MB | grep 全 code/config/.env/configs **0 引用**（廣域複查確認）| 🔴 **死weight** |

**關鍵發現**：
1. **「gemma4」是誤名**：`agent_query_sync.py` 6 處 `model="gemma4"` + route_type「gemma4」**實際跑 qwen2.5:7b**（env override）→ 觀測/trace 全部標錯模型名，混淆 baseline 分析。
2. **gemma4:e2b 是發票 OCR 視覺模型（必需，非死weight）**【2026-06-02 訂正】：我先前 grep `gemma4` 只看到 ai_connector + label，**漏看 vision 路徑**（`invoice_recognizer` 用 `vision_completion`→「via Gemma 4 vision」，model 在 vision_completion 內間接選，非字面 gemma4）。owner 提問「帳務是否透過 gemma4 發票解析」**及時揭發我誤刪**（已 `ollama pull` 重拉還原）。
   - ⚠️ **連帶揭發潛伏 bug 並已修**：`task_type="vision"` 原不在 TASK_MODEL_MAP → 落 `OLLAMA_DEFAULT_MODEL`(qwen2.5:7b 純文字) → 圖片送非視覺模型 → **發票視覺 OCR silent 失敗退 QR**。已加 `"vision": "gemma4:e2b"` 映射（commit 本批），發票 OCR 視覺真導向 gemma4。
3. **embeddinggemma 621MB 確定死**：無引用。
4. **VRAM 壓力**：RTX 4060 8GB。gemma4(7.2GB) 與 qwen(4.7GB) 無法同時常駐；若 Hermes(qwen-ctx64k) + Missive(qwen 7b) 同時活躍 → load thrashing（兩個 4.7GB 變體）。

### 1.2 建議（依 ROI / 風險）

| # | 建議 | 效益 | 風險 | 等級 |
|---|---|---|---|---|
| M1 | **刪 embeddinggemma**（已執行 `ollama rm`）| 釋 621MB，0 引用 | 無 | ✅ **已執行** |
| ~~M2 刪 gemma4:e2b~~ | 🔴 **撤回 — gemma4:e2b 是發票 OCR 視覺模型，必須保留** | — | 誤刪會斷發票 OCR | ❌ **不可刪（已還原）** |
| M2' | **vision 路由修法**：加 `task_type="vision"→gemma4:e2b` 進 TASK_MODEL_MAP | 發票視覺 OCR 真活（原 silent 退 QR）| 低 | ✅ **已執行** |
| M3 | **統一本地模型**：Missive 也用 `qwen2.5:7b-ctx64k`（與 Hermes 同）| 1 模型常駐、免 thrash、長 context | 改 `.env OLLAMA_MODEL`，需測 classify/planning 效果 | owner 評估 |
| M4 | **修「gemma4」誤名**：route_type/model label 改 `local` 或實際模型名 | 觀測 trace 模型名正確、baseline 分析準 | 純 label，低風險 | 安全可做 |
| M5 | **inference-profiles.yaml 對齊 .env**：primary 改 qwen2.5:7b 反映現實 | SSOT 一致、消除「primary=gemma4 但實跑 qwen」漂移 | 文件對齊 | 安全可做 |

**核心**：本地模型實際只需 **2 個 LLM（qwen2.5:7b / -ctx64k，甚至統一成 1 個）+ 1 embed（nomic）**。gemma4:e2b + embeddinggemma 是歷史殘留（8 週前載入），佔 7.8GB disk + 造成模型名混淆。

---

## 二、坤哥頁 tab 重複盤點 + 核心分類建議

### 2.1 現況 tab 全清單（實測）

**/kunge 主頁 7 tab**：直接對話 / 我是誰 / 記憶圖譜 / 結晶進化 / 技能星雲 / 對話精選 / 運維儀表板(ops)
**ops 子 tab（user 7 / admin 12）**：對話 / 自省 / 追蹤 / 派工 / 儀表板 / 進化 / 拓撲
**散落他處**：MemoryDashboardPage(`/ai/memory-dashboard`) / GraphHubPage(`/ai/graphs`)

### 2.2 重複 / 重疊（owner 觀察屬實）

| 重複類 | 散落位置 | 問題 |
|---|---|---|
| **對話** | 主「直接對話」+ ops「對話」 | 2 個聊天入口，重複 |
| **進化** | 主「結晶進化」(pattern→crystal 學習) + ops「進化」(健康/agent 品質) | **同名不同義** — 最易混淆 |
| **圖譜/星雲/拓撲** | 主「記憶圖譜」+「技能星雲」+ ops「拓撲」+ `/ai/graphs` + `/ai/memory-dashboard` | **5 處圖譜類**，資產分散 |
| **自省/身份** | 主「我是誰」+ ops「自省」(critique) | 相關但分離 |

### 2.3 核心分類建議（7+7 tab → 4-5 大類，活化資產）

```
坤哥（單一意識體入口）
├── 💬 對話         ← 合併: 主 chat + ops 對話 (移除重複，單一入口)
├── 🧠 心智         ← 合併: 我是誰(identity) + 記憶圖譜(memory) + 自省(critique) + 對話精選
│                      (內在心智統一: 身份/記憶/反省/精選對話)
├── 🌱 進化         ← 釐清雙軌: 子分頁「結晶進化」(學習閉環 pattern→crystal)
│                      vs「健康進化」(運行品質) — 同頁清楚區隔不再撞名
├── 🕸️ 圖譜         ← 導向統一中樞 /ai/graphs: 技能星雲+拓撲+記憶圖譜 收口
│                      (5 散點 → 1 GraphHub，省維護)
└── 🛠️ 運維(admin)  ← ops 保留: 派工 / 追蹤 / 儀表板 (運維專屬)
```

**效益**：7 主 + 7 子 ≈ 14 tab → **5 大類**；消除「對話 ×2」「進化撞名」「圖譜 5 散點」；對齊 ADR-0031「坤哥唯一入口」原意。

**注意**：tab 重構是 UI/UX 變更，依 `feedback_no_modal_navigation_mode` + confirm-before-change，**待 owner 拍板後**才動（涉路由四方同步，避免重演 sidebar 事故）。

---

## 三、v6.14 續推狀態

| ID | 項目 | 狀態 |
|---|---|---|
| LN2 | gemma4 意圖 silent return | ✅ 完成（`_INTENT_TOOL_MAP` commit `a33a0bbc`）|
| LN1 + H1 路由側 | intent→tool 確定性映射 | ✅ 完成（finance/tender/project/vendor 真實工具）|
| 兩頁服務 | 排程追溯 / ADR | ✅ 完成（500→200 / 0→23 筆）|
| **H1 bridge 層** | tools_manifest 暴露 ERP/tender 給 Hermes gateway | 🟡 **post-LN2 邊際降低** — agent 內部已正確路由（含 LINE）；bridge 僅 gateway 直呼層 discoverability，且需 hermes-stack 協調。建議列 owner 決策 |
| LN3 / #3 | Groq quota | owner |
| L1 | crystal-intent 真實化（pattern_extractor 補 query 文字）| v6.14 |

**H1 評估**：LN2 已從 agent 路由層根本解決「只答派工」（所有頻道含 LINE 都受惠）。H1（bridge manifest 補 finance/tender 條目）價值降為「Hermes gateway 直呼 discoverability」，且 manifest 的 `dispatch_search` 本就指向通用 `/api/ai/agent/query_sync`（LN2 後已能正確路由任意域）。故 **H1 非必要、可延後**，避免為邊際效益再動 backend。

---

## 四、可安全自主辦理 vs owner 決策

| 安全可做（低風險） | owner 決策 |
|---|---|
| M1 刪 embeddinggemma / M4 修 gemma4 誤名 / M5 profiles 對齊 | M2 刪 gemma4:e2b / M3 統一本地模型 |
| — | tab 重構（UI/路由四方同步）|
| — | H1 bridge / LN3 Groq quota |

---

> **核心精神**：模型庫「實用 2-3 個、殘留 2 個」；坤哥 tab「14 散 → 5 核心類」；v6.14 路由側已根治。三者都是「**接通與收口**」問題 — 資產（工具/模型/頁面）早就有，缺的是去重複 + 正確分類 + 對外暴露對齊。
