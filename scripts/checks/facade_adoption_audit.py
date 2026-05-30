"""Facade Adoption Audit (P1.7 / fitness step 61, 2026-05-30)

L51.7 覆盤揭發: v6.10 P1 Phase B 12 facades 平均 importer = 1.7（含 contracts 內部）
業務 code 實際 0 importer，孤兒 facade 反模式。

設計：
- 計算 12 facades 各自被 business code import 次數（排除 /contracts/ 內部）
- 月 baseline 寫 wiki/memory/facade_adoption_baseline.json
- 追蹤趨勢（增量 vs 月初）

informational only — 不入 strict fail（facade 收口為 v6.12 規劃）

Usage:
  python scripts/checks/facade_adoption_audit.py
  python scripts/checks/facade_adoption_audit.py --update-baseline  # 月初跑一次
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


FACADES = [
    "CalendarFacade", "ContractFacade", "DocumentFacade", "IntegrationFacade",
    "NotificationFacade", "AgencyFacade", "VendorFacade", "AIFacade",
    "MemoryFacade", "ERPFacade", "WikiFacade", "AuditFacade", "TenderFacade",
]


def count_importers(facade: str) -> int:
    """計算 facade 在 business code 內被 import 次數（排除 /contracts/ 內部）"""
    try:
        # grep -rlnE: list files containing pattern (extended regex)
        result = subprocess.run(
            ["grep", "-rlnE",
             f"from app.services.contracts.facades.*import.*{facade}|"
             f"from app.services.contracts.facades import.*{facade}",
             "backend/app/", "--include=*.py"],
            capture_output=True, text=True, timeout=10,
        )
        files = result.stdout.strip().splitlines() if result.returncode == 0 else []
        # 排除 contracts 內部 + __pycache__
        files = [f for f in files
                 if "__pycache__" not in f
                 and "/contracts/" not in f]
        return len(files)
    except Exception:
        return 0


def load_baseline() -> dict:
    """讀月 baseline (wiki/memory/facade_adoption_baseline.json)"""
    p = Path("wiki/memory/facade_adoption_baseline.json")
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_baseline(data: dict) -> None:
    """寫月 baseline"""
    p = Path("wiki/memory/facade_adoption_baseline.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main(update_baseline: bool = False) -> int:
    print("=== Facade Adoption Audit (P1.7 / fitness step 61) ===")
    print(f"  date: {date.today().isoformat()}")
    print()

    current = {f: count_importers(f) for f in FACADES}
    total = sum(current.values())
    avg = total / len(FACADES) if FACADES else 0

    baseline = load_baseline()
    baseline_total = sum(baseline.get("counts", {}).values()) if baseline else 0
    baseline_date = baseline.get("date", "(none)")

    print(f"{'Facade':<24} {'Current':<10} {'Baseline':<10} {'Delta':<10}")
    print("─" * 60)
    for f in FACADES:
        cur = current[f]
        base = baseline.get("counts", {}).get(f, 0)
        delta = cur - base
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        marker = "🔴" if cur == 0 else ("🟢" if cur >= 3 else "🟡")
        print(f"  {marker} {f:<22} {cur:<10} {base:<10} {delta_str:<10}")

    print("─" * 60)
    print(f"  Total importers:  {total} (baseline: {baseline_total})")
    print(f"  Avg per facade:   {avg:.2f}")
    print(f"  Baseline date:    {baseline_date}")
    print()

    # 統計 health
    zero_count = sum(1 for c in current.values() if c == 0)
    low_count = sum(1 for c in current.values() if 0 < c < 3)
    healthy_count = sum(1 for c in current.values() if c >= 3)

    print(f"Health: {zero_count} zero / {low_count} low (<3) / {healthy_count} healthy (≥3)")
    print()

    if avg >= 3:
        print("✅ GREEN: 平均 ≥3 importer per facade")
    elif avg >= 1:
        print("🟡 YELLOW: 平均 1-3 importer，仍有 facade 孤兒")
    else:
        print("🔴 RED: 平均 <1 importer，多數 facade 業務 code 沒用")
    print()
    print("提升路線: docs/architecture/FACADE_ADOPTION_GUIDE_20260530.md")

    if update_baseline:
        save_baseline({
            "date": date.today().isoformat(),
            "counts": current,
            "total": total,
            "avg": avg,
        })
        print(f"\n✓ baseline updated: {date.today().isoformat()}")

    return 0  # informational only, never fails


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-baseline", action="store_true",
                        help="Update wiki/memory/facade_adoption_baseline.json (月初跑)")
    args = parser.parse_args()
    sys.exit(main(update_baseline=args.update_baseline))
