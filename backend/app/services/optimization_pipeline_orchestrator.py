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
    # v6.21 (2026-06-18) 修：原 status_priority 缺 "info"，配 .get(s, 4) 預設值
    # → precommit_hook 的 info(容器略過) 被算成優先級 4，反而蓋過 red(2)
    # → 管理端看到誤導性「Overall: INFO」(底下其實有 RED)。
    # 修法：info 列為最低優先（非阻斷），unknown 預設 0(非 4)，overall 如實反映最差 actionable。
    status_priority = {"info": -1, "green": 0, "yellow": 1, "red": 2, "error": 3}
    overall = max(
        (s.status for s in steps),
        key=lambda s: status_priority.get(s, 0),
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


# ─── 中文化標籤 + 白話解讀（v6.21 2026-06-18：使管理端更明確掌握資訊）──────
# owner 回饋：LINE 推播「[Pipeline INFO] 每日巡檢 (5 steps)」英文標籤 + raw dict
# 對管理端不友善。以下把步驟名/狀態/摘要轉成中文白話。

STEP_LABELS_ZH = {
    "fitness": "架構健檢",
    "capability_audit": "能力使用稽核",
    "memory_loop": "記憶學習閉環",
    "shadow_baseline": "AI 回應品質基線",
    "precommit_hook": "提交守門",
}

STATUS_LABELS_ZH = {
    "green": "✅ 正常",
    "yellow": "🟡 注意",
    "red": "🔴 異常",
    "error": "⛔ 錯誤",
    "info": "ℹ️ 略過",
}

OVERALL_LABELS_ZH = {
    "green": "✅ 全部正常",
    "yellow": "🟡 注意（無紅燈阻斷）",
    "red": "🔴 有異常項待確認",
    "error": "⛔ 巡檢執行錯誤",
    "info": "ℹ️ 資訊",
}


def _is_accepted_red(step: Dict[str, Any]) -> bool:
    """判斷 shadow_baseline 的紅燈是否為「已知限制」（非 actionable）。

    p95 延遲超標但成功率仍 OK = 本地模型強度上限（免費策略下的 TPM 牆），
    monorepo 已定調維持免費、不投 prompt 層 → 屬已接受限制，不應驚動管理端。
    """
    if step.get("name") != "shadow_baseline" or step.get("status") != "red":
        return False
    d = step.get("details") or {}
    p95 = d.get("p95_ms") or 0
    succ = d.get("success_ratio")
    return p95 > 60000 and (succ is None or succ >= 0.85)


def _display_overall_zh(report: Dict[str, Any]) -> str:
    """人類可讀的整體狀態：紅燈若全為「已知限制」則不以 🔴 驚動管理端。

    機器用的 report["overall_status"] 仍保留真實最差值（供 alerting / exit code），
    此函式只決定「人看的那行」如何呈現，避免每日因已知延遲上限被訓練成忽略紅燈。
    """
    steps = report.get("steps", [])
    actionable = [s for s in steps
                  if s["status"] in ("red", "error") and not _is_accepted_red(s)]
    accepted = [s for s in steps if _is_accepted_red(s)]
    yellow = [s for s in steps if s["status"] == "yellow"]
    if any(s["status"] == "error" for s in actionable):
        return OVERALL_LABELS_ZH["error"]
    if actionable:
        return OVERALL_LABELS_ZH["red"]
    if yellow and accepted:
        return "🟡 注意（含已知限制，無紅燈待處理）"
    if yellow:
        return OVERALL_LABELS_ZH["yellow"]
    if accepted:
        return "🟢 正常（僅含已知限制，無需處理）"
    return OVERALL_LABELS_ZH["green"]


def _interpret_zh(step: Dict[str, Any]) -> str:
    """把 step 英文 summary 轉成管理端看得懂的中文白話。"""
    name = step.get("name")
    d = step.get("details") or {}
    if name == "fitness":
        return (f"{d.get('pass', '?')} 項通過、{d.get('warn', '?')} 項待注意、"
                f"{d.get('fail', '?')} 項失敗")
    if name == "capability_audit":
        if step.get("status") == "green":
            return "無閒置能力（工具／知識圖譜／學習迴圈／ADR 皆有在用）"
        return f"偵測到閒置能力待清理（{step.get('summary', '')}）"
    if name == "memory_loop":
        c = d.get("counts", {})
        return (f"日記 {c.get('diary', '?')} 篇、學習模式 {c.get('patterns', '?')} 個、"
                f"待批提案 {c.get('proposals_pending', '?')} 件、已結晶 {c.get('crystals', '?')} 個")
    if name == "shadow_baseline":
        n = d.get("n", "?")
        avg = (d.get("avg_ms") or 0) / 1000
        p95 = (d.get("p95_ms") or 0) / 1000
        succ = d.get("success_ratio")
        base = f"近 24 小時 {n} 筆、平均 {avg:.1f} 秒、p95 {p95:.1f} 秒"
        if succ is not None:
            base += f"、成功率 {succ:.0%}"
        if _is_accepted_red(step):
            base += "（延遲偏高＝本地模型強度上限，免費策略下屬已知限制、無需處理）"
        return base
    if name == "precommit_hook":
        if step.get("status") == "info":
            return "容器環境略過（提交守門於主機端 git 執行）"
        return step.get("summary", "")
    return step.get("summary", "")


def format_digest_markdown(report: Dict[str, Any]) -> str:
    """格式化 daily digest 為中文表格（寫入 .md + 終端輸出）。"""
    date = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# 系統每日巡檢報告 — {date}",
        "",
        f"**整體狀態**：{_display_overall_zh(report)}",
        "",
        "| 巡檢項目 | 狀態 | 說明 |",
        "|---|---|---|",
    ]
    for s in report["steps"]:
        label = STEP_LABELS_ZH.get(s["name"], s["name"])
        st = STATUS_LABELS_ZH.get(s["status"], s["status"])
        lines.append(f"| {label} | {st} | {_interpret_zh(s)} |")
    lines.append("")
    lines.append("> 巡檢由每日 cron 自動執行；完整明細：`wiki/memory/pipeline-reports/`")
    return "\n".join(lines)


