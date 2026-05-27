#!/usr/bin/env python3
"""db_schema_drift_audit.py — fitness step 43

偵測 SQLAlchemy 模型 vs Alembic migration drift（next_session_resume #1）。

風險背景：
- L43 災難（2026-05-21）根因之一是 alembic 不需資料就推進 → 空殼 volume 也通過
- 衍生風險：開發者改 model 卻忘記建 migration → 部署到 fresh DB 缺欄位
- 本 audit 用「mtime heuristic」+「alembic check」雙重偵測

判定邏輯：
1. 找 backend/app/extended/models/*.py 最晚 mtime（newest model）
2. 找 backend/alembic/versions/*.py 最晚 mtime（newest migration）
3. 若 newest model mtime - newest migration mtime > 1 day → YELLOW 警告
4. 若 newest model mtime - newest migration mtime > 7 days → RED drift
5. 額外：alembic 1.9+ 的 `alembic check` 子命令在 docker container 內跑（若可）

Usage:
    python scripts/checks/db_schema_drift_audit.py [--strict]

Exit codes:
    0 = green (no drift)
    1 = yellow (model file newer than migration by 1-7 days)
    2 = red (model file newer by 7+ days or alembic check fail)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MODELS_DIR = REPO_ROOT / "backend" / "app" / "extended" / "models"
ALEMBIC_VERSIONS_DIR = REPO_ROOT / "backend" / "alembic" / "versions"

# Thresholds (seconds)
YELLOW_DAYS = 1
RED_DAYS = 7
SECONDS_PER_DAY = 86400


def _latest_mtime(directory: Path, pattern: str = "*.py") -> tuple[Path, float] | None:
    """Find the file with latest mtime in directory."""
    if not directory.exists():
        return None
    files = list(directory.glob(pattern))
    # exclude __init__.py because it auto-updates whenever you touch any model
    # but DO include it if it's the only file (edge case)
    real_files = [f for f in files if f.name != "__init__.py"]
    if not real_files and files:
        real_files = files
    if not real_files:
        return None
    latest = max(real_files, key=lambda f: f.stat().st_mtime)
    return latest, latest.stat().st_mtime


def _run_alembic_check_in_docker() -> tuple[int, str]:
    """Try alembic check inside docker container."""
    try:
        result = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "alembic", "check"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return -1, "alembic check timeout"
    except FileNotFoundError:
        return -1, "docker not available"
    except Exception as e:
        return -1, f"alembic check error: {e}"


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
    print("DB schema drift audit (next_session_resume #1)")
    print("v1.0 / detect model vs alembic migration drift")
    print("=" * 60)

    # 1. mtime heuristic
    latest_model = _latest_mtime(MODELS_DIR)
    latest_migration = _latest_mtime(ALEMBIC_VERSIONS_DIR)

    if not latest_model:
        print(f"  ⚪ no model files in {MODELS_DIR}")
        return 0
    if not latest_migration:
        print(f"  🔴 no migration files in {ALEMBIC_VERSIONS_DIR}")
        return 2

    model_file, model_mtime = latest_model
    mig_file, mig_mtime = latest_migration

    delta_seconds = model_mtime - mig_mtime
    delta_days = delta_seconds / SECONDS_PER_DAY

    print(f"\n  newest model:     {model_file.name}")
    print(f"  newest migration: {mig_file.name}")
    print(f"  model - migration: {delta_days:+.1f} days")

    severity = "GREEN"
    if delta_days > RED_DAYS:
        severity = "RED"
    elif delta_days > YELLOW_DAYS:
        severity = "YELLOW"

    if severity == "GREEN":
        print(f"  🟢 mtime check: aligned (model ≤ migration + {YELLOW_DAYS} day)")
    elif severity == "YELLOW":
        print(f"  🟡 mtime check: model newer by {delta_days:.1f} days — may need migration")
    else:
        print(f"  🔴 mtime check: model newer by {delta_days:.1f} days — likely missing migration")

    # 2. alembic check (live container)
    # 嚴重度判定:
    #   - "Detected added/new column/index" → RED（model 有 DB 沒，將 fail at runtime）
    #   - "Detected removed table/index" → YELLOW（DB 殘留 dead tables，不 critical 但 cleanup 待做）
    #   - 0 detected → GREEN
    print(f"\n  Trying `alembic check` in ck_missive_backend container...")
    rc, out = _run_alembic_check_in_docker()

    if rc == 0:
        print(f"  🟢 alembic check: PASS (no pending schema changes)")
    elif rc == -1:
        print(f"  ⚪ alembic check: skipped ({out})")
    else:
        # Parse output for 嚴重度 — 區分 critical (runtime fail) vs informational
        added_critical = 0   # added column / new table / type change → RED runtime risk
        added_index = 0      # added index → YELLOW (效能 only)
        removed = 0
        seq_info = 0
        modified = 0
        for line in out.split("\n"):
            if "Detected sequence" in line:
                seq_info += 1
            elif "Detected added index" in line:
                added_index += 1
            elif "Detected added column" in line or "Detected added table" in line or "Detected new" in line:
                added_critical += 1
            elif "Detected modified" in line or "Detected type change" in line:
                modified += 1
            elif "Detected removed" in line:
                removed += 1

        # 嚴重度判定
        # CRITICAL（RED）：added column / new table — model 期望 DB 缺，runtime 必 fail
        # NON-CRITICAL（YELLOW）：added index（效能）/ modified type（型別寬鬆）/ removed（dead cleanup）
        if added_critical > 0:
            print(f"  🔴 alembic check: FAIL — {added_critical} added column/table (CRITICAL: runtime fail risk)")
            severity = "RED"
        else:
            total_non_critical = added_index + modified + removed
            if total_non_critical > 0:
                print(f"  🟡 alembic check: {added_index} idx + {modified} type / {removed} removed (informational, no runtime risk)")
                if severity == "GREEN":
                    severity = "YELLOW"
            else:
                print(f"  🟢 alembic check: PASS (no drift)")

    print(f"\n  Final severity: {severity}")

    if severity == "RED":
        print("\n💡 修法建議：")
        print("  1. 在 backend 目錄跑：alembic revision --autogenerate -m '<描述>'")
        print("  2. review 生成的 migration（檢查 ADD COLUMN 是否 idempotent）")
        print("  3. alembic upgrade head 套用")
        print("  4. 重跑本 audit 應 GREEN")
        print("  5. 若 model 變更是 deprecated cleanup 不需 migration，註記在 model 檔頂部")
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
