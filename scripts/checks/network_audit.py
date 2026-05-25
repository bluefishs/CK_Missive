#!/usr/bin/env python3
"""network_audit.py — 跨 repo Docker Network Standard 驗證（fitness step 37）

對應 ADR CK_AaaP#0043 Cross-Repo Docker Network Standard。
驗證 docker-compose.yml 是否符合 4 層分網路 + 命名 SSOT。

Usage:
    python scripts/checks/network_audit.py [--repo=<name>] [--strict]
"""
from __future__ import annotations

import re
import sys
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


REQUIRED_LAYERS = {"frontend", "backend", "worker", "data"}
LAYERS_NEED_INTERNAL = {"worker", "data"}
NAME_PATTERN = re.compile(r"^ck_[a-z0-9]+(?:_[a-z0-9]+)*_(?:frontend|backend|worker|data)_net$")
EXTERNAL_PATTERN = re.compile(r"^ck_platform_[a-z0-9_]+_net$")
LEGACY_BLACKLIST = {"nemoclaw_network", "openclaw_network"}
EXTERNAL_GRANDFATHERED = {"ck_platform_obs_net", "ck_hermes_net", "ck_ollama_net"}


@dataclass
class AuditResult:
    repo_path: Path
    compose_files: list[Path] = field(default_factory=list)
    networks_found: dict[str, dict] = field(default_factory=dict)
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "unknown"


def _find_compose_files(repo_path: Path) -> list[Path]:
    candidates = list(repo_path.glob("docker-compose*.yml"))
    candidates += list(repo_path.glob("docker-compose*.yaml"))
    return [
        p for p in candidates
        if "archive" not in str(p).lower() and "deprecated" not in str(p).lower()
    ]


def _parse_networks(compose_file: Path) -> dict[str, dict]:
    try:
        with compose_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Parse failed: {compose_file.name}: {e}")
        return {}
    if not isinstance(data, dict):
        return {}
    networks = data.get("networks") or {}
    return networks if isinstance(networks, dict) else {}


def _extract_layer(net_name: str) -> Optional[str]:
    for layer in REQUIRED_LAYERS:
        if f"_{layer}_net" in net_name:
            return layer
    return None


def _check_naming(name: str, config: dict, result: AuditResult) -> None:
    actual = (config or {}).get("name") or name
    if actual in LEGACY_BLACKLIST:
        result.violations.append(f"❌ legacy network: '{actual}' (ADR-0015 廢止)")
        return
    if (config or {}).get("external"):
        if EXTERNAL_PATTERN.match(actual) or actual in EXTERNAL_GRANDFATHERED:
            return
        result.warnings.append(f"⚠️  external '{actual}' 不符 ck_platform_*_net pattern")
        return
    if name == "default":
        return
    if not NAME_PATTERN.match(actual):
        result.violations.append(
            f"❌ network '{actual}' 不符 ck_<repo>_<layer>_net pattern"
        )


def _check_internal(name: str, config: dict, result: AuditResult) -> None:
    actual = (config or {}).get("name") or name
    layer = _extract_layer(actual)
    if layer in LAYERS_NEED_INTERNAL and not (config or {}).get("internal"):
        result.violations.append(
            f"❌ '{actual}' (layer={layer}) 必須 internal:true（攻擊面隔離）"
        )


def _check_4layer(result: AuditResult) -> None:
    found = set()
    for name, config in result.networks_found.items():
        actual = (config or {}).get("name") or name
        layer = _extract_layer(actual)
        if layer:
            found.add(layer)
    missing = REQUIRED_LAYERS - found
    if missing and result.networks_found:
        result.warnings.append(f"⚠️  缺 layer: {sorted(missing)}（4 層分網路未完整）")


def _check_obs(result: AuditResult) -> None:
    has_obs = any(
        ((c or {}).get("name") or n) == "ck_platform_obs_net"
        for n, c in result.networks_found.items()
    )
    if not has_obs and result.networks_found:
        result.warnings.append("⚠️  未接 ck_platform_obs_net（觀測棧 scrape）")


def audit_repo(repo_path: Path) -> AuditResult:
    result = AuditResult(repo_path=repo_path)
    result.compose_files = _find_compose_files(repo_path)
    if not result.compose_files:
        result.warnings.append("⚠️  無 docker-compose*.yml")
        result.status = "yellow"
        return result
    for cf in result.compose_files:
        for name, config in _parse_networks(cf).items():
            result.networks_found[name] = config or {}
    for name, config in result.networks_found.items():
        _check_naming(name, config, result)
        _check_internal(name, config, result)
    _check_4layer(result)
    _check_obs(result)
    if result.violations:
        result.status = "red"
    elif result.warnings:
        result.status = "yellow"
    else:
        result.status = "green"
    return result


def main() -> int:
    import argparse
    # Force UTF-8 stdout for Windows cp950 console (L45 family fix)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Specific repo path")
    parser.add_argument("--strict", action="store_true", help="Exit 2 on violations")
    args = parser.parse_args()

    if args.repo:
        repos = [Path(args.repo).resolve()]
    else:
        anchor = Path(__file__).resolve().parent.parent.parent
        parent = anchor.parent
        repos = sorted([
            p for p in parent.iterdir()
            if p.is_dir() and p.name.startswith(("CK_", "hermes"))
            and any(p.glob("docker-compose*.yml"))
        ])

    if not repos:
        print("❌ No repos found")
        return 2

    print(f"🔍 Auditing {len(repos)} repo(s)... (ADR CK_AaaP#0043)\n")
    results = [audit_repo(p) for p in repos]
    red = yellow = green = 0
    for r in results:
        emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(r.status, "❓")
        print(f"{emoji} {r.repo_path.name}: {r.status.upper()} "
              f"({len(r.networks_found)} networks, "
              f"{len(r.violations)} violations, {len(r.warnings)} warnings)")
        for v in r.violations:
            print(f"    {v}")
        for w in r.warnings:
            print(f"    {w}")
        if r.status == "red":
            red += 1
        elif r.status == "yellow":
            yellow += 1
        else:
            green += 1

    print(f"\n=== Summary ===")
    print(f"  🟢 GREEN: {green} / 🟡 YELLOW: {yellow} / 🔴 RED: {red}")
    print(f"  ADR: CK_AaaP#0043 / Registry: CK_AaaP/runbooks/docker-network-registry.md")

    if args.strict and red > 0:
        return 2
    return 1 if (red + yellow) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
