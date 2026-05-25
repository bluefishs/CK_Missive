#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 31 - Naming Convention Audit (v6.10 P1 Phase A, 2026-05-18).

Per docs/architecture/NAMING_CONVENTIONS.md v1.0, auto-detect naming violations.

8 categories:
  1. Python module filename PascalCase (should be snake_case)
  2. ABC class not ending with Port
  3. shared-modules/* not starting with ck-
  4. env var missing namespace
  5. API endpoint underscore (should be kebab-case)
  6. DB table singular / PascalCase (Phase D)
  7. Frontend component non-PascalCase.tsx (Phase D)
  8. FQID missing source repo prefix (Phase D)

v6.10 transition: most violations are warnings; v6.11 upgrade to error.

Exit codes:
  0 - pass or warnings only
  1 - strict mode + error-level violations
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend" / "app"
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "src"
SHARED_MODULES_DIR = PROJECT_ROOT / "shared-modules"
ENV_FILE = PROJECT_ROOT / ".env.example"

# Env var allowed without namespace (business-specific, not cross-repo)
ENV_BUSINESS_WHITELIST = {
    "TAOYUAN_", "MORNING_REPORT_", "MISSIVE_", "EZBID_", "PCC_",
    "WIKI_", "AGENT_", "MEMORY_", "GROQ_", "NVIDIA_", "OLLAMA_",
    "POSTGRES_", "REDIS_", "TELEGRAM_", "LINE_", "DISCORD_", "GOOGLE_",
    # v6.11+ GOOGLE_/LINE_ etc. auth-related must move to CKAUTH_*
    "PYTHON", "DATABASE_URL", "SECRET_KEY", "JWT_", "DEBUG", "LOG_LEVEL",
    "SHADOW_", "AUTH_", "DEVELOPMENT_", "PRODUCTION_", "TZ", "NODE_",
    "CKAUTH_", "CKOBS_", "CKPATHS_", "CK_",  # namespace-prefixed
    # Docker / compose / infrastructure (cross-repo neutral)
    "COMPOSE_", "FRONTEND_", "BACKEND_", "ADMINER_", "VITE_",
    "ENVIRONMENT", "PROJECT_VERSION", "PROJECT_NAME",
    # Algorithm / token (常見 namespace-neutral)
    "ALGORITHM", "ACCESS_TOKEN_", "REFRESH_TOKEN_",
    # AI/ML 通用配置
    "EMBEDDING_", "LLM_", "MODEL_", "VLLM_",
    # Telemetry
    "PROMETHEUS_", "GRAFANA_", "LOKI_", "PROMTAIL_",
}

NAMING_CONVENTIONS_DOC = "docs/architecture/NAMING_CONVENTIONS.md"

# Legacy ABC whitelist (non-Port-suffix ABC allowed to remain)
ABC_LEGACY_WHITELIST = {
    "BaseAIService", "BaseRepository", "BaseService",
    "ImportBaseService", "AuditableServiceMixin",
}


def _check_python_module_filename() -> list[dict]:
    violations = []
    for f in BACKEND_DIR.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        name = f.stem
        if name.startswith("_"):
            continue
        if re.match(r"^[A-Z]", name) and re.search(r"[A-Z]", name[1:]):
            violations.append({
                "level": "warning",
                "category": "python_module_filename",
                "file": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "issue": f"PascalCase filename '{name}.py' - should be snake_case",
                "rule": "NAMING-1 Python module snake_case",
            })
    return violations


def _check_abc_port_suffix() -> list[dict]:
    violations = []
    abc_pattern = re.compile(r"class\s+(\w+)\([^)]*ABC[^)]*\):")
    for f in BACKEND_DIR.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in abc_pattern.finditer(text):
            class_name = m.group(1)
            if class_name in ABC_LEGACY_WHITELIST:
                continue
            if class_name.endswith("Port"):
                continue
            line_no = text[: m.start()].count("\n") + 1
            violations.append({
                "level": "warning",
                "category": "abc_port_suffix",
                "file": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "line": line_no,
                "issue": f"ABC class '{class_name}' not ending with 'Port'",
                "rule": "NAMING-1 ABC Interface *Port suffix",
            })
    return violations


def _check_shared_modules_ck_prefix() -> list[dict]:
    violations = []
    if not SHARED_MODULES_DIR.exists():
        return []
    for d in SHARED_MODULES_DIR.iterdir():
        if not d.is_dir():
            continue
        if d.name.startswith("."):
            continue
        if not d.name.startswith("ck-"):
            violations.append({
                "level": "error",
                "category": "shared_modules_ck_prefix",
                "file": f"shared-modules/{d.name}",
                "issue": f"shared module '{d.name}' must start with 'ck-'",
                "rule": "NAMING-2 shared package ck-{kebab}",
            })
    return violations


def _check_env_var_namespace() -> list[dict]:
    violations = []
    if not ENV_FILE.exists():
        return []
    try:
        text = ENV_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", line)
        if not m:
            continue
        var = m.group(1)
        if any(var.startswith(prefix) for prefix in ENV_BUSINESS_WHITELIST):
            continue
        violations.append({
            "level": "warning",
            "category": "env_namespace",
            "file": ".env.example",
            "line": i,
            "issue": f"env var '{var}' missing namespace prefix",
            "rule": "NAMING-3 Env Var Namespace",
        })
    return violations


def _check_api_endpoint_kebab() -> list[dict]:
    violations = []
    pattern = re.compile(r"@router\.(?:get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")
    endpoints_dir = BACKEND_DIR / "api" / "endpoints"
    if not endpoints_dir.exists():
        return []
    for f in endpoints_dir.rglob("*.py"):
        if "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in pattern.finditer(text):
            path = m.group(1)
            segments = [s for s in path.split("/") if s and not s.startswith("{")]
            for seg in segments:
                if "_" in seg:
                    line_no = text[: m.start()].count("\n") + 1
                    violations.append({
                        "level": "warning",
                        "category": "api_endpoint_kebab",
                        "file": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "line": line_no,
                        "issue": f"endpoint segment '{seg}' uses underscore",
                        "rule": "NAMING-5 API Endpoint kebab-case",
                    })
                    break
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 31 - Naming Convention Audit")
    parser.add_argument("--ci", action="store_true", help="strict - fail on error level")
    parser.add_argument("--category", help="run single category")
    args = parser.parse_args()

    all_checks = {
        "python_module": _check_python_module_filename,
        "abc_port": _check_abc_port_suffix,
        "shared_ck": _check_shared_modules_ck_prefix,
        "env_ns": _check_env_var_namespace,
        "api_kebab": _check_api_endpoint_kebab,
    }
    if args.category:
        if args.category not in all_checks:
            print(f"[ERR] Unknown category: {args.category}", file=sys.stderr)
            return 2
        all_violations = all_checks[args.category]()
    else:
        all_violations = []
        for check_fn in all_checks.values():
            all_violations.extend(check_fn())

    by_level = defaultdict(int)
    by_category = defaultdict(int)
    for v in all_violations:
        by_level[v["level"]] += 1
        by_category[v["category"]] += 1

    print("=" * 60)
    print(f"Naming Convention Audit - per {NAMING_CONVENTIONS_DOC}")
    print("=" * 60)
    print(f"\n  Total violations: {len(all_violations)}")
    print(f"    error:   {by_level['error']}")
    print(f"    warning: {by_level['warning']}")
    print(f"\n  By category:")
    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"    {cat:<28} {count}")

    if all_violations:
        print(f"\n  Sample violations (first 15):")
        for v in all_violations[:15]:
            loc = v.get("file", "") + (f":{v['line']}" if v.get("line") else "")
            print(f"    [{v['level']:<7}] [{v['category']:<22}] {loc}")
            print(f"            {v['issue']}")

    has_error = by_level.get("error", 0) > 0
    if args.ci and has_error:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
