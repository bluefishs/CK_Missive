#!/usr/bin/env python3
"""container_lifecycle_audit.py — fitness step 44

偵測 docker container image tag drift（next_session_resume 8 大根因 #4）。

風險背景：
- cloudflared / postgres / redis 用 `:latest` tag → silent upgrade
  - 2026-04-21 chronic QUIC timeout 即因 cloudflared latest 升版觸發
- 不同 repo 用不同版本 cloudflared → 跨 repo 行為不一致
- 修法：所有 production image 必須 pin 明確版本 + 跨 repo 對齊

判定邏輯：
1. 掃 docker ps 取得所有 running container 的 image
2. 掃所有 CK_* repos 的 docker-compose*.yml 找 image: 宣告
3. 對每個 image：
   - 若 tag = `latest` 或無 tag → RED（silent upgrade risk）
   - 若 tag 是 sha256 digest → GREEN（強 immutable）
   - 若 tag 是版本號（e.g. 2026.5.0）→ GREEN
4. 同一 image（如 cloudflare/cloudflared）跨 repo 版本不一致 → YELLOW

Usage:
    python scripts/checks/container_lifecycle_audit.py [--strict]

Exit codes:
    0 = green (no latest tags, versions aligned)
    1 = yellow (cross-repo version drift)
    2 = red (latest tag in use)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Focus image families (跨 repo 治理重點)
KEY_IMAGES = {
    "cloudflare/cloudflared",   # L43 antecedent (chronic QUIC timeout 2026-04-21)
    "postgres",                  # L43 主角 (volume drift)
    "redis",
    "nginx",
}

# Local build image patterns — :latest 是合理模式，跳過 latest 警告
LOCAL_IMAGE_PATTERNS = [
    re.compile(r"^ck[_-]"),          # ck_missive_backend, ck-tunnel-api 等
    re.compile(r"^pile[-_]"),        # pile-cloudflared etc
    re.compile(r"^ck-"),             # ck-hermes-gateway etc
]


def _is_local_image(image_name: str) -> bool:
    """Detect local-build image (no namespace prefix, or known internal pattern)."""
    family = image_name.split(":")[0]
    # No "/" means single-name image (typical local build)
    if "/" not in family:
        for p in LOCAL_IMAGE_PATTERNS:
            if p.match(family):
                return True
        # Unknown single-name image — still treat as local if matches typical pattern
        if re.match(r"^[a-z_][a-z_0-9-]+$", family) and not family in {"postgres", "redis", "nginx", "ubuntu", "alpine", "debian"}:
            return True
    return False

_IMAGE_LINE = re.compile(r"image:\s*[\"']?([^\s\"']+)[\"']?")


def _find_repos(start: Path) -> list[Path]:
    """Find CK_* repos starting from CK_Missive's parent."""
    parent = start.resolve().parent
    return sorted([
        p for p in parent.iterdir()
        if p.is_dir() and p.name.startswith(("CK_", "hermes"))
    ])


def _parse_image(image_str: str) -> tuple[str, str]:
    """Split 'repo/name:tag' or 'repo/name@sha256:...' into (image_family, tag)."""
    if "@sha256:" in image_str:
        family, _, digest = image_str.partition("@sha256:")
        return family, f"sha256:{digest[:12]}"
    if ":" in image_str:
        family, _, tag = image_str.rpartition(":")
        return family, tag
    return image_str, "latest"  # implicit latest


def _running_containers() -> list[tuple[str, str]]:
    """Return [(container_name, image), ...] from `docker ps`."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}"],
            capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    rows = []
    for line in (result.stdout or "").strip().split("\n"):
        if "\t" in line:
            name, image = line.split("\t", 1)
            rows.append((name.strip(), image.strip()))
    return rows


def _scan_compose_images(repo: Path) -> list[tuple[Path, str]]:
    """Scan docker-compose*.yml for image: declarations."""
    rows = []
    for p in sorted(repo.glob("docker-compose*.yml")):
        if "archive" in p.parts or "deprecated" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _IMAGE_LINE.finditer(text):
            rows.append((p, m.group(1)))
    return rows


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
    print("Container lifecycle audit (8 根因 #4)")
    print("v1.0 / detect :latest tags + cross-repo version drift")
    print("=" * 60)

    repos = _find_repos(REPO_ROOT)

    # 1. Scan running containers
    running = _running_containers()
    latest_running: list[tuple[str, str]] = []  # (container_name, image)
    for name, img in running:
        _, tag = _parse_image(img)
        if tag in {"latest", ""} and not _is_local_image(img):
            latest_running.append((name, img))

    # 2. Scan compose declarations across repos
    family_to_versions: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    latest_in_compose: list[tuple[Path, str]] = []
    for repo in repos:
        for cpath, img in _scan_compose_images(repo):
            family, tag = _parse_image(img)
            if tag in {"latest", ""}:
                if not _is_local_image(img):
                    latest_in_compose.append((cpath, img))
                continue
            # Track only KEY_IMAGES across repo for drift detection
            family_short = family.split("/")[-1] if "/" in family else family
            if family in KEY_IMAGES or family_short in KEY_IMAGES:
                family_to_versions[family][tag].append(cpath)

    # 3. Report
    severity = "GREEN"

    print(f"\n  repos scanned:      {len(repos)}")
    print(f"  running containers: {len(running)}")
    print(f"  compose 內 :latest: {len(latest_in_compose)}")
    print(f"  running :latest:    {len(latest_running)}\n")

    # RED: :latest in running containers
    if latest_running:
        print(f"  🔴 running container with :latest tag ({len(latest_running)}):")
        for name, img in latest_running:
            print(f"    {name}: {img}")
        severity = "RED"

    if latest_in_compose:
        print(f"\n  🔴 compose 宣告 :latest（{len(latest_in_compose)}）:")
        for cpath, img in latest_in_compose:
            rel = cpath.relative_to(REPO_ROOT.parent)
            print(f"    {rel}: {img}")
        severity = "RED"

    # YELLOW: cross-repo version drift for key images
    cross_repo_drift = False
    print(f"\n  Key image cross-repo version check:")
    for family, versions in sorted(family_to_versions.items()):
        if len(versions) > 1:
            cross_repo_drift = True
            print(f"  🟡 {family}: DRIFT — {len(versions)} different versions:")
            for tag, paths in sorted(versions.items()):
                for p in paths:
                    rel = p.relative_to(REPO_ROOT.parent)
                    print(f"      {tag:<20}  {rel}")
        else:
            (tag,) = versions.keys()
            print(f"  🟢 {family}: aligned ({tag}, used in {sum(len(v) for v in versions.values())} compose)")

    if cross_repo_drift and severity == "GREEN":
        severity = "YELLOW"

    print(f"\n  Final severity: {severity}")

    if severity == "RED":
        print("\n💡 修法建議：")
        print("  1. 公網 production container 嚴禁用 :latest（silent upgrade 風險）")
        print("  2. docker compose: image: cloudflare/cloudflared:2026.5.0 (pinned)")
        print("  3. docker run 改用明確版本：docker run cloudflare/cloudflared:2026.5.0")
        print("  4. 升版要走 ADR + 升版 SOP（測試 → 部署）")

    if severity == "RED":
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
