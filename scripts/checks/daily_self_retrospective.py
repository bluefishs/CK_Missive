"""Daily Self-Retrospective (v6.12 #4 升級版, 2026-05-30)

每日 06:30 自動跑「規範 vs 現況」6 面向對齊檢查，防 L4x family 反覆。

設計觸發：Owner 反饋
> 是否能建構每日自我覆盤機制 以及核心服務議題 避免規範現況落差
> 實現自我進化檢核 非重複錯誤

對齊元覆盤 §4 進化原則 #4 (從「季初強制」升級為「daily 自我覆盤」)

【7 面向】
1. ADR vs 現況落差 (active ADR 是否仍有效)
2. SOP 遵守度 (container image freshness / env alignment)
3. 核心服務真活 (Hermes/坤哥/agent_query/shadow)
4. L4x family 反覆預警 (新增 lesson 是否屬已知 family)
5. 學習閉環健康度 (patterns/proposals/crystals 流通)
6. 觀測閉環真活 (cron last_run / messaging counter)
7. **已建構資產真活** (KG/LLM Wiki/Code Graph/GitNexus 是否仍 update)
   - Owner 反饋: 「已建構程式圖譜 llmwiki 等好像都無法自動化與覆盤」
   - 防 dormant asset (建表不等於用表) 反模式

報告寫 wiki/memory/self-retrospective-reports/YYYY-MM-DD.md
+ LINE 推 owner 摘要

Usage:
  python scripts/checks/daily_self_retrospective.py
  python scripts/checks/daily_self_retrospective.py --update-baseline
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WIKI_MEMORY = PROJECT_ROOT / "wiki" / "memory"
REPORTS_DIR = WIKI_MEMORY / "self-retrospective-reports"
BASELINE_FILE = WIKI_MEMORY / "self_retrospective_baseline.json"


_METRICS_CACHE: dict = {"text": None, "ok": None, "err": None}


def _fetch_metrics_text() -> tuple[str | None, str | None]:
    """單次 fetch /metrics，retry 2 次（避 backend restart 瞬間誤判）。
    回 (text, error_str) — 任一為 None。"""
    import urllib.request
    last_err = None
    for attempt in (1, 2, 3):
        try:
            with urllib.request.urlopen(
                "http://localhost:8001/metrics", timeout=10
            ) as r:
                return r.read().decode("utf-8", errors="ignore"), None
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt < 3:
                import time as _t
                _t.sleep(2)
    return None, last_err


def metric(name: str) -> float:
    """從 /metrics 抓單一 metric 值（簡單 parser）。
    v6.12 補完：cache 單次 fetch + retry，避 backend restart 瞬間 silent timeout。
    """
    if _METRICS_CACHE["text"] is None and _METRICS_CACHE["ok"] is None:
        text, err = _fetch_metrics_text()
        _METRICS_CACHE["text"] = text
        _METRICS_CACHE["ok"] = text is not None
        _METRICS_CACHE["err"] = err
    text = _METRICS_CACHE["text"]
    if not text:
        return -1.0
    for line in text.splitlines():
        if line.startswith(name + " "):
            try:
                return float(line.split()[-1])
            except (ValueError, IndexError):
                return -1.0
    return -1.0


def metric_endpoint_health() -> dict:
    """報告 /metrics endpoint 是否可達 — 避免誤把 endpoint down 當 self fitness 問題"""
    if _METRICS_CACHE["ok"] is None:
        _fetch_metrics_text()  # trigger 一次 cache
    return {
        "reachable": bool(_METRICS_CACHE["ok"]),
        "error": _METRICS_CACHE["err"],
    }


# =============================================================
# 1. ADR vs 現況落差
# =============================================================

def check_adr_alignment() -> dict:
    """active ADR 數量 + stale (>90d 未動)"""
    adr_dir = PROJECT_ROOT / "docs" / "adr"
    if not adr_dir.exists():
        return {"status": "SKIP", "reason": "adr dir missing"}

    active = 0
    stale_90d = 0
    cutoff = datetime.now() - timedelta(days=90)

    for f in adr_dir.glob("*.md"):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            # 取 status
            m = re.search(r"^\s*[*-]?\s*\*?\*?狀態\*?\*?[:：]\s*(\w+)", text, re.MULTILINE)
            if not m:
                m = re.search(r"^\s*[*-]?\s*\*?\*?status\*?\*?[:：]\s*(\w+)",
                              text, re.MULTILINE | re.IGNORECASE)
            status = m.group(1).lower() if m else "unknown"
            if status in ("accepted", "proposed", "active"):
                active += 1
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    stale_90d += 1
        except Exception:
            continue

    level = "GREEN"
    if active > 25:
        level = "YELLOW"  # 治理債過多
    if stale_90d > 5:
        level = "RED"  # active 但 90d 未動可能 dormant

    return {
        "status": level,
        "active_count": active,
        "stale_90d": stale_90d,
        "target": "active ≤25, stale ≤5",
    }


# =============================================================
# 2. SOP 遵守度
# =============================================================

def check_sop_compliance() -> dict:
    """跑 container env + image freshness 兩 audit"""
    results = []
    for script in ("container_env_alignment_audit.py", "container_image_freshness_check.py"):
        p = PROJECT_ROOT / "scripts" / "checks" / script
        if not p.exists():
            continue
        try:
            r = subprocess.run(
                ["python", str(p)],
                capture_output=True, text=True, timeout=30,
            )
            results.append({
                "script": script,
                "rc": r.returncode,
                "tail": (r.stdout or "")[-200:],
            })
        except Exception as e:
            results.append({"script": script, "rc": -1, "error": str(e)[:100]})

    fail_count = sum(1 for r in results if r.get("rc", 0) != 0)
    return {
        "status": "RED" if fail_count > 0 else "GREEN",
        "fail_count": fail_count,
        "audits_run": len(results),
    }


# =============================================================
# 3. 核心服務真活 (Hermes-agent + 坤哥)
# =============================================================

def check_core_services_alive() -> dict:
    """Hermes baseline + 坤哥 metric"""
    return {
        "shadow_baseline_rows_24h": metric("shadow_baseline_rows_total"),
        "messaging_push_line_success": metric('messaging_push_total{channel="line",result="success"}'),
        "v7_channel_diversity": metric("v7_channel_diversity"),
        "v7_soul_drift": metric("v7_soul_drift_lines"),
        "memory_diary_days": metric("memory_diary_days_total"),
        "memory_crystals": metric("memory_crystals_total"),
        "memory_proposals_pending": metric("memory_proposals_pending"),
        "status": "INFO",
    }


# =============================================================
# 4. L4x family 反覆預警
# =============================================================

def check_l4x_family_pattern() -> dict:
    """偵測 L4x family count 是否增量"""
    lessons = WIKI_MEMORY / "lessons"
    failures = WIKI_MEMORY / "failures"
    l4x_count = 0
    latest_files = []

    for d in (lessons, failures):
        if d.exists():
            for f in d.glob("*.md"):
                if re.match(r"L(4\d|5\d)_", f.name):
                    l4x_count += 1
                    latest_files.append(f.name)

    # 比對 baseline
    baseline = _load_baseline()
    baseline_l4x = baseline.get("l4x_count", 0)
    delta = l4x_count - baseline_l4x

    return {
        "status": "RED" if delta > 0 else "GREEN",
        "l4x_count": l4x_count,
        "baseline": baseline_l4x,
        "delta_since_baseline": delta,
        "latest_5": latest_files[-5:],
    }


# =============================================================
# 5. 學習閉環健康度
# =============================================================

def check_learning_loop() -> dict:
    """patterns / proposals / crystals 流通率"""
    patterns = len(list((WIKI_MEMORY / "patterns").glob("*.md"))) if (WIKI_MEMORY / "patterns").exists() else 0
    proposals_dir = WIKI_MEMORY / "proposals"
    pending = 0
    if proposals_dir.exists():
        for f in proposals_dir.glob("*.md"):
            try:
                if "status: pending" in f.read_text(encoding="utf-8", errors="ignore"):
                    pending += 1
            except Exception:
                continue
    crystals = len(list((WIKI_MEMORY / "crystals").glob("*.md"))) if (WIKI_MEMORY / "crystals").exists() else 0
    evolutions = len(list((WIKI_MEMORY / "evolutions").glob("20*.md"))) if (WIKI_MEMORY / "evolutions").exists() else 0

    # 流通率 = crystals / (crystals + pending)
    total = crystals + pending
    flow_rate = (crystals / total * 100) if total > 0 else 0

    level = "GREEN" if flow_rate >= 30 else ("YELLOW" if flow_rate >= 10 else "RED")

    return {
        "status": level,
        "patterns": patterns,
        "proposals_pending": pending,
        "crystals_applied": crystals,
        "evolutions": evolutions,
        "flow_rate_pct": round(flow_rate, 1),
        "target": "flow ≥30%",
    }


# =============================================================
# 6. 觀測閉環真活
# =============================================================

def check_observability_alive() -> dict:
    """governance metrics + pipeline report freshness"""
    return {
        "pipeline_red_consecutive_days": metric("governance_pipeline_red_consecutive_days"),
        "report_freshness_hours": metric("governance_fitness_report_freshness_hours"),
        "lessons_total": metric("governance_lessons_total"),
        "messaging_push_24h": metric('messaging_push_total{channel="line",result="success"}'),
        "status": "INFO",
    }


# =============================================================
# 7. 已建構資產真活 (KG/LLM Wiki/Code Graph/GitNexus)
# =============================================================

def check_built_assets_alive() -> dict:
    """Owner 反饋: 「已建構程式圖譜 llmwiki 等好像都無法自動化與覆盤」

    防 dormant asset 反模式 — 已花成本建構但無持續更新 = 過時資產
    """
    result = {"status": "INFO"}

    # KG canonical_entities — 真實 metric name 是 kg_entities_total (5/30 self-debug 修正)
    kg_total = metric("kg_entities_total")
    kg_embedded = metric("kg_entities_embedded_total")
    result["kg_entities_total"] = kg_total
    result["kg_entities_embedded"] = kg_embedded
    if kg_total > 0 and kg_embedded >= 0:
        result["kg_embedding_coverage_pct"] = round(kg_embedded / kg_total * 100, 1)

    # LLM Wiki pages (wiki/*.md 排除 memory/)
    wiki_dir = PROJECT_ROOT / "wiki"
    if wiki_dir.exists():
        wiki_pages = sum(1 for p in wiki_dir.rglob("*.md") if "memory" not in p.parts)
        result["wiki_pages_total"] = wiki_pages
        # 最新 wiki page mtime
        try:
            latest = max(
                (p for p in wiki_dir.rglob("*.md") if "memory" not in p.parts),
                key=lambda p: p.stat().st_mtime,
                default=None,
            )
            if latest:
                hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
                result["wiki_freshness_hours"] = round(hours, 1)
        except Exception:
            pass

    # Code Graph / GitNexus dormant 偵測
    # 看是否有 module-level dormant marker
    gitnexus_dir = PROJECT_ROOT / "wiki" / "code-graph"
    if gitnexus_dir.exists():
        try:
            latest = max(gitnexus_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, default=None)
            if latest:
                hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600
                result["code_graph_freshness_hours"] = round(hours, 1)
        except Exception:
            pass

    # Skills 自動發現
    skills_dir = PROJECT_ROOT / ".claude" / "skills"
    if skills_dir.exists():
        skills_count = sum(1 for p in skills_dir.rglob("*.md") if p.is_file())
        result["skills_count"] = skills_count

    # 評定 status
    issues = []
    if result.get("wiki_freshness_hours", 0) > 168:  # >7d
        issues.append("wiki >7d 未更新")
    if result.get("code_graph_freshness_hours", 0) > 168:
        issues.append("code_graph >7d 未更新")
    if kg_total < 0 or kg_total == 0:
        issues.append("KG metric 不可達")

    if issues:
        result["status"] = "YELLOW"
        result["issues"] = issues
    else:
        result["status"] = "GREEN"

    return result


def _load_baseline() -> dict:
    if not BASELINE_FILE.exists():
        return {}
    try:
        return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_baseline(data: dict) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def render_markdown(report: dict) -> str:
    """6 面向結果 → Markdown 報告"""
    today = date.today().isoformat()
    overall = "GREEN"
    for k, v in report.items():
        s = v.get("status", "")
        if s == "RED":
            overall = "RED"
            break
        if s == "YELLOW" and overall != "RED":
            overall = "YELLOW"

    lines = [
        f"# Daily Self-Retrospective — {today}",
        "",
        f"**Overall**: {overall}",
        "",
        "## 6 面向結果",
        "",
    ]
    icons = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "INFO": "ℹ️", "SKIP": "⚪"}
    sections = [
        ("ADR vs 現況", "adr"),
        ("SOP 遵守度", "sop"),
        ("核心服務真活", "core_services"),
        ("L4x family 反覆", "l4x_family"),
        ("學習閉環健康", "learning_loop"),
        ("觀測閉環真活", "observability"),
        ("已建構資產真活", "built_assets"),
    ]
    for label, key in sections:
        v = report.get(key, {})
        status = v.get("status", "?")
        icon = icons.get(status, "?")
        lines.append(f"### {icon} {label} — {status}")
        for kk, vv in v.items():
            if kk == "status":
                continue
            lines.append(f"- **{kk}**: {vv}")
        lines.append("")

    return "\n".join(lines)


def main(update_baseline: bool = False) -> int:
    print(f"=== Daily Self-Retrospective ({date.today().isoformat()}) ===")
    print()

    # v6.12 補完: 先驗 /metrics endpoint 可達，避誤判 backend down 為 self fitness 問題
    endpoint = metric_endpoint_health()
    if not endpoint["reachable"]:
        print(f"⚠ /metrics endpoint 不可達: {endpoint['error']}")
        print("  → KG / Memory / Governance metrics 將顯示 -1.0 (非真實 RED)")
        print()

    report = {
        "metric_endpoint": endpoint,
        "adr": check_adr_alignment(),
        "sop": check_sop_compliance(),
        "core_services": check_core_services_alive(),
        "l4x_family": check_l4x_family_pattern(),
        "learning_loop": check_learning_loop(),
        "observability": check_observability_alive(),
        "built_assets": check_built_assets_alive(),
    }

    md = render_markdown(report)
    print(md)

    # 寫 daily report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    (REPORTS_DIR / f"{today}.md").write_text(md, encoding="utf-8")
    (REPORTS_DIR / f"{today}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if update_baseline:
        _save_baseline({
            "date": today,
            "l4x_count": report["l4x_family"].get("l4x_count", 0),
            "report_freshness_h": report["observability"].get("report_freshness_hours", -1),
        })
        print(f"\n✓ baseline updated: {today}")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()
    sys.exit(main(update_baseline=args.update_baseline))
