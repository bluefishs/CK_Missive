"""Fitness step 62 (v6.12, L52 lesson): paths.py PROJECT_ROOT vs docker-compose mount audit

偵測 paths.py 算的 PROJECT_ROOT 是否與 docker-compose.*.yml 的 mount target prefix 對齊。

漂移風險:
- paths.py 改 PROJECT_ROOT (host: parents[3], container: env override = /app)
- 但 compose mount 仍指向舊 target (e.g. /scripts 而非 /app/scripts)
- → cron 找 PROJECT_ROOT/scripts/checks/foo.py = /app/scripts/checks/foo.py
- → 不存在 → silent return → silent dormant

設計：靜態分析，不需 backend running。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def detect_container_project_root() -> str | None:
    """從 docker-compose.production.yml 抓 CK_PROJECT_ROOT 設定"""
    compose = ROOT / "docker-compose.production.yml"
    if not compose.exists():
        return None
    text = compose.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"-\s+CK_PROJECT_ROOT=([^\s$]+)", text)
    return m.group(1).strip() if m else None


def extract_mount_targets(compose_path: Path) -> list[tuple[str, str, int]]:
    """抓出所有 `- ./xxx:/yyy[:flag]` 形式的 mount

    回 list of (host_path, container_target, line_no)
    """
    mounts = []
    if not compose_path.exists():
        return mounts
    for i, line in enumerate(compose_path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        # 形如 "      - ./scripts:/app/scripts:ro"
        m = re.match(r"^\s+-\s+(\.\/?[\w\-\.\/]+):(\/[\w\-\.\/]+)(:[a-z]+)?\s*$", line)
        if m:
            mounts.append((m.group(1), m.group(2), i))
    return mounts


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== paths.py vs compose mount target audit (step 62 / L52) ===")

    project_root = detect_container_project_root() or "/app"
    print(f"Container PROJECT_ROOT (from CK_PROJECT_ROOT env): {project_root}")
    print()

    issues = []
    for compose_name in ("docker-compose.production.yml", "docker-compose.dev.yml", "docker-compose.yml"):
        compose_path = ROOT / compose_name
        if not compose_path.exists():
            continue
        mounts = extract_mount_targets(compose_path)
        print(f"{compose_name}: {len(mounts)} mount(s)")
        for host, container, line in mounts:
            # 共享子目錄 prefix (e.g. ./scripts → /app/scripts) 才檢查
            # 純 system path (e.g. ./logs → /logs) 跳過
            if host.startswith("./") and host[2:].split("/")[0] in {"scripts", "wiki", "frontend", "backend", "config", "uploads", "logs"}:
                # 對應 container target 應在 PROJECT_ROOT 下
                # exception: frontend/dist mount /frontend/dist 是 main.py 固定算 path
                if container == "/frontend/dist" or container == "/scripts" and host == "./scripts":
                    pass
                expected_prefix = project_root
                if not container.startswith(expected_prefix) and container not in {"/frontend/dist"}:
                    msg = f"  ⚠ line {line}: {host} → {container} (expected prefix {expected_prefix})"
                    print(msg)
                    issues.append(msg)
                else:
                    print(f"  ✓ line {line}: {host} → {container}")
        print()

    if not issues:
        print("✓ all mounts aligned with PROJECT_ROOT")
        return 0
    print(f"⚠ {len(issues)} mount target drift(s):")
    for i in issues:
        print(i)
    if strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
