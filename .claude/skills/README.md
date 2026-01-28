# Claude Code Skills 架構說明

> **版本**: 1.0.0
> **建立日期**: 2026-01-28
> **用途**: 說明 Skills 分層設計理念與使用方式

---

## 分層架構概述

```
.claude/skills/
├── *.md                    # 頂層 Skills (專案特定)
├── README.md               # 本文件
├── superpowers/            # Superpowers 工作流 Skills
└── _shared/                # 共享 Skills 庫
    ├── shared/             # 通用共享 Skills
    ├── backend/            # 後端專用 Skills
    └── ai/                 # AI 相關 Skills
```

---

## 分層設計理念

### 頂層 Skills (`skills/*.md`)

**定位**: 專案特定的領域知識與規範

**特點**:
- 包含 CK_Missive 專案特定的業務邏輯
- 可覆蓋 `_shared` 中的同名 Skills
- 由 Claude Code 優先載入

**範例**:
- `document-management.md` - 公文管理領域知識
- `calendar-integration.md` - 行事曆整合規範
- `type-management.md` - SSOT 型別管理規範

### 共享 Skills (`skills/_shared/`)

**定位**: 通用的開發最佳實踐，可跨專案複用

**特點**:
- 不含專案特定的業務邏輯
- 透過 `settings.json` 的 `inherit` 載入
- 被頂層同名 Skills 覆蓋

**子目錄**:
| 目錄 | 說明 | 範例 |
|------|------|------|
| `shared/` | 通用開發實踐 | error-handling, security-patterns |
| `backend/` | 後端專用 | postgres-patterns, fastapi-patterns |
| `ai/` | AI 開發模式 | ai-architecture-patterns |

---

## 繼承機制

### settings.json 配置

```json
{
  "skills": {
    "inherit": [
      ".claude/skills/_shared/shared",
      ".claude/skills/_shared/backend"
    ]
  }
}
```

### 載入優先順序

1. 頂層 Skills (`skills/*.md`) - **最高優先**
2. 第一個 inherit 目錄
3. 第二個 inherit 目錄
4. ...依此類推

**覆蓋規則**: 同名 Skills，頂層版本覆蓋 `_shared` 版本

---

## 重複 Skills 說明

以下 Skills 在頂層和 `_shared` 中都存在，這是**有意的設計**：

| Skill | 頂層版本 | _shared 版本 | 說明 |
|-------|---------|-------------|------|
| `error-handling.md` | v1.0.0 | v1.0.0 | 頂層優先，可包含專案特定處理 |
| `security-hardening.md` | v1.0.0 | v1.0.0 | 頂層優先，可包含專案特定配置 |
| `type-management.md` | v1.1.0 | v1.1.0 | 頂層包含 SSOT 架構詳細說明 |

**設計原因**:
- 頂層版本可以針對專案需求進行客製化
- `_shared` 版本保持通用性，可複用於其他專案
- 繼承機制確保不會載入重複內容

---

## Skills 觸發機制

Skills 會根據關鍵字自動載入：

```markdown
> **觸發關鍵字**: 公文, document, 收文, 發文
```

當對話中出現觸發關鍵字時，對應的 Skill 會自動載入上下文。

---

## 新增 Skills 指引

### 新增專案特定 Skill

1. 在 `skills/` 目錄建立 `*.md` 檔案
2. 添加標準 header：
   ```markdown
   # Skill 名稱

   > **版本**: 1.0.0
   > **觸發關鍵字**: keyword1, keyword2
   > **適用範圍**: 說明
   ```
3. 更新 `CLAUDE.md` 的 Skills 清單

### 新增共享 Skill

1. 在 `skills/_shared/` 適當子目錄建立檔案
2. 使用 YAML frontmatter 格式：
   ```markdown
   ---
   name: skill-name
   description: 說明
   version: 1.0.0
   category: shared
   triggers:
     - keyword1
     - keyword2
   ---
   ```
3. 確保不包含專案特定內容

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `CLAUDE.md` | Skills 清單與觸發關鍵字 |
| `.claude/settings.json` | inherit 配置 |
| `docs/SYSTEM_OPTIMIZATION_REPORT.md` | Skills 分析報告 |
