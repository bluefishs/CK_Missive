---
title: L54 — 跨 repo install-template 套用 ≠ 落實 (audit 雙層揭發)
type: lesson
date: 2026-05-30
fqid: CK_Missive#L54
family: cross-repo-governance
related: [L31, L53]
---

# L54 — 套用 ≠ 落實

> **日期**：2026-05-30
> **觸發**：install-template 對 4 子專案套用完 → cross_repo_drift GREEN → 但實際各 repo 待 commit
> **規模**：1 commit / 1 fitness step / 1 audit script

---

## 揭發真因

`install-template-to.sh` 對 4 子專案套用：
- `cross_repo_template_drift_audit` (step 65) 顯示 4/4 GREEN（採用度 6/6）✓
- 但實際 4 子專案各有 staging changes 待 commit：

| Repo | 未 commit 檔 |
|---|---|
| CK_lvrland_Webmap | 38 |
| CK_PileMgmt | 26 |
| CK_Showcase | 1 |
| CK_KMapAdvisor | 59 |

**問題**：
- 若子專案 owner 沒進 repo `git commit + push`
- 下次 `git pull` 可能 conflict 或本批變動被覆蓋
- audit 顯示 GREEN 但實際是「working tree 有但 history 沒」

→ 「套用 ≠ 落實」

---

## 修法：fitness step 66

新增 `scripts/checks/cross_repo_uncommitted_audit.py`：
- 對 4 子專案跑 `git status --porcelain`
- 若有 staging changes → YELLOW + 列出樣本 5 檔
- 若全 committed → GREEN

接進 weekly fitness step 16:
```
run_step "16" "cross-repo uncommitted audit"
```

---

## 雙層 audit 完整檢核

從本批起，跨 repo 治理走**雙層 audit**：

| Layer | Audit | 檢核 |
|---|---|---|
| 1. 範本採用 | `cross_repo_template_drift_audit` step 65 | 檔案是否存在 |
| 2. 真實落實 | `cross_repo_uncommitted_audit` step 66 | 是否已 commit |

兩層皆 GREEN → 才算真正落實。

---

## 元洞察 — L31 ROI 公式延伸

L31「ROI = entities × usage_rate」假設 entity 已被「真實採用」。
但 L54 揭發：採用有 3 階段
1. **檔案存在** (file system)
2. **已 commit** (git history)
3. **被使用** (runtime caller)

每一層都要 audit。否則：
- 階段 1 達標但 2 未達 → silent rollback 風險
- 階段 2 達標但 3 未達 → dormant entity (L31 階段)

ROI 公式精確化：
```
真實 ROI = entities × commit_rate × usage_rate
```

---

## 修法資產

| 檔案 | 行為 | commit |
|---|---|---|
| `scripts/checks/cross_repo_uncommitted_audit.py` | NEW fitness step 66 | （本批）|
| `scripts/checks/run_fitness_weekly.sh` | 15→16 step | （本批）|
| `wiki/memory/lessons/L54_*.md` | NEW lesson | （本批）|

---

## 自我覆盤閉環 升級為 6 步

```
1. Owner trigger
2. Audit 揭發 (step 65 drift)
3. Dashboard 整合 (§9)
4. Dry-run 預覽報告
5. Owner approve → 執行 install-template
6. ★ Post-apply audit (step 66 uncommitted) ← NEW
```

第 6 步揭發「套用後是否落實」，閉環完整。

---

> **核心精神**：寫程式碼很容易，commit + push 才算落實。
> Audit 不只查 file system，還要查 git history。
> 「執行了」≠「持久化了」。
