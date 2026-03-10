---
name: skill-creator
description: >
  建立、修改、優化 Skills 的標準化工作流。基於 Anthropic 官方 skill-creator 規範。
  當使用者要建立新 skill、改善既有 skill、評估 skill 觸發準確度、或整理 skills
  目錄結構時使用。即使使用者只是提到「新增一個 skill」或「這個流程能不能變成 skill」
  也應觸發此 skill。
version: 1.0.0
category: project
triggers:
  - skill
  - skill-creator
  - 建立 skill
  - 新增 skill
  - 改善 skill
  - 優化觸發
  - SKILL.md
  - writing-skills
updated: '2026-03-09'
---

# Skill Creator — CK_Missive 專案版

基於 [Anthropic 官方 skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) 規範，
適配 CK_Missive 專案架構。

---

## 核心流程

1. **釐清意圖** — 使用者想讓 Claude 做什麼？何時觸發？
2. **撰寫草稿** — 遵循下方結構標準
3. **測試驗證** — 2-3 個測試提示，觀察實際行為
4. **迭代改善** — 根據測試回饋調整
5. **觸發優化** — 確保 description 能精準觸發

---

## Skill 檔案結構

### 單檔 Skill（大多數情況）

```
.claude/skills/
└── my-skill.md          # YAML frontmatter + Markdown 指令
```

### 多檔 Skill（需要腳本/參考文件）

```
.claude/skills/my-skill/
├── SKILL.md             # 主檔（必要）
├── scripts/             # 可執行腳本（確定性/重複性任務）
├── references/          # 參考文件（按需載入）
└── assets/              # 範本、圖示等靜態資源
```

### 漸進式載入（三層）

| 層級 | 載入時機 | 建議長度 |
|------|---------|---------|
| **Metadata** (name + description) | 永遠在 context 中 | ~100 字 |
| **SKILL.md body** | 觸發時載入 | <500 行 |
| **Bundled resources** | 按需讀取 | 不限 |

> 超過 500 行時，拆分為 `references/` 子目錄並在 SKILL.md 中標註何時讀取。

---

## YAML Frontmatter 標準

```yaml
---
name: skill-name              # 識別碼（kebab-case）
description: >                 # 觸發描述（關鍵！見下方指引）
  技能功能描述 + 觸發情境。要具體且「積極」，
  列出所有應觸發的關鍵字和情境。
version: 1.0.0                 # SemVer
category: project|backend|react|ai|shared
triggers:                      # 觸發關鍵字列表
  - keyword1
  - keyword2
updated: 'YYYY-MM-DD'
---
```

---

## Description 撰寫指引（最重要）

Description 是決定 Claude 是否調用 skill 的**主要機制**。

### 原則：積極觸發

Claude 傾向**不夠積極**地使用 skills。因此 description 應偏「推」：

```yaml
# ❌ 太被動
description: 處理 Unicode 正規化問題

# ✅ 積極且具體
description: >
  處理 Unicode/CJK 正規化、全形半形轉換、康熙部首相容字元問題。
  當遇到中文搜尋失敗、ILIKE 不匹配、字元比對異常、或需要處理
  UTF-8 編碼問題時使用。即使使用者沒有明確提到 Unicode，只要
  涉及中文字元處理或搜尋結果不符預期，都應觸發此 skill。
```

### Description 必須包含

1. **做什麼** — 技能的核心能力
2. **何時觸發** — 具體的使用者情境和關鍵字
3. **邊界案例** — 即使使用者沒明確提到，什麼情況也應觸發

---

## 撰寫風格指引

### 解釋「為什麼」，而非強制「MUST」

```markdown
# ❌ 生硬
ALWAYS use `json.dumps(ensure_ascii=False)` for Chinese content. NEVER use default serialization.

# ✅ 解釋原因
為了正確處理中文字元，使用 `json.dumps(ensure_ascii=False)`。
預設的 ASCII 編碼會將中文轉為 \uXXXX 跳脫序列，
在日誌和除錯時難以閱讀，也會增加儲存空間。
```

### 使用祈使句

```markdown
# ✅ 直接
檢查所有 ORM 欄位是否有 `comment` 參數。
使用 `select_related` 避免 N+1 查詢。
```

### 提供範例

```markdown
## 端點命名
**範例 1:**
Input: 取得使用者列表
Output: GET /api/v1/users/list

**範例 2:**
Input: 建立公文
Output: POST /api/v1/documents-enhanced/create
```

---

## 測試案例撰寫

建立 2-3 個測試提示，模擬真實使用者會說的話：

```markdown
### 測試案例
1. "我想在公文匯入時自動偵測機關名稱中的全形空格"
2. "為什麼搜尋「桃園市政府」找不到「桃園市政府工務局」？"
3. "幫我建一個新的 API endpoint 來查詢派工單統計"
```

> 好的測試案例是**具體的**，包含檔案路徑、欄位名稱、業務情境，而非抽象請求。

---

## CK_Missive 專案慣例

### 檔案位置

| 類型 | 位置 |
|------|------|
| 專案特定 skills | `.claude/skills/*.md` |
| 共享 skills | `.claude/skills/_shared/shared/` |
| React skills | `.claude/skills/_shared/react/` |
| Superpowers | `.claude/skills/_shared/shared/superpowers/` |

### 繼承機制

- 頂層 skill 覆蓋 `_shared` 同名 skill
- 配置於 `settings.json` 的 `skills.inherit` 陣列

### 新增 Skill 後必須更新

1. `.claude/skills/SKILLS_INVENTORY.md` — 版本追蹤
2. `.claude/rules/skills-inventory.md` — 觸發關鍵字清單
3. `CLAUDE.md` — 如涉及新頁面/路由/模組

### 驗證

```bash
node .claude/scripts/validate-all.cjs    # 格式驗證
node .claude/scripts/generate-index.cjs  # 索引重建
```

---

## 迭代改善原則

1. **通用化** — skill 會被使用千百次，不要過度擬合測試案例
2. **保持精簡** — 移除沒有用的指令，閱讀 transcript 找出浪費時間的部分
3. **提取重複工作** — 如果每次都要寫類似的腳本，打包進 `scripts/`
4. **解釋動機** — 讓模型理解「為什麼」比強制「ALWAYS/NEVER」更有效