def _format_line_digest(report: Dict[str, Any]) -> str:
    """精簡 LINE digest（4000 字內），中文、按嚴重度分區，管理端一眼掌握。

    分區：🔴 需處理（actionable red/error）→ 🟡 注意 → ℹ️ 已知限制（accepted red）。
    LINE 不支援 markdown，純文字。
    """
    steps = report["steps"]
    actionable = [s for s in steps
                  if s["status"] in ("red", "error") and not _is_accepted_red(s)]
    yellow = [s for s in steps if s["status"] == "yellow"]
    accepted = [s for s in steps if _is_accepted_red(s)]

    date = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊 系統每日巡檢 — {date}",
        f"整體：{_display_overall_zh(report)}",
        "",
    ]
    if actionable:
        lines.append(f"🔴 需處理（{len(actionable)} 項）：")
        for s in actionable:
            lines.append(f"  • {STEP_LABELS_ZH.get(s['name'], s['name'])}：{_interpret_zh(s)[:140]}")
        lines.append("")
    if yellow:
        lines.append(f"🟡 注意（{len(yellow)} 項）：")
        for s in yellow[:5]:  # 至多 5 條避免超過 LINE 4000 字
            lines.append(f"  • {STEP_LABELS_ZH.get(s['name'], s['name'])}：{_interpret_zh(s)[:140]}")
        lines.append("")
    if accepted:
        lines.append(f"ℹ️ 已知限制（{len(accepted)} 項，無需處理）：")
        for s in accepted:
            lines.append(f"  • {STEP_LABELS_ZH.get(s['name'], s['name'])}：{_interpret_zh(s)[:160]}")
        lines.append("")
    if not actionable and not yellow and not accepted:
        lines.append("✅ 五項巡檢全部正常")
        lines.append("")
    lines.append("📂 完整明細：wiki/memory/pipeline-reports/")
    return "\n".join(lines)


# 公開別名供 scheduler 等呼叫端使用（避免跨模組 import 私有 _ 名）
format_line_digest = _format_line_digest
display_overall_zh = _display_overall_zh


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
        # raw step summary（除錯用，英文機器格式；管理端看上方中文表格）
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
