"""Container image freshness check (L51.7.1 / fitness step 60, 2026-05-30)

L51 incident 揭發: docker cp 修法不持久，image 內檔過舊導致 5 防護層
silent disabled 36h。本 check 自動偵測 host 與 container 內檔 hash drift，
強迫 rebuild image 才能標 OK。

設計：
- 對 N 個 critical backend 檔做 md5 比對 host vs container
- 任一 drift → RED
- container 未起 → SKIP (informational)
- 預設不入 strict fail（dev 環境可能沒 docker）

Usage:
  python scripts/checks/container_image_freshness_check.py
  python scripts/checks/container_image_freshness_check.py --strict
  python scripts/checks/container_image_freshness_check.py --container=ck_missive_backend
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


CRITICAL_FILES = [
    "main.py",
    "app/core/scheduler.py",
    "app/core/memory_wiki_metrics.py",
    "app/services/contracts/adapters/messaging_default.py",
    "app/services/tender/business_recommendation.py",
    "app/api/endpoints/auth/common.py",
    "app/api/endpoints/auth/profile.py",
    "app/api/endpoints/tender_module/search.py",
    "app/api/endpoints/tender_module/enrichment_review.py",
    "app/services/tender/enrichment.py",
    "app/services/tender/metrics.py",
]


def host_md5(path: Path) -> str:
    """計算 host 檔案 md5（前 8 chars）"""
    if not path.exists():
        return ""
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def container_md5(container: str, path: str) -> str:
    """從 container 內取檔 md5（直接 read 內容算 md5，避 docker exec md5sum 路徑轉換）"""
    try:
        # cat 比 md5sum 更可靠（不會被 git bash 路徑轉換影響）
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"  # git bash protection
        result = subprocess.run(
            ["docker", "exec", container, "cat", path],
            capture_output=True, timeout=10, env=env,
        )
        if result.returncode != 0:
            return ""
        h = hashlib.md5()
        h.update(result.stdout)
        return h.hexdigest()
    except Exception:
        return ""


def main(strict: bool = False, container: str = "ck_missive_backend") -> int:
    print(f"=== Container Image Freshness Check (L51.7.1 / fitness step 60) ===")
    print(f"  container: {container}")

    # 確認 container 在跑
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0 or "true" not in result.stdout:
            print(f"  [SKIP] container {container} not running")
            return 0
    except Exception:
        print(f"  [SKIP] docker not available")
        return 0

    print()
    drift_count = 0
    missing_count = 0
    match_count = 0

    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"

    for rel_path in CRITICAL_FILES:
        host_path = backend_dir / rel_path
        cont_path = f"/app/{rel_path}"

        host_hash = host_md5(host_path)
        cont_hash = container_md5(container, cont_path)

        if not host_hash:
            print(f"  ?  {rel_path}: host file missing")
            missing_count += 1
        elif not cont_hash:
            print(f"  ?  {rel_path}: container file missing or unreadable")
            missing_count += 1
        elif host_hash == cont_hash:
            print(f"  ✓  {rel_path}")
            match_count += 1
        else:
            print(f"  ✗  {rel_path}  DRIFT (host={host_hash[:10]} cont={cont_hash[:10]})")
            drift_count += 1

    print()
    print(f"Summary: {match_count} match, {drift_count} drift, {missing_count} missing")

    if drift_count > 0:
        print()
        print("⚠ Image vs Source drift detected (L51 incident 同型)")
        print("  原因可能: docker cp 修法未跟 rebuild image")
        print("  修法: docker compose -f docker-compose.production.yml build backend")
        print("        docker compose -f docker-compose.production.yml up -d backend")
        if strict:
            return 1
    elif match_count >= len(CRITICAL_FILES) - 1:  # 容忍 1 個 missing
        print("✅ Image 與 source 對齊")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--container", default="ck_missive_backend")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict, container=args.container))
