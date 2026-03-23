# Document Release — 發布後文件同步

> 靈感來源: [gstack/document-release](https://github.com/garrytan/gstack) — 確保文件與程式碼同步
> **版本**: 1.0.0

發布後自動檢查並更新所有需要同步的系統文件，防止文件與程式碼脫節。

## 使用方式

```
/document-release              # 完整文件同步檢查
/document-release check        # 僅檢查，不修改（預設）
/document-release fix          # 檢查並自動修復
/document-release changelog    # 僅更新 CHANGELOG
```

## Phase 1: 變更偵測

```bash
# 最近一次發布以來的變更
git log --since="$(git log --tags --simplify-by-decoration --pretty='format:%ai' -1)" --name-only --format="" | sort -u

# 或比對最近 N 個 commits
git log -20 --name-only --format="" | sort -u
```

**識別**：
- 新增的檔案（需要加入架構文件）
- 修改的服務/端點（需要更新 API 文件）
- 新增的路由（需要同步 skills-inventory）
- 新增的 hooks/commands（需要同步 hooks-guide）

## Phase 2: 文件同步檢查清單

### A. 架構文件 (`architecture.md`)

| 檢查項 | 偵測方式 |
|--------|---------|
| 新增 ORM model | `git diff --name-only` 含 `models/` 新檔案 |
| 新增 Service | `git diff --name-only` 含 `services/` 新檔案 |
| 新增 Repository | `git diff --name-only` 含 `repositories/` 新檔案 |
| 新增 API endpoint | `git diff --name-only` 含 `endpoints/` 新檔案 |
| 新增前端頁面 | `git diff --name-only` 含 `pages/` 新檔案 |
| 新增前端 Hook | `git diff --name-only` 含 `hooks/` 新檔案 |

**動作**: 比對 `.claude/rules/architecture.md` 中的結構樹，補充缺失項目。

### B. Skills Inventory (`skills-inventory.md`)

| 檢查項 | 偵測方式 |
|--------|---------|
| 新增 Command | `ls .claude/commands/*.md` vs skills-inventory 列表 |
| 新增 Skill | `ls .claude/skills/*.md` vs skills-inventory 列表 |
| 新增 Agent | `ls .claude/agents/*.md` vs skills-inventory 列表 |
| 新增 Hook | `settings.json` hooks vs hooks-guide 列表 |

**動作**: 自動比對並列出缺失項目，`fix` 模式下自動補充。

### C. Hooks Guide (`hooks-guide.md`)

| 檢查項 | 偵測方式 |
|--------|---------|
| 新增 PreToolUse hook | `settings.json` PreToolUse 區段 |
| 新增 PostToolUse hook | `settings.json` PostToolUse 區段 |
| 新增 git hook | `.git/hooks/` 目錄 |

### D. CHANGELOG (`CHANGELOG.md`)

| 檢查項 | 偵測方式 |
|--------|---------|
| 版本號更新 | `CLAUDE.md` 版本 vs CHANGELOG 最新版本 |
| 新功能記錄 | `git log --grep="feat:"` 是否都有記錄 |
| 修復記錄 | `git log --grep="fix:"` 是否都有記錄 |

### E. MANDATORY_CHECKLIST (`MANDATORY_CHECKLIST.md`)

| 檢查項 | 偵測方式 |
|--------|---------|
| 新增模組 | 是否需要新增檢查清單項目 |
| 版本號 | 檢查清單版本是否已更新 |

### F. 型別文件 (前端)

| 檢查項 | 偵測方式 |
|--------|---------|
| 新增型別 | `types/` 下新檔案是否在 `index.ts` 中匯出 |
| 新增 API | `api/` 下新檔案是否在 `endpoints.ts` 中有常數 |

## Phase 3: 報告輸出

```markdown
# Document Release Report — YYYY-MM-DD

## 同步狀態

| 文件 | 狀態 | 缺失項目 |
|------|------|---------|
| architecture.md | ⚠️ 需更新 | 新增 2 services, 1 endpoint |
| skills-inventory.md | ✅ 同步 | — |
| hooks-guide.md | ⚠️ 需更新 | 新增 2 hooks |
| CHANGELOG.md | ❌ 需更新 | 缺少 v5.1.16 記錄 |
| MANDATORY_CHECKLIST.md | ✅ 同步 | — |

## 建議動作

1. [具體修改建議]
2. [建議]

## Auto-Fix 結果 (若使用 --fix)
[已自動修復的項目清單]
```

## 搭配使用

- `/ship` 完成後 → `/document-release fix` 確保文件同步
- `/retro` 時 → 檢查文件更新是否跟上程式碼變更
- 版本發布前 → `/document-release check` 最終驗證
