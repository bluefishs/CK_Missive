#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 35 - Manifest Drift Audit (v6.10 P1 + LR-015/L33 配套, 2026-05-18).

對齊 lvrland 端 #4 要求 — module_portability_audit v1.1 之 manifest_drift 子模組。

偵測 shared-modules/{pkg}/ 內：
  - 實際存在的檔 vs manifest.yml 內列出的檔（差異 → drift）
  - manifest schema_version (應 >= 1.1，L33 後)
  - transitive_dependencies 欄位是否填寫
  - 4 件齊備 real_adoption_criteria 欄位是否存在

依據:
  - lvrland 回饋 #4 要求 (manifest_drift detection)
  - L33 lesson (Transitive Deps 缺失必致 Half-Wired)
  - ck-modular-toolkit/templates/manifest.template.yml v1.1

Exit codes:
  0 - 全 OK
  1 - strict mode + drift
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml required", file=sys.stderr)
    sys.exit(2)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHARED_MODULES = PROJECT_ROOT / "shared-modules"


def audit_manifest(pkg_path: Path) -> dict:
    manifest_path = pkg_path / "manifest.yml"
    if not manifest_path.exists():
        return {"package": pkg_path.name, "error": "manifest.yml not found"}
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"package": pkg_path.name, "error": f"YAML parse error: {e}"}

    issues = []

    # Check 1: schema version
    schema_ver = manifest.get("manifest_schema_version", 1.0)
    if isinstance(schema_ver, (int, float)) and schema_ver < 1.1:
        issues.append({
            "type": "schema_version_outdated",
            "current": schema_ver,
            "required": 1.1,
            "fix": "Upgrade manifest_schema_version to 1.1 (含 transitive_dependencies)",
        })

    # Check 2: transitive_dependencies 必填（L33）
    if "transitive_dependencies" not in manifest:
        issues.append({
            "type": "missing_transitive_deps",
            "fix": "Add transitive_dependencies field per L33 / manifest.template.yml v1.1",
        })

    # Check 3: real_adoption_criteria 必填（ADR-0036 §Lessons）
    if "real_adoption_criteria" not in manifest:
        issues.append({
            "type": "missing_real_adoption_criteria",
            "fix": "Add real_adoption_criteria field (install + 編譯 + 啟動 + hook 4 件)",
        })

    # Check 4: 實際檔 vs manifest 內列出檔
    listed_files = []
    files_section = manifest.get("files", {})
    for layer in files_section.values():  # backend / frontend
        if not isinstance(layer, dict):
            continue
        for category in layer.values():
            if isinstance(category, dict):
                source_dir = category.get("source", "")
                file_list = category.get("files", [])
                for f in file_list:
                    if f and source_dir:
                        listed_files.append(source_dir.rstrip("/") + "/" + f)

    actual_files = []
    for f in pkg_path.rglob("*"):
        if "__pycache__" in f.parts or "_meta" in f.parts:
            continue
        if not f.is_file():
            continue
        if f.suffix not in (".py", ".ts", ".tsx", ".d.ts"):
            continue
        rel = f.relative_to(pkg_path).as_posix()
        actual_files.append(rel)

    # Compute drift
    listed_set = {x.lstrip("/") for x in listed_files}
    actual_set = set(actual_files)

    unlisted = sorted(actual_set - listed_set)
    missing_actual = sorted(listed_set - actual_set)

    if unlisted:
        issues.append({
            "type": "unlisted_files",
            "count": len(unlisted),
            "samples": unlisted[:5],
            "fix": "Add to manifest.files.{backend|frontend}.{category}.files",
        })
    if missing_actual:
        issues.append({
            "type": "missing_actual_files",
            "count": len(missing_actual),
            "samples": missing_actual[:5],
            "fix": "Either remove from manifest or restore file",
        })

    return {
        "package": pkg_path.name,
        "schema_version": schema_ver,
        "issues": issues,
        "total_issues": len(issues),
        "actual_files_count": len(actual_files),
        "listed_files_count": len(listed_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 35 - Manifest Drift Audit")
    parser.add_argument("target", nargs="?", default=None,
                        help="Package path (default: scan all shared-modules/ck-*)")
    parser.add_argument("--ci", action="store_true", help="strict mode")
    args = parser.parse_args()

    targets = []
    if args.target:
        targets = [Path(args.target).resolve()]
    elif SHARED_MODULES.exists():
        targets = [d for d in SHARED_MODULES.iterdir()
                   if d.is_dir() and d.name.startswith("ck-")]

    total_issues = 0
    for pkg in targets:
        report = audit_manifest(pkg)
        print("=" * 60)
        print(f"Manifest Drift Audit - {report['package']}")
        print("=" * 60)
        if "error" in report:
            print(f"  [ERR] {report['error']}")
            continue
        print(f"  Schema version: {report['schema_version']}")
        print(f"  Listed files:   {report['listed_files_count']}")
        print(f"  Actual files:   {report['actual_files_count']}")
        print(f"  Total issues:   {report['total_issues']}")
        total_issues += report["total_issues"]
        for issue in report["issues"]:
            print(f"\n  [{issue['type']}]")
            for k, v in issue.items():
                if k == "type":
                    continue
                if isinstance(v, list):
                    print(f"    {k}: {v[:3]}{'...' if len(v) > 3 else ''}")
                else:
                    print(f"    {k}: {v}")
        print("")

    print("=" * 60)
    print(f"TOTAL ISSUES: {total_issues}")
    print("=" * 60)

    if args.ci and total_issues > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
