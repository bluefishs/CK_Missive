"""Governance Integrated Dashboard Generator (v6.12, 2026-05-30)

Owner 問題: 每次詢問都有缺漏，如何完善規範+專案現況+覆盤整合效應

解法: 把 194 個治理文件散落 5 處的問題用「自動生 SSOT dashboard」收口
- 4 類規範 (ADR / lesson / SOP / fitness) 統一表格
- 現況真活 metric snapshot
- 最近 N session 覆盤積累
- 漂移看板 (audit 結果統一)
- 進化進度 (B 方案 / v6.12 4 原則 / Hermes baseline)

輸出: docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md
排程: daily 06:00 cron 自動 regenerate + LINE 推
session 啟動 hook 可直接讀
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "architecture" / "GOVERNANCE_INTEGRATED_DASHBOARD.md"

# L52/L57 family: 此腳本由「in-container scheduler (cwd=/app)」與「host 手動」兩種情境執行。
# 容器內後端套件在 /app/app、logs 在 /app/logs；host 在 backend/app、backend/logs。
# 寫死 host 佈局會讓 §5(facade caller)/§9.6(cron events) 在 cron 情境 silent 落空，
# 形成「治理儀表板自身的整合缺口」（正是 dashboard 設計初衷要消滅的問題）。


def _first_dir(*cands: "Path") -> "Path":
    for c in cands:
        if c.exists():
            return c
    return cands[0]


PKG_DIR = _first_dir(ROOT / "backend" / "app", ROOT / "app")   # 後端 python 套件根
LOGS_DIR = _first_dir(ROOT / "backend" / "logs", ROOT / "logs")  # cron_events.jsonl 所在
IS_GIT_REPO = (ROOT / ".git").exists()  # 容器內非 git repo → §3 commits 無法填


def fetch_metrics() -> dict[str, float]:
    out: dict[str, float] = {}
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=8) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return out
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if any(line.startswith(p) for p in (
            "governance_", "scheduler_job_",  # v6.13: 抓全部 scheduler_job_* (含 age/success/failure)
            "kg_entities_total", "wiki_pages_total",
            "v7_", "shadow_baseline_",
            "memory_diary_days_total", "memory_crystals_total",
        )):
            try:
                # v6.12 修法 (2026-05-30): 完整 metric key 保留 labels
                # 用空白分隔 metric_with_labels 與 value
                parts = line.rsplit(" ", 1)
                key = parts[0]  # 含 labels: shadow_baseline_latency_p95_ms{provider="gemma-local"}
                val = float(parts[1])
                if key not in out:
                    out[key] = val
            except (ValueError, IndexError):
                continue
    return out


def count_adrs() -> dict[str, int]:
    counts: dict[str, int] = {}
    adr_dir = ROOT / "docs" / "adr"
    if not adr_dir.is_dir():
        return counts
    for f in adr_dir.rglob("*.md"):
        if f.name in ("README.md", "TEMPLATE.md"):
            continue
        if "archived" in f.parts:
            counts["archived"] = counts.get("archived", 0) + 1
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")[:2000]
        except Exception:
            continue
        # 與 adr_lifecycle_check.py 同 regex (接受 blockquote > **狀態**:)
        m = re.search(
            r"^(?:\s*[-*>])?\s*\*\*(?:狀態|Status|status)\*\*\s*[:：]\s*"
            r"\*{0,2}`?([A-Za-z_]+)`?\*{0,2}",
            text, re.MULTILINE,
        )
        st = m.group(1).lower() if m else "unknown"
        # 視 proposed / proposal / accepted 為 active
        if st in ("accepted", "proposed", "proposal", "active"):
            counts["active"] = counts.get("active", 0) + 1
        elif st in ("superseded", "removed", "rejected", "deprecated"):
            counts[st] = counts.get(st, 0) + 1
        else:
            counts["unknown"] = counts.get("unknown", 0) + 1
    return counts


def list_lessons() -> list[tuple[str, str]]:
    """回 [(L編號, 標題)]

    SSOT = docs/architecture/LESSONS_REGISTRY.md（容器內可見），解析其 `## L<n> — <title>` 區段。
    L67 同型修（2026-06-11）：原讀空目錄 wiki/memory/lessons/ → Lessons 永遠 0；
    真實 lessons 集中在 LESSONS_REGISTRY.md（57+ 條）。保留舊目錄為 fallback。
    """
    out: list[tuple[str, str]] = []
    registry = ROOT / "docs" / "architecture" / "LESSONS_REGISTRY.md"
    if registry.is_file():
        text = registry.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^##\s+(L\d+)\s*[—\-:]\s*(.+?)\s*$", text, re.MULTILINE):
            out.append((m.group(1), m.group(2).strip()))
        if out:
            return out
    # fallback：舊式單檔目錄（多數環境為空）
    d = ROOT / "wiki" / "memory" / "lessons"
    if d.is_dir():
        for f in sorted(d.glob("L*.md")):
            mm = re.match(r"^(L\d+)_(.+)\.md$", f.name)
            if mm:
                out.append((mm.group(1), mm.group(2).replace("_", " ")))
    return out


def recent_commits(n: int = 8) -> list[str]:
    """git log 最近 n 個"""
    import subprocess
    import os
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        # text=False + decode 'utf-8' errors='replace' 解 cp950 阻擋
        r = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%h %s"],
            cwd=str(ROOT), capture_output=True, timeout=10, env=env,
        )
        if r.returncode == 0:
            return r.stdout.decode("utf-8", errors="replace").strip().splitlines()
    except Exception:
        pass
    return []


def list_recent_sessions(n: int = 5) -> list[str]:
    """memory/ 內最近 session_2026*.md"""
    mem = Path.home() / ".claude/projects/D--CKProject-CK-Missive/memory"
    if not mem.is_dir():
        return []
    sessions = sorted(mem.glob("session_2026*.md"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
    return [s.name for s in sessions[:n]]


def _existing_section_body(section_header: str) -> list[str]:
    """L73 非 clobber：cron 在容器內（無 git / 無 ~/.claude memory）regenerate 時，
    保留前次 host 寫入的實值區段（§3 commits / §4 sessions），避免每日把實值
    洗成「容器內無法取」placeholder（治理儀表板自身的 silent 回退）。

    section_header 例：「## 3.」。回傳該 section 與下一個 `## ` 之間的內文行。
    """
    if not OUT.exists():
        return []
    try:
        text = OUT.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    body: list[str] = []
    capturing = False
    for ln in text.splitlines():
        if ln.startswith("## "):
            if capturing:
                break
            capturing = ln.strip().startswith(section_header)
            continue
        if capturing:
            body.append(ln)
    # 剝除前次 append 的 clobber 保留註記，避免每日容器 regenerate 累加重複行
    # （host 端上次 regenerate 後，容器 cron 每日跑一次即多一行 → 一個月累積數十行）
    _note_markers = ("L73 非 clobber", "容器內無 git", "容器內無 ~/.claude memory")
    body = [ln for ln in body if not any(mk in ln for mk in _note_markers)]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    return body


def _is_placeholder(body: list[str]) -> bool:
    """前次區段是否本身就是 placeholder（無實值可保留）。"""
    return (not body) or any(("⚪" in b) or ("⚠️ git log" in b) or ("⚠ git log" in b) for b in body)


def check_cross_repo_drift() -> list[tuple[str, int, int, str]]:
    """v6.12 整合: 跨 repo 範本漂移摘要 (對齊 cross_repo_template_drift_audit step 65)"""
    targets = ["CK_lvrland_Webmap", "CK_PileMgmt", "CK_Showcase", "CK_KMapAdvisor"]
    assets = [
        ".claude/rules/cross-file-ssot-governance.md",
        "scripts/checks/paths_compose_mount_audit.py",
        "scripts/checks/container_env_alignment_audit.py",
        "scripts/checks/container_image_freshness_check.py",
        "scripts/checks/run_fitness_daily.sh",
        "scripts/checks/generate_governance_dashboard.py",
    ]
    out: list[tuple[str, int, int, str]] = []
    for tgt in targets:
        tgt_root = ROOT.parent / tgt
        if not tgt_root.is_dir():
            out.append((tgt, 0, len(assets), "⚪ N/A"))
            continue
        present = sum(1 for a in assets if (tgt_root / a).exists())
        if present == 0:
            verdict = "🔴 RED-zero"
        elif present >= len(assets) - 1:
            verdict = "🟢 GREEN"
        elif present >= len(assets) // 2:
            verdict = "🟡 YELLOW"
        else:
            verdict = "🔴 RED"
        out.append((tgt, present, len(assets), verdict))
    return out


def check_b_plan_progress() -> dict:
    """B 方案 60 天 trial 進度"""
    facades_dir = PKG_DIR / "services" / "contracts" / "facades"
    if not facades_dir.is_dir():
        return {}
    existing = [f.stem for f in facades_dir.glob("*.py") if f.name != "__init__.py"]
    # 數 caller
    import subprocess
    callers = {}
    for name in existing:
        fcap = name.title() + "Facade"
        if fcap == "AiFacade": fcap = "AIFacade"
        try:
            r = subprocess.run(
                ["grep", "-rln",
                 f"from app.services.contracts.facades.*import.*{fcap}",
                 str(PKG_DIR), "--include=*.py"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=10,
            )
            files = [f for f in r.stdout.splitlines()
                     if "contracts/" not in f and "__pycache__" not in f]
            callers[fcap] = len(files)
        except Exception:
            callers[fcap] = -1
    return callers


def render() -> str:
    metrics = fetch_metrics()
    adr_counts = count_adrs()
    lessons = list_lessons()
    commits = recent_commits(8)
    sessions = list_recent_sessions(5)
    b_progress = check_b_plan_progress()

    lines: list[str] = []
    a = lines.append

    a("# Governance Integrated Dashboard — 規範 + 現況 + 覆盤 整合 SSOT")
    a("")
    a(f"> **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    a("> **Owner 問題**: 每次詢問都有缺漏，需整合 5 處治理文件 (ADR/lesson/SOP/fitness/architecture)")
    a("> **解法**: 此 dashboard 由 cron 06:00 自動 regenerate，session 啟動讀此檔取完整快照")
    a("> **生成器**: `scripts/checks/generate_governance_dashboard.py`")
    a("")
    a("---")
    a("")

    # ── 1 規範 ──
    a("## 1. 規範清單盤點")
    a("")
    a("| 類別 | 數量 | 位置 |")
    a("|---|---|---|")
    active_adr = adr_counts.get("active", 0)
    archived_adr = adr_counts.get("archived", 0)
    a(f"| ADR | active={active_adr} / archived={archived_adr} | `docs/adr/` |")
    a(f"| Lessons | {len(lessons)} | `docs/architecture/LESSONS_REGISTRY.md` |")
    rules_count = len(list((ROOT / ".claude" / "rules").glob("*.md")))
    # SOPs 在 .claude/rules/（dev-time 目錄，未掛載入 backend 容器 → cron 產出時為 0）
    sop_note = "" if rules_count else "（容器未掛載 .claude/，host 端執行才計數）"
    a(f"| SOPs | {rules_count} | `.claude/rules/*.md`{sop_note} |")
    fitness_count = len(list((ROOT / "scripts" / "checks").glob("*.py")))
    a(f"| Fitness checks | {fitness_count} | `scripts/checks/*.py` |")
    arch_count = len(list((ROOT / "docs" / "architecture").glob("*.md")))
    a(f"| Architecture docs | {arch_count} | `docs/architecture/*.md` |")
    a(f"| **Total** | **{active_adr + archived_adr + len(lessons) + rules_count + fitness_count + arch_count}** | 5 處散落 |")
    a("")

    # ── 2 現況真活 metric ──
    a("## 2. 現況真活 metric (從 /metrics 即時抓)")
    a("")
    a("```")
    for k in sorted(metrics.keys()):
        a(f"  {k:50} {metrics[k]:>12.1f}")
    a("```")
    a("")
    a("> ℹ️ **metric 範疇註記（消 SSOT 誤判）**：`wiki_pages_total` = 全 `wiki/**/*.md` 檔數（含 memory/diary/patterns）；")
    a("> self-retrospective 報告的「wiki 頁數」= LLM wiki 頁（`wiki/` 前兩層）。兩者同名不同範疇，差異屬定義非漂移。")
    a("> `v7_soul_drift_lines = -1` 為 sentinel（容器內 writer 盲視 host `CK_AaaP`，L73）；真值須 host fitness 寫入。")
    a("")

    # ── 3 最近 8 commits ──
    a("## 3. 最近 8 commits (進化執行軌跡)")
    a("")
    if commits:
        for c in commits:
            a(f"- `{c}`")
    else:
        prev = _existing_section_body("## 3.")
        if not _is_placeholder(prev):
            for ln in prev:
                a(ln)
            a("")
            a("> ℹ️ 容器內無 git；以上為前次 host regenerate 保留值（L73 非 clobber，避免 silent 回退空白）。")
        elif not IS_GIT_REPO:
            a("> ⚪ 容器內執行（非 git repo）無法取 commit 歷史；於 host 端手動 regenerate 可填。")
        else:
            a("> ⚠️ git log 取回為空。")
    a("")

    # ── 4 最近 session 覆盤 ──
    a("## 4. 最近 5 session 覆盤 (memory/)")
    a("")
    if sessions:
        for s in sessions:
            a(f"- {s}")
    else:
        prev = _existing_section_body("## 4.")
        if not _is_placeholder(prev):
            for ln in prev:
                a(ln)
            a("")
            a("> ℹ️ 容器內無 ~/.claude memory；以上為前次 host regenerate 保留值（L73 非 clobber）。")
        else:
            a("> ⚪ 容器內無 ~/.claude memory 存取；於 host 端手動 regenerate 可填。")
    a("")

    # ── 5 B 方案 60 天 trial 進度 ──
    a("## 5. Facade B 方案 60 天 trial 進度 (重評日 2026-07-30)")
    a("")
    a("| Facade | 現 caller | 60 天目標 | 達標 |")
    a("|---|---|---|---|")
    for f_name, target in (("IntegrationFacade", 5), ("MemoryFacade", 5), ("WikiFacade", 3)):
        cur = b_progress.get(f_name, "?")
        ok = "✅" if isinstance(cur, int) and cur >= target else "🟡" if isinstance(cur, int) and cur >= 3 else "🔴"
        a(f"| {f_name} | {cur} | ≥{target} | {ok} |")
    a("")

    # ── 6 lesson 索引 ──
    a("## 6. Lesson 索引 (L4x family 為主)")
    a("")
    for L_id, title in lessons:
        a(f"- **{L_id}** — {title}")
    a("")

    # ── 7 v6.12 進化 4 原則狀態 ──
    a("## 7. v6.12 進化 4 原則狀態")
    a("")
    a("| # | 原則 | 落地證據 | 狀態 |")
    a("|---|---|---|---|")
    a("| #1 | 修法掃全範圍 audit | fitness step 60 container image freshness | ✅ |")
    a("| #2 | observability 分層 forcing | Tier 1 daily 7 + Tier 2 weekly 14 + Tier 3 monthly | ✅ |")
    a("| #3 | 治理本身 metric 化 | 7 governance_* gauge + scheduler_job_* | ✅ |")
    a("| #4 | 元覆盤 cron | daily_self_retrospective 7 aspects (06:30) | ✅ |")
    a("")

    # ── 8 漂移看板 ──
    a("## 8. 漂移看板 (audit 結果統一)")
    a("")
    issues = []
    fitness_age = metrics.get("governance_fitness_report_freshness_hours", -1)
    if fitness_age > 48:
        issues.append(f"⚠ Pipeline report 距今 {fitness_age:.0f}h > 48h")
    pipeline_red = metrics.get("governance_pipeline_red_consecutive_days", 0)
    if pipeline_red > 3:
        issues.append(f"⚠ Pipeline 連續 {pipeline_red:.0f} 天 RED (> 3 天門檻)")
    wiki_age = metrics.get("governance_wiki_freshness_hours", -1)
    if wiki_age > 72:
        issues.append(f"⚠ Wiki 距今 {wiki_age:.0f}h > 72h 未更新")
    if not issues:
        a("✓ 所有 governance metric 在門檻內")
    else:
        for i in issues:
            a(f"- {i}")
    a("")

    # ── 8.5 Hermes Baseline 5 條件即時 (v6.12 P3.15 整合) ──
    a("## 8.5 Hermes Baseline GO/NO-GO 5 條件 (Sprint 3.P3.15)")
    a("")
    a("| # | 條件 | 門檻 | 現況 | 達標 |")
    a("|---|---|---|---|---|")
    # baseline_rows 用簡單 key（有 {lookback_hours=...} label）
    baseline_rows = next(
        (v for k, v in metrics.items() if k.startswith("shadow_baseline_rows_total")),
        0,
    )
    # p95 跨 provider 取 max（含 labeled keys）
    p95_ms = max(
        (v for k, v in metrics.items() if k.startswith("shadow_baseline_latency_p95_ms")),
        default=0,
    )
    # success_ratio 取所有 provider 平均
    success_vals = [v for k, v in metrics.items() if k.startswith("shadow_baseline_success_ratio")]
    success = sum(success_vals) / len(success_vals) if success_vals else 0
    err_rate = (1 - success) * 100 if success > 0 else 100
    a(f"| 1 | baseline rows | ≥ 30 | {baseline_rows:.0f} | {'✅' if baseline_rows >= 30 else '❌'} |")
    a(f"| 2 | dogfooding 連 7d | ≥ 7 days | 未追 | ⏳ |")
    a(f"| 3 | soul fidelity | ≥ 70% | 未跑 | ⏳ |")
    a(f"| 4 | error rate | < 5% | {err_rate:.1f}% | {'✅' if err_rate < 5 else '❌'} |")
    a(f"| 5 | p95 latency | < 8s | {p95_ms/1000:.1f}s | {'✅' if p95_ms < 8000 else '❌'} |")
    met = sum([
        baseline_rows >= 30,
        False,  # dogfooding TODO
        False,  # fidelity TODO
        err_rate < 5,
        p95_ms < 8000,
    ])
    verdict = "✅ GO" if met == 5 else ("🟡 NEAR-GO" if met >= 3 else "🔴 NO-GO")
    a(f"| **Summary** | — | — | **{met}/5** | **{verdict}** |")
    a("")
    a("> ℹ️ **#4 error rate / #5 p95 為已接受的結構性限制（accepted constraint）**：瓶頸坐實在本地模型強度")
    a("> （免費策略下 TPM 牆），非 prompt/管路可解；monorepo 已定調維持免費、勿再投 prompt 層 recall 強化。")
    a("> 維持免費策略期間此兩項不列為待辦，避免每次覆盤重觸發雜訊。升付費 tier 或換更強模型才重評。")
    a("")
    a("詳見 `docs/architecture/HERMES_BASELINE_RESET_PLAN_20260530.md`")
    a("")

    # ── 9 跨 repo 範本漂移 (v6.12 step 65 整合) ──
    a("## 9. 跨 repo 範本漂移 (4 子專案 v6.12 治理採用度)")
    a("")
    a("| Repo | 跟進度 | Verdict | 修法建議 |")
    a("|---|---|---|---|")
    crd = check_cross_repo_drift()
    for tgt, present, total, verdict in crd:
        action = "—" if verdict in ("🟢 GREEN", "⚪ N/A") else "`install-template-to.sh`"
        a(f"| {tgt} | {present}/{total} | {verdict} | {action} |")
    a("")
    red_count = sum(1 for _, _, _, v in crd if "RED" in v)
    if red_count > 0:
        a(f"⚠ **{red_count}/4 子專案 RED** — 範本對外採用度不足，owner approve 後執行:")
        a("```bash")
        a("bash scripts/install-template-to.sh ../<repo_name> \\")
        a("  --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons")
        a("```")
    a("")

    # ── 9.5 Cron 排程真活表 (v6.13 owner: 真活大於規劃) ──
    a("## 9.5 Cron 排程真活全表 (事件追溯依據)")
    a("")
    a("**近期活躍 cron**（從 `/metrics scheduler_job_*` 即時抓 = 重啟後已 fire 的 job）：")
    a("")
    a("> ⚠️ 此表只含「後端重啟後已執行過」的 job（metric 重啟歸零）；週級/月級 job 在重啟後")
    a("> 到下次 fire 前不會出現於此，**非代表中斷**。完整註冊×執行對賬（用持久 cron_events.jsonl，")
    a("> 涵蓋週自傳等低頻 job）以 `scheduler_liveness_audit.py` 為權威，silent dormant 由其偵測。")
    a("")
    scheduler_age = {k: v for k, v in metrics.items() if k.startswith("scheduler_job_last_run_age_seconds")}
    scheduler_succ = {k: v for k, v in metrics.items() if k.startswith("scheduler_job_success_total")}
    scheduler_fail = {k: v for k, v in metrics.items() if k.startswith("scheduler_job_failure_total")}
    a(f"| Job ID | Age | Success | Failure | 狀態 |")
    a(f"|---|---|---|---|---|")
    seen_jobs = set()
    rows = []
    for k, v in scheduler_age.items():
        job_id = k.split('job_id="')[1].split('"')[0] if 'job_id=' in k else "?"
        if job_id in seen_jobs:
            continue
        seen_jobs.add(job_id)
        hours = v / 3600
        succ_key = f'scheduler_job_success_total{{job_id="{job_id}"}}'
        fail_key = f'scheduler_job_failure_total{{job_id="{job_id}"}}'
        succ = int(scheduler_succ.get(succ_key, 0))
        fail = int(scheduler_fail.get(fail_key, 0))
        if hours < 24 and succ > 0:
            status = "🟢"
        elif hours < 48:
            status = "🟡"
        else:
            status = "🔴"
        rows.append((hours, job_id, succ, fail, status))
    # 排序：先 RED 後 YELLOW 後 GREEN
    rows.sort(key=lambda r: (r[4] != "🔴", r[4] != "🟡", -r[0]))
    for hours, job_id, succ, fail, status in rows:
        a(f"| `{job_id}` | {hours:.1f}h | {succ} | {fail} | {status} |")
    a("")
    a(f"**統計**：{len(rows)} 個近期活躍 cron / {len([r for r in rows if r[4] == '🟢'])} GREEN / "
      f"{len([r for r in rows if r[4] == '🟡'])} YELLOW / {len([r for r in rows if r[4] == '🔴'])} RED"
      f"（完整對賬見 scheduler_liveness_audit）")
    a("")
    a("**凌晨低干擾排程設計（v6.13）**：")
    a("- 02:00 fitness_daily / 02:30 dashboard_regen / 02:45 self_retrospective")
    a("- 03:00 optimization_pipeline / 03:35 db_schema")
    a("- 避開 06:00-22:00 用戶活躍時段 + 早報推播")
    a("")
    a("**事件追溯**：每 scheduler tracker 含 `last_run` / `last_status` / `last_duration_ms` / `last_error`")
    a("")

    # ── 9.6 Cron 執行歷史 (v6.13 owner: 紀錄變文件化與架構) ──
    a("## 9.6 Cron 執行歷史摘要 (jsonl event log)")
    a("")
    a("**事件 log**：`backend/logs/cron_events.jsonl` (跨 backend restart 持久化)")
    a("")
    events_log = LOGS_DIR / "cron_events.jsonl"
    if events_log.exists():
        import json as _json
        try:
            event_raw_lines = events_log.read_text(encoding="utf-8").splitlines()
            recent = []
            for line in event_raw_lines[-30:]:
                try:
                    recent.append(_json.loads(line))
                except Exception:
                    pass
            if recent:
                a(f"**最近 {len(recent)} 個事件**：")
                a("")
                a("| 時間 | Job | 狀態 | 耗時 |")
                a("|---|---|---|---|")
                for ev in reversed(recent[-10:]):
                    ts = ev.get("ts", "?")[-8:]
                    job = ev.get("job_id", "?")[:30]
                    status = ev.get("status", "?")
                    duration = ev.get("duration_ms", 0)
                    icon = "✅" if status == "success" else "❌"
                    a(f"| {ts} | `{job}` | {icon} {status} | {duration:.0f}ms |")
                a("")
                # 統計
                succ = sum(1 for e in recent if e.get("status") == "success")
                fail = sum(1 for e in recent if e.get("status") == "failure")
                a(f"**統計** (最近 {len(recent)} 個事件): {succ} 成功 / {fail} 失敗 / 失敗率 {fail/len(recent)*100:.1f}%")
            else:
                a("⚪ 無 cron event 紀錄（jsonl 為空或解析錯）")
        except Exception as e:
            a(f"⚠ event log 讀取錯: {e}")
    else:
        a("⚪ cron_events.jsonl 不存在（待 backend rebuild 後 SchedulerTracker._append_event 啟動）")
    a("")

    # ── 10 owner action 待辦 ──
    a("## 10. Owner action 待辦 (不可委任)")
    a("")
    a("- ADR-0020 + ADR-0035 proposed 收斂")
    a("- 4 pending crystal 審批 (`/admin/crystals`)")
    a("- Hermes GO/NO-GO baseline 重評")
    a(f"- 跨 repo install-template 對 {red_count} RED 子專案套用 (詳 §9)")
    a("- CK_KMapAdvisor CLAUDE.md STALE 32 天")
    a("- Task Scheduler 重建 / sync_enabled=true")
    a("")

    # ── 10 整合視角結論 ──
    a("---")
    a("")
    a("## 整合視角結論")
    a("")
    a("> 此 dashboard 整合 5 處散落治理文件 (194 docs)，解決「每次詢問都有缺漏」的整合缺口。")
    a("> Session 啟動讀此檔取完整快照，無需重新 grep 各處規範。")
    a("> 更新: 06:00 cron 自動 regenerate + LINE 推 / 手動: `python scripts/checks/generate_governance_dashboard.py`")

    return "\n".join(lines)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8")
    print(f"✓ Wrote {OUT}")
    print(f"  Size: {len(OUT.read_text(encoding='utf-8'))} chars")
    return 0


if __name__ == "__main__":
    # L49.8 family: host cp950 stdout 無法編碼 ✓/中文 → 結尾 print 崩潰（檔已寫成功卻 rc!=0）
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
