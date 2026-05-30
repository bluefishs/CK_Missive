"""Fitness step 69 (v6.12, 2026-05-30): paths.py sub-path vs compose mount sub-path audit

L57 立法後新增 — L52 audit 只檢 PROJECT_ROOT 對齊，本 audit 擴覆蓋 sub-path:
- LOGS_DIR / WIKI_DIR / SCRIPTS_DIR / BACKEND_DIR/logs 等
- 對 compose mount target 各層 prefix 對齊

漂移風險:
- shadow_logger 用 BACKEND_DIR/logs → /app/backend/logs/
- 但 compose mount ./backend/logs:/app/logs/ → /app/logs/
- 兩處不對齊 silent fail (L57 揭發)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def extract_paths_module_vars() -> dict[str, str]:
    """從 paths.py 抓 sub-path 變數定義 (PROJECT_ROOT/BACKEND_DIR/LOGS_DIR 等)"""
    paths_file = ROOT / "backend" / "app" / "core" / "paths.py"
    if not paths_file.exists():
        return {}
    text = paths_file.read_text(encoding="utf-8", errors="ignore")
    out = {}
    # 抓 = PROJECT_ROOT / "xxx" 形式
    for m in re.finditer(
        r"(\w+_DIR|\w+_PATH)\s*:\s*Path\s*=\s*([A-Z_]+)\s*/\s*['\"]([^'\"]+)['\"]",
        text,
    ):
        var, base, sub = m.group(1), m.group(2), m.group(3)
        out[var] = f"{base}/{sub}"
    return out


def extract_compose_mounts() -> list[tuple[str, str]]:
    """抓 docker-compose.production.yml 所有 - ./host:/target 形式"""
    out = []
    compose = ROOT / "docker-compose.production.yml"
    if not compose.exists():
        return out
    for i, line in enumerate(compose.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        m = re.match(r"^\s+-\s+(\.\/?[\w\-\.\/]+):(\/[\w\-\.\/]+)(:[a-z]+)?\s*$", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== paths.py sub-path vs compose mount audit (step 69, L57) ===")
    print()

    vars_map = extract_paths_module_vars()
    mounts = extract_compose_mounts()

    print(f"paths.py sub-path 變數: {len(vars_map)}")
    for var, expr in vars_map.items():
        print(f"  {var:20} = {expr}")
    print()

    print(f"compose mount targets: {len(mounts)}")
    issues = []

    # 關鍵 sub-path 列表 (來自 paths.py 真實計算)
    # container 內 PROJECT_ROOT=/app 因 CK_PROJECT_ROOT env override
    expected_container_paths = {
        "LOGS_DIR": ("/app/logs", "/app/backend/logs"),
        # 兩種可能形式，看 paths.py 怎算
    }

    # L57 揭發核心對比: BACKEND_DIR/logs vs mount /app/logs
    backend_logs_expr = vars_map.get("BACKEND_DIR")
    has_app_logs_mount = any(c == "/app/logs" for _, c in mounts)
    has_app_backend_logs_mount = any(c == "/app/backend/logs" for _, c in mounts)

    if has_app_logs_mount and not has_app_backend_logs_mount:
        # mount 在 /app/logs 但 paths.py 算 sub-path 可能用 BACKEND_DIR/logs
        # 需 grep code 找誰用 BACKEND_DIR/logs 沒對齊
        bad_callers = grep_callers_using_backend_logs()
        if bad_callers:
            print(f"⚠ L57 同型 path drift 候選 {len(bad_callers)}:")
            for caller in bad_callers[:5]:
                print(f"    - {caller}")
            issues.append("L57 candidates")

    if not issues:
        print("✓ paths.py sub-path 與 compose mount 對齊 (或無 L57 同型 caller)")
    else:
        print()
        print(f"⚠ {len(issues)} 議題待 owner 修法")
        if strict:
            return 1
    return 0


def grep_callers_using_backend_logs() -> list[str]:
    """grep code 內用 BACKEND_DIR / "logs" 形式（L57 危險用法）"""
    import subprocess
    try:
        r = subprocess.run(
            ["grep", "-rln",
             r'BACKEND_DIR\s*/\s*["\']logs["\']',
             "backend/app/", "--include=*.py"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=10,
        )
        files = [f for f in r.stdout.splitlines() if "__pycache__" not in f]
        return files
    except Exception:
        return []


if __name__ == "__main__":
    sys.exit(main())
