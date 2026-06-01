"""Optimization Pipeline Orchestrator — 每日把散修零件串成連通的流水線。

2026-05-16 retro 治理建議（架構覆盤）:
  每日 cron 03:00 跑此 orchestrator，產出 daily digest 推送 owner。
  避免「環節各自跑卻沒人合成 holistic 健康度」的累積債務。

設計
====

10 條優化環節盤點見 ``docs/architecture/OPTIMIZATION_PIPELINE.md``。
本 orchestrator 不重複實作各環節邏輯，而是**呼叫既有模組** + 合成 digest:

1. **Fitness 22 steps**         → 透過 ``run_fitness.sh`` (subprocess)
2. **Capability Usage Audit**   → 透過 ``capability_usage_audit.py`` (subprocess)
3. **Memory Loop Health**       → 直接 filesystem 計數
4. **Shadow Baseline 24h**      → 直接 SQLite 查
5. **ADR Orphan 偵測**          → capability_usage_audit JSON 已含
6. **Pre-commit Guard probe**   → git log 過去 24h 是否有 commit 被擋
7. **Cron 任務真活 probe**      → APScheduler get_jobs() last_run_time

產出
====

* JSON daily report at ``wiki/memory/pipeline-reports/YYYY-MM-DD.json``
* Markdown summary at ``wiki/memory/pipeline-reports/YYYY-MM-DD.md``
* Telegram/LINE push (optional, dev-only env flag ``PIPELINE_PUSH_ENABLED``)

ADR-0028 合規
=============

* 任何環節失敗（subprocess timeout / DB unreachable）→ ``logger.error`` + 部分降級
* Orchestrator 自身不該因任一環節失敗而崩潰；報告中標記該節「ERROR」即可
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from app.core.paths import PROJECT_ROOT, WIKI_DIR, WIKI_MEMORY_DIR, BACKEND_DIR, LOGS_DIR  # v6.10 P1-E SSOT
# v6.13 (2026-05-31) L52 family 第 7 案修法：
# bug: BACKEND_DIR / "logs" 在 container 內 = /app/backend/logs (不存在)
# 真實 mount: ./backend/logs:/app/logs → 用 LOGS_DIR (= /app/logs)
# 影響: pipeline shadow_baseline step ERROR shadow_trace.db not found
SHADOW_DB = LOGS_DIR / "shadow_trace.db"
REPORT_DIR = WIKI_MEMORY_DIR / "pipeline-reports"


# ─── Step Result Types ─────────────────────────────────────────────


@dataclass
class StepResult:
    """單一環節執行結果。"""

    name: str
    status: str  # green | yellow | red | error
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 1),
        }


# ─── Step 1: Fitness Steps ─────────────────────────────────────────


def _run_fitness() -> StepResult:
    """呼叫 run_fitness.sh，解析紅燈/黃燈 step。"""
    import time
    t0 = time.time()
    script = PROJECT_ROOT / "scripts" / "checks" / "run_fitness.sh"

    if not script.exists():
        return StepResult(
            name="fitness",
            status="error",
            summary="run_fitness.sh not found",
            duration_ms=(time.time() - t0) * 1000,
        )

    bash = shutil.which("bash")
    if not bash:
        return StepResult(
            name="fitness",
            status="error",
            summary="bash interpreter not found (Windows: install Git Bash)",
            duration_ms=(time.time() - t0) * 1000,
        )

    try:
        proc = subprocess.run(
            [bash, str(script)],
            capture_output=True, text=True, timeout=300,
            cwd=str(PROJECT_ROOT),
            # Windows subprocess 預設用 cp950 解碼，遇 emoji/Unicode 會 UnicodeDecodeError
            # → output 變 None → 後續 stdout+stderr 報 NoneType + NoneType 錯
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return StepResult(
            name="fitness",
            status="error",
            summary="run_fitness.sh timed out (>300s)",
            duration_ms=(time.time() - t0) * 1000,
        )

    output = (proc.stdout or "") + (proc.stderr or "")
    # 簡單解析：抓 [FAIL] / [WARN] / [PASS] 行
    fail_count = len(re.findall(r"\[FAIL\]|\[ERROR\]|\bFAIL\b", output))
    warn_count = len(re.findall(r"\[WARN\]|\[YELLOW\]|\bWARN\b", output))
    pass_count = len(re.findall(r"\[PASS\]|\[OK\]|\bPASS\b", output))

    if fail_count > 0:
        status = "red"
    elif warn_count > 0:
        status = "yellow"
    else:
        status = "green"

    return StepResult(
        name="fitness",
        status=status,
        summary=f"{pass_count} pass / {warn_count} warn / {fail_count} fail",
        details={
            "pass": pass_count,
            "warn": warn_count,
            "fail": fail_count,
            "exit_code": proc.returncode,
        },
        duration_ms=(time.time() - t0) * 1000,
    )


# ─── Step 2: Capability Usage Audit ─────────────────────────────────


def _run_capability_audit() -> StepResult:
    import time
    t0 = time.time()
    script = PROJECT_ROOT / "scripts" / "checks" / "capability_usage_audit.py"
    if not script.exists():
        return StepResult(
            name="capability_audit",
            status="error",
            summary="capability_usage_audit.py not found",
            duration_ms=(time.time() - t0) * 1000,
        )

    try:
        # --quick 跳過 ADR reverse-reference grep（Windows 慢，月度 retro 才需完整）
        proc = subprocess.run(
            [sys.executable, str(script), "--json", "--quick"],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_ROOT),
            # Windows cp950 subprocess decode 防爆（同 _run_fitness）
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return StepResult(
            name="capability_audit",
            status="error",
            summary="audit timed out (>300s) — ADR ref grep too slow on Windows; consider --quick mode",
            duration_ms=(time.time() - t0) * 1000,
        )

    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        # P0-B (2026-05-19): parse fail 保留 raw stdout 前 500 字元供除錯
        # 防止 details={} 把 root cause 吃掉（同 ADR-0028 silent failure 政策）
        return StepResult(
            name="capability_audit",
            status="error",
            summary=f"failed to parse audit JSON output: {exc}",
            details={
                "raw_stdout_head": (proc.stdout or "")[:500],
                "raw_stderr_head": (proc.stderr or "")[:500],
                "exit_code": proc.returncode,
            },
            duration_ms=(time.time() - t0) * 1000,
        )

    dead_tools = len(report.get("tools", {}).get("dead", []))
    dead_kg = report.get("kg_entity_types", {}).get("dead_count", 0)
    dead_loops = len(report.get("memory_loop", {}).get("dead_loops", []))
    adr_orphans = report.get("adr", {}).get("orphan_count", 0)
    total_dead = dead_tools + dead_kg + dead_loops + adr_orphans

    if total_dead == 0:
        status = "green"
    elif total_dead <= 5:
        status = "yellow"
    else:
        status = "red"

    return StepResult(
        name="capability_audit",
        status=status,
        summary=(
            f"dead: tools={dead_tools} kg={dead_kg} loops={dead_loops} "
            f"adrs={adr_orphans} total={total_dead}"
        ),
        details=report,
        duration_ms=(time.time() - t0) * 1000,
    )


# ─── Step 3: Memory Loop Health ────────────────────────────────────


def _memory_loop_health() -> StepResult:
    import time
    t0 = time.time()
    base = WIKI_DIR / "memory"
    if not base.exists():
        return StepResult(
            name="memory_loop",
            status="error",
            summary="wiki/memory/ not found",
            duration_ms=(time.time() - t0) * 1000,
        )

    counts = {}
    for sub in ("diary", "patterns", "failures", "proposals",
                "crystals", "evolutions", "autobiography"):
        d = base / sub
        counts[sub] = len(list(d.glob("*.md"))) if d.exists() else 0

    # v6.13 (2026-06-01): proposals gate 只算 status: pending，
    # 不能把 applied/superseded 也當「pending 卡」(否則 owner 已處置仍誤判 RED)。
    # counts["proposals"] 保留總檔數供透明；gate 用 proposals_pending。
    prop_dir = base / "proposals"
    pending_props = 0
    if prop_dir.exists():
        for pf in prop_dir.glob("*.md"):
            try:
                head = pf.read_text(encoding="utf-8", errors="replace")[:400]
                m = re.search(r"^status:\s*(\S+)", head, re.MULTILINE)
                if m and m.group(1).strip() == "pending":
                    pending_props += 1
            except Exception:
                continue
    counts["proposals_pending"] = pending_props

    # v6.13 (2026-06-01): autobiography 實際寫在 evolutions/YYYY-WNN.md
    # (memory_type: autobiography)，非 wiki/memory/autobiography/ → 修正計數
    # 避免假 dormant (W17-W22 真活，已被 evolutions count 計入)。
    evo_dir = base / "evolutions"
    autobio_count = 0
    if evo_dir.exists():
        for ef in evo_dir.glob("*.md"):
            try:
                head = ef.read_text(encoding="utf-8", errors="replace")[:400]
                if re.search(r"^memory_type:\s*autobiography", head, re.MULTILINE):
                    autobio_count += 1
            except Exception:
                continue
    counts["autobiography"] = max(counts["autobiography"], autobio_count)

    dead_loops = []
    if counts["crystals"] == 0 and counts["patterns"] >= 3:
        dead_loops.append("crystals (閉環終點空)")
    if counts["autobiography"] == 0 and counts["diary"] >= 7:
        dead_loops.append("autobiography (應週期生成卻無檔)")

    if pending_props >= 3:
        dead_loops.append(f"proposals ({pending_props} pending gate 卡)")

    if not dead_loops:
        status = "green"
    elif len(dead_loops) == 1:
        status = "yellow"
    else:
        status = "red"

    return StepResult(
        name="memory_loop",
        status=status,
        summary=f"counts={counts}",
        details={"counts": counts, "dead_loops": dead_loops},
        duration_ms=(time.time() - t0) * 1000,
    )


# ─── Step 4: Shadow Baseline 24h ───────────────────────────────────


def _shadow_baseline_summary() -> StepResult:
    import time
    t0 = time.time()
    if not SHADOW_DB.exists():
        return StepResult(
            name="shadow_baseline",
            status="error",
            summary="shadow_trace.db not found",
            duration_ms=(time.time() - t0) * 1000,
        )

    try:
        conn = sqlite3.connect(str(SHADOW_DB))
        cur = conn.execute(
            """
            SELECT COUNT(*),
                   AVG(latency_ms),
                   MAX(latency_ms),
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN latency_ms > 30000 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN latency_ms > 60000 THEN 1 ELSE 0 END)
            FROM query_trace
            WHERE ts > datetime('now', '-24 hours')
            """
        )
        row = cur.fetchone()
        conn.close()
    except Exception as exc:
        return StepResult(
            name="shadow_baseline",
            status="error",
            summary=f"shadow DB query failed: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        )

    n, avg_ms, max_ms, ok_count, over30, over60 = row
    n = n or 0
    avg_ms = avg_ms or 0
    max_ms = max_ms or 0
    success_ratio = (ok_count or 0) / n if n else 0.0

    # 計算粗略 p95
    p95_ms = None
    if n > 0:
        try:
            conn = sqlite3.connect(str(SHADOW_DB))
            cur = conn.execute(
                """
                SELECT latency_ms FROM query_trace
                WHERE ts > datetime('now', '-24 hours')
                ORDER BY latency_ms ASC
                """
            )
            values = [r[0] for r in cur]
            conn.close()
            if values:
                idx = min(len(values) - 1, int(len(values) * 0.95))
                p95_ms = values[idx]
        except Exception:
            pass

    # 判斷 status — p95 ≤ 30s 綠，≤ 60s 黃，> 60s 紅；成功率 < 0.95 黃；< 0.85 紅
    status = "green"
    if p95_ms and p95_ms > 60000:
        status = "red"
    elif p95_ms and p95_ms > 30000:
        status = "yellow"
    if success_ratio < 0.85:
        status = "red"
    elif success_ratio < 0.95 and status == "green":
        status = "yellow"

    return StepResult(
        name="shadow_baseline",
        status=status,
        summary=(
            f"24h n={n} avg={avg_ms/1000:.1f}s p95={p95_ms/1000 if p95_ms else 0:.1f}s "
            f"success={success_ratio:.2%} over30={over30}/over60={over60}"
        ),
        details={
            "n": n,
            "avg_ms": int(avg_ms),
            "p95_ms": p95_ms,
            "max_ms": int(max_ms),
            "success_ratio": round(success_ratio, 3),
            "over_30s": over30 or 0,
            "over_60s": over60 or 0,
        },
        duration_ms=(time.time() - t0) * 1000,
    )


# ─── Step 5: Pre-commit Hook Probe ─────────────────────────────────


def _precommit_hook_probe() -> StepResult:
    """檢查 pre-commit 是否含 ADR-0028 3 守護腳本（本 session C1 修法）。

    v6.13 (2026-05-31) 修法: container 內 .git/ 不 mount 是設計 (git 不在 container 用)
    → 改回 INFO/skip 不算 RED (host-side cron 才應跑此 probe)
    """
    import time
    t0 = time.time()
    git_dir = PROJECT_ROOT / ".git"
    hook = git_dir / "hooks" / "pre-commit"
    if not git_dir.exists():
        # container 環境 .git 不 mount，回 INFO skip (不是 RED)
        return StepResult(
            name="precommit_hook",
            status="info",
            summary="skipped: .git/ not present (container env, host-side check only)",
            duration_ms=(time.time() - t0) * 1000,
        )
    if not hook.exists():
        return StepResult(
            name="precommit_hook",
            status="red",
            summary=".git/hooks/pre-commit not installed",
            duration_ms=(time.time() - t0) * 1000,
        )

    try:
        content = hook.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return StepResult(
            name="precommit_hook",
            status="error",
            summary=f"hook unreadable: {exc}",
            duration_ms=(time.time() - t0) * 1000,
        )

    guards = {
        "async_session_race_guard": "async_session_race_guard.py" in content,
        "sse_headers_guard": "sse_headers_guard.py" in content,
        "schema_lazy_load_guard": "schema_lazy_load_guard.py" in content,
        "pattern_yaml_type_guard": "pattern_yaml_type_guard.py" in content,
    }
    missing = [g for g, present in guards.items() if not present]

    if not missing:
        status = "green"
    elif len(missing) <= 1:
        status = "yellow"
    else:
        status = "red"

    return StepResult(
        name="precommit_hook",
        status=status,
        summary=f"guards present: {len(guards)-len(missing)}/{len(guards)}",
        details={"guards": guards, "missing": missing},
        duration_ms=(time.time() - t0) * 1000,
    )


# ─── Orchestrator ──────────────────────────────────────────────────


def run_daily_pipeline() -> Dict[str, Any]:
    """每日 pipeline 主入口 — 同步執行所有 step 並合成 digest。

    可從 cron / scheduler / CLI 呼叫。回傳完整 JSON report。
    """
    started_at = datetime.now(timezone.utc).isoformat()

    steps: List[StepResult] = []
    for step_fn in (
        _run_fitness,
        _run_capability_audit,
        _memory_loop_health,
        _shadow_baseline_summary,
        _precommit_hook_probe,
    ):
        try:
            steps.append(step_fn())
        except Exception as exc:
            logger.error("Pipeline step %s crashed: %s", step_fn.__name__, exc, exc_info=True)
            steps.append(StepResult(
                name=step_fn.__name__.lstrip("_"),
                status="error",
                summary=f"crashed: {type(exc).__name__}: {exc}",
            ))

    # 整體狀態 = 最差子 step
    status_priority = {"green": 0, "yellow": 1, "red": 2, "error": 3}
    overall = max(
        (s.status for s in steps),
        key=lambda s: status_priority.get(s, 4),
    )

    report = {
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "steps": [s.to_dict() for s in steps],
        "summary_lines": [f"  [{s.status.upper():<6}] {s.name:<22} {s.summary}" for s in steps],
    }

    # 寫入 report 檔
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        (REPORT_DIR / f"{date_str}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        # P0-B (2026-05-19): 同步寫 markdown digest — manual push 取代未接通的 LINE/Telegram
        # 5/19 揭發：format_digest_markdown 函數早已存在但 main 段沒呼叫 → 5/19 report 只有 .json 無 .md
        # 這也是 owner 看不到 daily health 的根因之一
        (REPORT_DIR / f"{date_str}.md").write_text(
            format_digest_markdown(report), encoding="utf-8",
        )
    except Exception as exc:
        logger.error("Failed to write pipeline report file: %s", exc)

    # P0-2 (2026-05-20)：自動推送 LINE digest（受 PIPELINE_PUSH_ENABLED env gate）
    # 解 R3 監督機制失明 — orchestrator 跑完無人收到通知
    if os.getenv("PIPELINE_PUSH_ENABLED", "false").lower() in ("true", "1"):
        try:
            push_digest_to_line_sync(report)
        except Exception as exc:
            # 推送失敗不影響 report 回傳（防止監督機制自己崩潰）
            logger.error("Auto-push pipeline digest failed: %s", exc, exc_info=True)

    return report


def format_digest_markdown(report: Dict[str, Any]) -> str:
    """格式化 daily digest 給 push channel（LINE/Telegram）。"""
    overall = report["overall_status"]
    lines = [
        f"# Optimization Pipeline Daily — {datetime.now().strftime('%Y-%m-%d')}",
        f"",
        f"**Overall**: {overall.upper()}",
        f"",
        "## Steps",
    ]
    for line in report["summary_lines"]:
        lines.append(line)
    lines.append("")
    lines.append("(完整 report: `wiki/memory/pipeline-reports/`)")
    return "\n".join(lines)


def _format_line_digest(report: Dict[str, Any]) -> str:
    """精簡 LINE digest（4000 字內），優先顯示 RED/YELLOW step。

    LINE 不支援 markdown，純文字。
    """
    red = [s for s in report["steps"] if s["status"] in ("red", "error")]
    yellow = [s for s in report["steps"] if s["status"] == "yellow"]

    lines = [
        f"📊 Pipeline {datetime.now().strftime('%Y-%m-%d')}",
        f"Overall: {report['overall_status'].upper()}",
        "",
    ]
    if red:
        lines.append(f"🔴 RED ({len(red)}):")
        for s in red:
            lines.append(f"  • {s['name']}: {s['summary'][:120]}")
        lines.append("")
    if yellow:
        lines.append(f"🟡 YELLOW ({len(yellow)}):")
        for s in yellow[:5]:  # 至多 5 條避免 LINE 4000 字限制
            lines.append(f"  • {s['name']}: {s['summary'][:120]}")
        lines.append("")
    if not red and not yellow:
        lines.append("✅ All steps GREEN")
        lines.append("")
    lines.append("詳見 wiki/memory/pipeline-reports/")
    return "\n".join(lines)


async def push_digest_to_line(report: Dict[str, Any]) -> bool:
    """P0-2 (2026-05-20)：daily pipeline digest 推送至 LINE admin 通道。

    解 RETRO_20260519 §3 R3「監督機制自身失明」— orchestrator 跑完無人收到通知。
    既有 admin push 通道（autobiography.push_to_line 同模式）+ admin_push_metrics counter。

    Args:
        report: run_daily_pipeline() 回傳的 report dict

    Returns:
        True if 真正送出 (LINE API 200) else False (env disabled / 缺 user_id / push fail)

    ENV gate:
        - PIPELINE_PUSH_ENABLED=true → 啟用本 push
        - LINE_GROWTH_NOTIFY_ENABLED=false → 全域關閉
        - LINE_ADMIN_USER_ID 必須設
    """
    if os.getenv("PIPELINE_PUSH_ENABLED", "false").lower() not in ("true", "1"):
        return False
    if os.getenv("LINE_GROWTH_NOTIFY_ENABLED", "true").lower() in ("false", "0"):
        return False

    line_user_id = os.getenv("LINE_ADMIN_USER_ID")
    if not line_user_id:
        logger.warning(
            "Pipeline LINE push skipped: LINE_ADMIN_USER_ID env not set",
        )
        return False

    try:
        from app.services.integration.line_bot import LineBotService
        line_bot = LineBotService()
        if not line_bot.enabled:
            logger.warning(
                "Pipeline LINE push skipped: LineBotService disabled "
                "(check LINE_CHANNEL_ACCESS_TOKEN)",
            )
            return False

        msg = _format_line_digest(report)
        ok = await line_bot.push_message(line_user_id, msg[:4000])
        if ok:
            logger.info(
                "Pipeline LINE digest pushed: overall=%s",
                report.get("overall_status"),
            )
        else:
            logger.warning(
                "Pipeline LINE digest push returned False (LINE API may be down)",
            )
        return ok
    except Exception as exc:
        # ADR-0028 錯誤合約化：監督機制自己也不能 silent fail
        logger.error(
            "Pipeline LINE digest push error: %s", exc, exc_info=True,
        )
        return False


def push_digest_to_line_sync(report: Dict[str, Any]) -> bool:
    """同步 wrapper — cron / __main__ 用。"""
    try:
        return asyncio.run(push_digest_to_line(report))
    except RuntimeError:
        # 已在 event loop 內（如從 FastAPI 呼叫）→ 直接 await 不是這 sync wrapper 的責任
        logger.warning(
            "push_digest_to_line_sync called from inside event loop; "
            "caller should await push_digest_to_line directly",
        )
        return False


# ─── CLI ───────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Optimization Pipeline Orchestrator")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--push", action="store_true", help="Push digest (LINE/Telegram, future)")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    report = run_daily_pipeline()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(format_digest_markdown(report))
        print()
        # 顯示詳細 step summary
        for line in report["summary_lines"]:
            print(line)

    # P0-2 (2026-05-20)：CLI --push 強制觸發 LINE push（不論 env gate）
    if args.push:
        # 暫時設 env gate 為 true 讓 push 函數通過
        os.environ.setdefault("PIPELINE_PUSH_ENABLED", "true")
        pushed = push_digest_to_line_sync(report)
        print(f"\n[PUSH] LINE digest pushed: {pushed}")

    # exit code 對應 overall status
    code_map = {"green": 0, "yellow": 0, "red": 1, "error": 2}
    sys.exit(code_map.get(report["overall_status"], 2))
