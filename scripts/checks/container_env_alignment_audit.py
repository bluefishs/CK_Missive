"""Container env vs host .env 對齊 audit (fitness step 57, L51 2026-05-29)

防 L48 / L51 同型事故反覆：
- L48 (SSO): host .env 有 CK_SSO_* 但 docker-compose 沒注入 → SSO silent fail
- L51 (LINE): host .env 有 LINE_* 但 docker-compose 沒注入 → LINE 通報全 silent fail

對 critical env var 群組驗證：
1. 在 host .env 中有值
2. 在 docker-compose.production.yml backend.environment 中有 `- VAR=${VAR:-...}` 注入
3. 兩個都有 → GREEN
4. 只有 .env 沒 compose → RED (silent fail 風險)
5. 都沒 → YELLOW (可能尚未啟用)

Usage:
  python scripts/checks/container_env_alignment_audit.py
  python scripts/checks/container_env_alignment_audit.py --strict
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Critical env groups — 缺一即可能 silent fail
CRITICAL_GROUPS = {
    "LINE": [
        "LINE_BOT_ENABLED", "LINE_CHANNEL_SECRET", "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_ADMIN_USER_ID", "LINE_SUBSCRIBE_TOKEN",
        "LINE_LOGIN_CHANNEL_ID", "LINE_LOGIN_CHANNEL_SECRET", "LINE_LOGIN_REDIRECT_URI",
    ],
    "SSO": [
        "CK_SSO_ENABLED", "CK_SSO_JWT_SECRET", "CK_SSO_JWKS_URL",
    ],
    "TELEGRAM": [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_CHAT_ID", "TELEGRAM_ADMIN_PUSH_ENABLED",
    ],
    "GOOGLE": [
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
        # 2026-06-11: GOOGLE_CALENDAR_ID 漏注入 → 容器退回 config 預設 'primary'
        #   = 服務帳號私人日曆（無人可見）→ 1043 事件靜默推進隱形日曆。補入此 audit 防回退。
        "GOOGLE_CALENDAR_ID",
    ],
    "AI_PROVIDERS": [
        "GROQ_API_KEY", "NVIDIA_API_KEY",
    ],
}


def parse_env_file(path: Path) -> dict[str, str]:
    """簡單 .env parser — KEY=VALUE 行，忽略 comment 與空行"""
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        result[key.strip()] = val.strip()
    return result


def parse_compose_backend_env(path: Path) -> set[str]:
    """從 docker-compose 抓 backend service environment 區塊中所有注入的 VAR 名"""
    result = set()
    if not path.exists():
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")

    # 找 backend: service 區塊（粗略 — 找 "  backend:" 到下一個 "  [a-z]+:" service）
    backend_match = re.search(r"^  backend:\n(.*?)(?=^  [a-z_][a-z_-]*:\n|\Z)",
                              text, re.MULTILINE | re.DOTALL)
    if not backend_match:
        return result

    backend_block = backend_match.group(1)

    # 找 environment: 區塊
    env_match = re.search(
        r"^    environment:\n((?:      .*\n?)+)",
        backend_block, re.MULTILINE,
    )
    if not env_match:
        return result

    env_block = env_match.group(1)

    # 抓 "- VAR=..." 中的 VAR
    for m in re.finditer(r"^\s*-\s*([A-Z_][A-Z0-9_]*)\s*=", env_block, re.MULTILINE):
        result.add(m.group(1))

    return result


def main(strict: bool = False) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    compose_path = repo_root / "docker-compose.production.yml"

    if not env_path.exists():
        print(f"[SKIP] .env not found at {env_path}")
        return 0
    if not compose_path.exists():
        print(f"[SKIP] {compose_path.name} not found")
        return 0

    env_vars = parse_env_file(env_path)
    compose_env = parse_compose_backend_env(compose_path)

    print("=== Container env vs Host .env Alignment Audit (L51 / fitness step 57) ===")
    print(f"  .env: {len(env_vars)} vars")
    print(f"  compose backend.environment: {len(compose_env)} vars")
    print()

    red_count = 0
    yellow_count = 0
    green_count = 0

    for group_name, var_list in CRITICAL_GROUPS.items():
        print(f"[{group_name}]")
        for var in var_list:
            in_env = var in env_vars and bool(env_vars[var])
            in_compose = var in compose_env

            if in_env and in_compose:
                status = "GREEN OK"
                green_count += 1
            elif in_env and not in_compose:
                status = "RED FAIL (host .env 有值但 compose 未注入 → silent fail 風險)"
                red_count += 1
            elif not in_env and in_compose:
                status = "YELLOW (compose 注入但 .env 無值 - 可能 prod 暫關)"
                yellow_count += 1
            else:
                status = "YELLOW (兩者皆無 - 可能尚未啟用)"
                yellow_count += 1

            print(f"  {var:<40} {status}")
        print()

    print(f"Summary: {green_count} GREEN, {yellow_count} YELLOW, {red_count} RED")

    if red_count > 0:
        print(f"\n[WARN] {red_count} critical env var(s) in .env but NOT injected to container "
              f"(L51 同型 silent fail 風險)")
        if strict:
            return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on RED (for fitness gate)")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
