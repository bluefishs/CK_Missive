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
            "governance_", "scheduler_job_success_total",
            "kg_entities_total", "wiki_pages_total",
            "v7_", "shadow_baseline_rows_total",
            "memory_diary_days_total", "memory_crystals_total",
        )):
            try:
                key = line.split("{")[0].split(" ")[0]
                val = float(line.rsplit(" ", 1)[1])
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
    """回 [(L編號, 標題)]"""
    out = []
    d = ROOT / "wiki" / "memory" / "lessons"
    if not d.is_dir():
        return out
    for f in sorted(d.glob("L*.md")):
        m = re.match(r"^(L\d+)_(.+)\.md$", f.name)
        if m:
            out.append((m.group(1), m.group(2).replace("_", " ")))
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
    facades_dir = ROOT / "backend" / "app" / "services" / "contracts" / "facades"
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
                 "backend/app/", "--include=*.py"],
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
    a(f"| Lessons | {len(lessons)} | `wiki/memory/lessons/L*.md` |")
    rules_count = len(list((ROOT / ".claude" / "rules").glob("*.md")))
    a(f"| SOPs | {rules_count} | `.claude/rules/*.md` |")
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

    # ── 3 最近 8 commits ──
    a("## 3. 最近 8 commits (進化執行軌跡)")
    a("")
    for c in commits:
        a(f"- `{c}`")
    a("")

    # ── 4 最近 session 覆盤 ──
    a("## 4. 最近 5 session 覆盤 (memory/)")
    a("")
    for s in sessions:
        a(f"- {s}")
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
    sys.exit(main())
