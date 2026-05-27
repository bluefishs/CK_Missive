#!/usr/bin/env python3
"""startup_dependency_race_audit.py — fitness step 47

偵測 docker-compose depends_on 缺 condition: service_healthy 的 startup race 風險
（v6.12 P3 forward-looking）。

風險背景：
- naïve `depends_on: - postgres` 只等 postgres container start，不等 healthy
- backend 啟動時 postgres 可能還在 init.sql 階段 → connection refused
- L43 災難中 alembic 不需資料就推進是同源 silent fail 模式
- 修法：所有 critical depends_on 必須用 dict 形式 + condition: service_healthy

判定邏輯：
1. 掃所有 docker-compose*.yml（排除 archive / deprecated）
2. 解析 services.*.depends_on
3. 若 depends_on 是 list 形式（naïve）→ YELLOW（dev tools 可接受）
4. 若 depends_on 是 dict 但缺 condition → YELLOW
5. 若 depends_on 用 condition: service_healthy → GREEN
6. 若 depends_on 缺失但 service 邏輯上需要 → audit 偵測不到（需 manual review）

Usage:
    python scripts/checks/startup_dependency_race_audit.py [--strict]

Exit codes:
    0 = green (all depends_on with service_healthy condition)
    1 = yellow (naïve list depends_on or missing condition)
    2 = red (--strict 時 yellow 也 exit 2)
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class DependsOnEntry:
    compose_file: Path
    service: str
    target: str
    form: str   # "list" or "dict"
    condition: str | None  # "service_healthy" / "service_started" / None


def _scan_compose(compose_path: Path) -> list[DependsOnEntry]:
    """Parse depends_on from a compose file."""
    try:
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    services = data.get("services") or {}
    results: list[DependsOnEntry] = []
    for svc_name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        deps = svc.get("depends_on")
        if not deps:
            continue
        # List form: depends_on: [postgres, redis]
        if isinstance(deps, list):
            for target in deps:
                results.append(DependsOnEntry(
                    compose_file=compose_path,
                    service=svc_name,
                    target=str(target),
                    form="list",
                    condition=None,
                ))
        # Dict form: depends_on: {postgres: {condition: service_healthy}}
        elif isinstance(deps, dict):
            for target, target_cfg in deps.items():
                if isinstance(target_cfg, dict):
                    cond = target_cfg.get("condition")
                    results.append(DependsOnEntry(
                        compose_file=compose_path,
                        service=svc_name,
                        target=target,
                        form="dict",
                        condition=cond,
                    ))
                else:
                    results.append(DependsOnEntry(
                        compose_file=compose_path,
                        service=svc_name,
                        target=target,
                        form="dict-bare",
                        condition=None,
                    ))
    return results


def main() -> int:
    # Force UTF-8 stdout for Windows cp950 console
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    args = parser.parse_args()

    print("=" * 60)
    print("Startup dependency race audit (v6.12 P3)")
    print("v1.0 / detect naïve depends_on race risk")
    print("=" * 60)

    composes = sorted(REPO_ROOT.glob("docker-compose*.yml"))
    composes = [p for p in composes if "archive" not in p.parts and "deprecated" not in p.parts]

    if not composes:
        print("  no docker-compose*.yml found")
        return 0

    all_entries: list[DependsOnEntry] = []
    for cp in composes:
        all_entries.extend(_scan_compose(cp))

    healthy = [e for e in all_entries if e.condition == "service_healthy"]
    started = [e for e in all_entries if e.condition == "service_started"]
    naive_list = [e for e in all_entries if e.form == "list"]
    bare_dict = [e for e in all_entries if e.form == "dict-bare"]

    print(f"\n  composes scanned:        {len(composes)}")
    print(f"  total depends_on edges:  {len(all_entries)}")
    print(f"  🟢 service_healthy:      {len(healthy)}")
    print(f"  🟡 service_started:      {len(started)}")
    print(f"  🟡 naïve list form:      {len(naive_list)}")
    print(f"  🟡 dict but no condition: {len(bare_dict)}")

    if naive_list:
        print(f"\n  🟡 naïve list depends_on (race risk):")
        for e in naive_list:
            rel = e.compose_file.relative_to(REPO_ROOT)
            print(f"    {rel}: {e.service} → {e.target}")

    if bare_dict:
        print(f"\n  🟡 dict form but missing condition:")
        for e in bare_dict:
            rel = e.compose_file.relative_to(REPO_ROOT)
            print(f"    {rel}: {e.service} → {e.target}")

    if started:
        print(f"\n  🟡 condition: service_started (only starts container, not health):")
        for e in started:
            rel = e.compose_file.relative_to(REPO_ROOT)
            print(f"    {rel}: {e.service} → {e.target}")

    severity = "GREEN"
    risk_count = len(naive_list) + len(bare_dict) + len(started)
    if risk_count > 0:
        severity = "YELLOW"

    print(f"\n  Final severity: {severity}")
    print(f"  Race risk edges: {risk_count} / {len(all_entries)}")

    if severity == "YELLOW":
        print("\n💡 修法建議：")
        print("  把所有 depends_on 改為 dict 形式 + condition: service_healthy:")
        print("    depends_on:")
        print("      postgres:")
        print("        condition: service_healthy")
        print("  確認對應 service 有 HEALTHCHECK 指令（否則 healthy 永遠假）")
        print("  ※ dev tools (adminer/pgadmin) 用 service_started 可接受")

    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
