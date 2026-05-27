#!/usr/bin/env python3
"""compose_dockerfile_healthcheck_ssot.py — fitness step 40

偵測 docker-compose*.yml healthcheck 與對應 Dockerfile HEALTHCHECK SSOT drift（L45 family）。

L45 事故觸發（2026-05-22）：
- `frontend/Dockerfile`: HEALTHCHECK 用 `wget http://127.0.0.1:3000/nginx-health`
- `nginx.conf`: `listen 3000`
- `docker-compose.production.yml`: healthcheck override 為 `:80` → nginx 不在 :80
- FailingStreak=36（fail 18 分鐘）— compose override 了正確 Dockerfile HEALTHCHECK
- 屬於 L43 family「跨檔 SSOT 治理失效」第 4 案例

判定邏輯：
1. 掃所有 `docker-compose*.yml`（排除 archive / deprecated）
2. 對於有 `build:` 的 service：
   a. 解析 service 的 `healthcheck:` test 區塊（如有）
   b. 讀對應 Dockerfile 的 `HEALTHCHECK CMD ...`（如有）
   c. 抽 port + endpoint，比對是否一致
3. 對於只有 `image:` 的 service：跳過（無 Dockerfile 可比對）

Drift 判定：
- compose healthcheck endpoint != Dockerfile HEALTHCHECK endpoint → RED
- compose 有 healthcheck 但 Dockerfile 沒 → YELLOW（compose 自定義，可接受）
- Dockerfile 有 HEALTHCHECK 但 compose 沒 override → GREEN（Dockerfile 為 SSOT）

Usage:
    python scripts/checks/compose_dockerfile_healthcheck_ssot.py [--strict]

Exit codes:
    0 = green (no drift)
    1 = yellow (warnings only)
    2 = red (drift detected; --strict 時也會 exit 2)
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Match curl/wget URL inside HEALTHCHECK CMD
# Examples:
#   wget -q -O - http://127.0.0.1:3000/nginx-health
#   curl -fsS http://localhost:8001/health
_URL_PATTERN = re.compile(
    r"(?:curl|wget)\s+[^\n]*?(https?://[^/\s\"']+(?::(\d+))?(/[^\s\"']*)?)",
    re.IGNORECASE,
)


@dataclass
class HealthcheckTarget:
    """Parsed healthcheck endpoint."""
    host: str
    port: Optional[str]
    path: str
    raw: str

    @property
    def key(self) -> tuple[str, str]:
        """Canonical key for drift comparison (port + path)."""
        # 127.0.0.1 / localhost / 0.0.0.0 treated as equivalent for healthcheck
        return (self.port or "default", self.path or "/")


def _parse_url(text: str) -> Optional[HealthcheckTarget]:
    """Extract URL from a healthcheck CMD string."""
    m = _URL_PATTERN.search(text)
    if not m:
        return None
    raw_url = m.group(1)
    port = m.group(2)
    path = m.group(3) or "/"
    # extract host
    host_match = re.match(r"https?://([^:/]+)", raw_url)
    host = host_match.group(1) if host_match else "?"
    return HealthcheckTarget(host=host, port=port, path=path, raw=raw_url)


def _extract_compose_healthcheck(service: dict) -> Optional[HealthcheckTarget]:
    """Extract healthcheck from a compose service block."""
    hc = service.get("healthcheck")
    if not hc:
        return None
    test = hc.get("test")
    if not test:
        return None
    # test can be: ["CMD", "wget", "...", "url"] or ["CMD-SHELL", "..."] or string
    if isinstance(test, list):
        cmd_str = " ".join(str(x) for x in test)
    else:
        cmd_str = str(test)
    return _parse_url(cmd_str)


def _extract_dockerfile_healthcheck(dockerfile_path: Path) -> Optional[HealthcheckTarget]:
    """Extract HEALTHCHECK CMD from Dockerfile."""
    if not dockerfile_path.exists():
        return None
    content = dockerfile_path.read_text(encoding="utf-8", errors="ignore")
    # Match HEALTHCHECK [options] CMD <command>
    # Multi-line continuation with backslash supported by collapsing.
    collapsed = re.sub(r"\\\s*\n", " ", content)
    for line in collapsed.split("\n"):
        s = line.strip()
        if s.upper().startswith("HEALTHCHECK"):
            return _parse_url(s)
    return None


def _resolve_dockerfile(service_name: str, service: dict, compose_path: Path) -> Optional[Path]:
    """Resolve Dockerfile path from build: directive."""
    build = service.get("build")
    if not build:
        return None
    if isinstance(build, str):
        context = build
        dockerfile = "Dockerfile"
    else:
        context = build.get("context", ".")
        dockerfile = build.get("dockerfile", "Dockerfile")
    base = (compose_path.parent / context).resolve()
    return base / dockerfile


def _scan_compose(compose_path: Path) -> list[dict]:
    """Return list of {service, compose_hc, dockerfile_hc, drift, severity}."""
    try:
        data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [{"error": f"parse failed: {e}", "compose": str(compose_path)}]
    if not isinstance(data, dict):
        return []
    services = data.get("services") or {}
    rows = []
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        if "build" not in svc:
            continue  # image-only; skip
        compose_hc = _extract_compose_healthcheck(svc)
        dockerfile_path = _resolve_dockerfile(name, svc, compose_path)
        dockerfile_hc = _extract_dockerfile_healthcheck(dockerfile_path) if dockerfile_path else None
        # Drift logic
        severity = "GREEN"
        reason = ""
        if compose_hc and dockerfile_hc:
            if compose_hc.key != dockerfile_hc.key:
                severity = "RED"
                reason = (
                    f"compose ({compose_hc.port or '?'}{compose_hc.path}) "
                    f"!= Dockerfile ({dockerfile_hc.port or '?'}{dockerfile_hc.path})"
                )
        elif compose_hc and not dockerfile_hc:
            severity = "YELLOW"
            reason = "compose has healthcheck but Dockerfile lacks HEALTHCHECK (consider adding to Dockerfile as SSOT)"
        elif dockerfile_hc and not compose_hc:
            severity = "GREEN"
            reason = "Dockerfile HEALTHCHECK in effect (no override)"
        else:
            severity = "GREEN"
            reason = "no healthcheck declared anywhere (image may have inherited one)"
        rows.append({
            "compose": str(compose_path.relative_to(REPO_ROOT)),
            "service": name,
            "compose_hc": compose_hc.raw if compose_hc else None,
            "dockerfile": str(dockerfile_path.relative_to(REPO_ROOT)) if dockerfile_path else None,
            "dockerfile_hc": dockerfile_hc.raw if dockerfile_hc else None,
            "severity": severity,
            "reason": reason,
        })
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
    print("compose vs Dockerfile HEALTHCHECK SSOT audit (L45)")
    print("v1.0 / detect healthcheck endpoint drift")
    print("=" * 60)

    composes = sorted(REPO_ROOT.glob("docker-compose*.yml"))
    composes = [p for p in composes if "archive" not in p.parts and "deprecated" not in p.parts]
    if not composes:
        print("  no docker-compose*.yml found")
        return 0

    all_rows = []
    for cp in composes:
        all_rows.extend(_scan_compose(cp))

    red = [r for r in all_rows if r.get("severity") == "RED"]
    yellow = [r for r in all_rows if r.get("severity") == "YELLOW"]
    green = [r for r in all_rows if r.get("severity") == "GREEN"]

    print(f"\n  composes scanned:    {len(composes)}")
    print(f"  services with build: {len(all_rows)}")
    print(f"  🔴 RED drift:        {len(red)}")
    print(f"  🟡 YELLOW warnings:  {len(yellow)}")
    print(f"  🟢 GREEN aligned:    {len(green)}")

    if red:
        print("\n  🔴 Drift detected:")
        for r in red:
            print(f"    {r['compose']} → {r['service']}: {r['reason']}")
            print(f"      compose:    {r['compose_hc']}")
            print(f"      Dockerfile: {r['dockerfile_hc']}")
    if yellow:
        print("\n  🟡 Warnings:")
        for r in yellow:
            print(f"    {r['compose']} → {r['service']}: {r['reason']}")

    if red:
        print("\n💡 修法建議：")
        print("  1. 把 SSOT 放在 Dockerfile HEALTHCHECK（讓 image 自帶健康定義）")
        print("  2. compose 不要 override（除非有環境特異性，且註解理由）")
        print("  3. 同步 nginx.conf / uvicorn 等 listen port，確保 endpoint 真活")

    if red:
        return 2
    if yellow and args.strict:
        return 2
    if yellow:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
