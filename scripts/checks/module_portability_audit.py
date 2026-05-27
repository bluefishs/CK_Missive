#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 30 — Module Portability Audit (v6.10 P1, 2026-05-18).

評估指定 module（目錄或檔案）是否可跨 repo 採用，依據業務 keyword 黑名單。

用途：
- shared-modules/ck-auth/ install 前審計（決定能否被 lvrland/pile 採用）
- contracts/ 自檢確認真通用
- 任何新 module 上線前的 portability sanity check

對應規約：
- 整體律定方案 §A 建議 2 shared-modules 化
- adr-anti-half-wired-sop §「過濾性程式碼設計守則」

Exit codes:
  0 — PORTABLE 或 NEEDS_RENAME（warning only）
  1 — NOT_PORTABLE（critical hits > 0 + strict mode）

Usage:
  python scripts/checks/module_portability_audit.py backend/app/services/contracts/
  python scripts/checks/module_portability_audit.py shared-modules/ck-auth/ --strict
  python scripts/checks/module_portability_audit.py path/to/file.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import yaml
except ImportError:
    print("[ERROR] pyyaml not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
KEYWORD_YAML = PROJECT_ROOT / "scripts" / "checks" / "data" / "business_keyword_blacklist.yml"

# 級別 → 分數扣減
LEVEL_PENALTY = {
    "critical": 0.30,
    "high": 0.10,
    "medium": 0.02,
    "domain_specific": 0.0,  # 只報告不扣分
}


def _load_keywords() -> dict:
    if not KEYWORD_YAML.exists():
        raise FileNotFoundError(f"Keyword yaml not found: {KEYWORD_YAML}")
    return yaml.safe_load(KEYWORD_YAML.read_text(encoding="utf-8")) or {}


def _scan_file(path: Path, keywords: dict, base_dir: Path) -> list[dict]:
    """掃單一檔案，回傳 hit list"""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    hits = []
    rel = path.relative_to(base_dir).as_posix() if base_dir in path.parents or base_dir == path else path.name
    for level in ("critical", "high", "medium", "domain_specific"):
        for kw in keywords.get(level, []):
            # case-insensitive，但保留原 keyword 大小寫供 hit 顯示
            for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
                line_no = text[: m.start()].count("\n") + 1
                start = max(0, m.start() - 20)
                end = min(len(text), m.end() + 30)
                context = text[start:end].replace("\n", "\n")
                hits.append({
                    "file": rel,
                    "line": line_no,
                    "level": level,
                    "keyword": kw,
                    "context": context,
                })
    return hits


def audit_module(target_path: Path) -> dict:
    """主審計流程"""
    keywords = _load_keywords()
    target = target_path.resolve()
    if not target.exists():
        return {"verdict": "ERROR", "reason": f"Path not found: {target}"}

    base_dir = target if target.is_dir() else target.parent
    files_to_scan = (
        sorted(target.rglob("*.py")) if target.is_dir() else [target]
    )
    # 過濾掉 __pycache__
    files_to_scan = [f for f in files_to_scan if "__pycache__" not in f.parts]

    all_hits = []
    lines_scanned = 0
    for f in files_to_scan:
        try:
            lines_scanned += len(f.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
        all_hits.extend(_scan_file(f, keywords, base_dir))

    # 統計
    level_counts = defaultdict(int)
    for hit in all_hits:
        level_counts[hit["level"]] += 1

    # 計分（從 1.0 開始扣）
    score = 1.0
    for level, penalty in LEVEL_PENALTY.items():
        score -= level_counts[level] * penalty
    score = max(0.0, score)

    # 判 verdict
    if level_counts["critical"] > 0:
        verdict = "NOT_PORTABLE"
    elif level_counts["high"] > 0:
        verdict = "NEEDS_RENAME"
    elif score < 0.95:
        verdict = "PORTABLE_WITH_NOTES"
    else:
        verdict = "PORTABLE"

    return {
        "module": str(target.relative_to(PROJECT_ROOT) if PROJECT_ROOT in target.parents else target),
        "files_scanned": len(files_to_scan),
        "lines_scanned": lines_scanned,
        "level_counts": dict(level_counts),
        "portability_score": round(score, 3),
        "verdict": verdict,
        "hits": all_hits[:50],  # 限制輸出
        "total_hits": len(all_hits),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 30 — Module Portability Audit")
    parser.add_argument("target", help="Path to module (dir or .py file)")
    parser.add_argument("--strict", action="store_true", help="fail on NOT_PORTABLE")
    parser.add_argument("--json", action="store_true", help="JSON output (for install.sh consumption)")
    args = parser.parse_args()

    result = audit_module(Path(args.target))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        v = result.get("verdict", "ERROR")
        emoji = {"PORTABLE": "[OK]", "PORTABLE_WITH_NOTES": "[NOTE]",
                 "NEEDS_RENAME": "[WARN]", "NOT_PORTABLE": "[FAIL]", "ERROR": "[ERR]"}.get(v, "[?]")
        print("=" * 60)
        print(f"Module Portability Audit — {result.get('module', args.target)}")
        print("=" * 60)
        if v == "ERROR":
            print(f"\n  {emoji} {result.get('reason')}")
            return 2
        print(f"\n  Files scanned:        {result['files_scanned']}")
        print(f"  Lines scanned:        {result['lines_scanned']}")
        print(f"  Total hits:           {result['total_hits']}")
        print(f"")
        for level in ("critical", "high", "medium", "domain_specific"):
            count = result["level_counts"].get(level, 0)
            print(f"    {level:<20} {count}")
        print(f"")
        print(f"  Portability score:    {result['portability_score']:.3f}")
        print(f"  Verdict:              {emoji} {v}")
        print(f"")
        if result["total_hits"] > 0:
            print("  Sample hits:")
            for h in result["hits"][:10]:
                print(f"    L{h['line']:<4} [{h['level']:<14}] {h['file']:<35} '{h['keyword']}'")
                print(f"           ...{h['context']}...")

    if args.strict and result.get("verdict") == "NOT_PORTABLE":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
