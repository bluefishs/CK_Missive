"""Fitness step 68 (v6.12, 2026-05-30): Hermes GO/NO-GO baseline gate 自動裁判

Sprint 3.P3.15 落地 — ADR-0030 GO 門檻自動 audit + LINE 推 owner

5 GO 條件 (ADR-0030):
1. shadow_baseline rows ≥ 30
2. owner dogfooding ≥ 7 連續天 (Hermes Web UI)
3. soul fidelity ≥ 70%
4. error rate < 5%
5. p95 latency < 8s

自動評估:
- 5/5 → ✅ GO (可進入 Phase 1 dogfooding 擴展)
- 3-4/5 → 🟡 NEAR-GO (延 1 month)
- < 3/5 → 🔴 NO-GO

接 daily 06:30 cron (對齊 daily_self_retrospective)
"""
from __future__ import annotations

import sys
import urllib.request


def fetch_metric(name: str) -> float | None:
    """從 /metrics 抓特定 metric，回 None 若不存在"""
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=8) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    for line in text.splitlines():
        if line.startswith(name + "{") or line.startswith(name + " "):
            try:
                return float(line.rsplit(" ", 1)[1])
            except (ValueError, IndexError):
                continue
    return None


def fetch_metric_avg(name: str) -> float | None:
    """取所有 label 變體的平均值（如 p95 跨多 provider）"""
    try:
        with urllib.request.urlopen("http://localhost:8001/metrics", timeout=8) as r:
            text = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    values = []
    for line in text.splitlines():
        if line.startswith(name + "{"):
            try:
                values.append(float(line.rsplit(" ", 1)[1]))
            except (ValueError, IndexError):
                continue
    return sum(values) / len(values) if values else None


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== Hermes GO/NO-GO Baseline Gate Audit (step 68, Sprint 3.P3.15) ===")
    print()

    # 1. baseline rows
    rows = fetch_metric("shadow_baseline_rows_total")
    # 2. dogfooding 暫時 placeholder（待 user_sessions query 實作）
    dogfood_days = 0  # TODO: query user_sessions Hermes Web UI 連續 login
    # 3. soul fidelity 暫 placeholder（待 fidelity_log.jsonl reader 實作）
    fidelity = 0.0  # TODO: read wiki/memory/evolutions/fidelity_log.jsonl 24h avg
    # 4. error rate (1 - success_ratio)
    success = fetch_metric_avg("shadow_baseline_success_ratio") or 0
    error_rate = 1.0 - success
    # 5. p95 latency
    p95_ms = fetch_metric_avg("shadow_baseline_latency_p95_ms") or 0

    # 5 條件評估
    conditions = {
        "1. baseline rows ≥ 30":     (rows is not None and rows >= 30, f"{rows}"),
        "2. dogfooding ≥ 7 days":    (dogfood_days >= 7, f"{dogfood_days} days (TODO)"),
        "3. soul fidelity ≥ 70%":    (fidelity >= 0.70, f"{fidelity*100:.0f}% (TODO)"),
        "4. error rate < 5%":        (error_rate < 0.05, f"{error_rate*100:.1f}%"),
        "5. p95 latency < 8s":       (p95_ms < 8000, f"{p95_ms:.0f}ms"),
    }

    met = sum(1 for ok, _ in conditions.values() if ok)
    print(f"{'Condition':<35} {'Met':<5} {'Actual'}")
    print("-" * 70)
    for cond, (ok, actual) in conditions.items():
        icon = "✅" if ok else "❌"
        print(f"{cond:<35} {icon:<5} {actual}")
    print()
    print(f"Summary: {met}/5 達標")
    print()

    if met == 5:
        print("✅ GO — 5/5 達標，可進入 Phase 1 dogfooding 擴展")
        print("    建議：開放 Web UI Owner + 2 內部 + LINE 白名單 3-5")
        return 0
    elif met >= 3:
        print(f"🟡 NEAR-GO — {met}/5，缺 {5-met} 條件，延 1 month")
        print("    詳見: docs/architecture/HERMES_BASELINE_RESET_PLAN_20260530.md")
        return 0
    else:
        print(f"🔴 NO-GO — {met}/5，需修真因")
        if rows is not None and rows < 5:
            print("    真因 #1: synthetic_baseline cron 未真活 (預期 30/日，實際", rows, ")")
        if p95_ms > 30000:
            print("    真因 #2: p95 過高（Ollama cold start），建議切 groq")
        if strict:
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
