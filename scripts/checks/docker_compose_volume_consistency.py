#!/usr/bin/env python3
"""docker_compose_volume_consistency.py — fitness step 38

偵測同一專案多個 docker-compose*.yml + backup script 內 volume 命名 drift。

L43 事故觸發（2026-05-21）：
- `docker-compose.production.yml` 寫 `name: ck_missive_postgres_data`（空殼）
- `docker-compose.dev.yml` / `infra.yml` 寫 `name: ck_missive_postgres_dev_data`（真實主庫）
- `scripts/backup/pre_upgrade_backup.sh:33` 寫死 `ck_missive_postgres_dev_data`
→ 切換 production compose 啟動時 postgres 掛到空殼，業務 API 全 500，
  dormant ~10 小時直到 owner 登入觸發。

判定邏輯：
1. 掃所有 `docker-compose*.yml`（排除 archive / deprecated）解析 `volumes:` 區塊
2. 掃 `scripts/backup/*.sh` 取出寫死的 `*postgres*data` / `*redis*data` volume name
3. 將每個 volume 用「邏輯 key」分群（例：`postgres_data` / `postgres_dev_data` → 同 `postgres`）
4. 若同邏輯 key 出現 2+ 個實體 volume name → drift（red）
5. 若 compose 宣告但 backup script 不知道 → warning（yellow）

Usage:
    python scripts/checks/docker_compose_volume_consistency.py [--strict]

Exit codes:
    0 = green (no drift)
    1 = yellow (warnings only)
    2 = red (drift detected; --strict 時也會 exit 2)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Env var 解析 pattern: ${VAR} 或 ${VAR:-default}
_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}")


def _load_env(repo: Path) -> dict[str, str]:
    """讀 .env 檔回傳變數字典（為 ${VAR} 展開用）。"""
    env: dict[str, str] = {}
    env_file = repo / ".env"
    if not env_file.exists():
        return env
    try:
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip("'\"")
    except Exception:
        pass
    # repo 目錄名 fallback（compose 預設 project name）
    env.setdefault("COMPOSE_PROJECT_NAME", repo.name.lower())
    return env


def _expand_vars(value: str, env: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        var_name = m.group(1)
        default = m.group(2) or ""
        return env.get(var_name, default)
    return _ENV_VAR_PATTERN.sub(repl, value)


# 邏輯 key 萃取：postgres_data / postgres_dev_data / pg_volume → "postgres"
LOGICAL_KEY_RULES = [
    (re.compile(r"postgres|pg_", re.IGNORECASE), "postgres"),
    (re.compile(r"redis", re.IGNORECASE), "redis"),
    (re.compile(r"ollama", re.IGNORECASE), "ollama"),
    (re.compile(r"vllm|nim_", re.IGNORECASE), "inference"),
    (re.compile(r"backend_logs|backend_uploads", re.IGNORECASE), "backend_runtime"),
    (re.compile(r"frontend_logs", re.IGNORECASE), "frontend_runtime"),
]


@dataclass
class VolumeRef:
    source_file: Path
    alias: str          # compose volumes 區塊中的 alias（dict key）
    physical_name: str  # 實體 docker volume name
    logical_key: str    # 分群用 key


@dataclass
class AuditResult:
    refs: list[VolumeRef] = field(default_factory=list)
    backup_refs: list[VolumeRef] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)  # host volumes not in any compose
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    status: str = "unknown"


def _logical_key(name: str) -> str:
    for pattern, key in LOGICAL_KEY_RULES:
        if pattern.search(name):
            return key
    return name  # 無分類，自成一群


def _find_compose_files(repo: Path) -> list[Path]:
    files = list(repo.glob("docker-compose*.yml")) + list(repo.glob("docker-compose*.yaml"))
    return [
        f for f in files
        if "archive" not in str(f).lower() and "deprecated" not in str(f).lower()
    ]


def _parse_compose_volumes(compose_file: Path, env: dict[str, str]) -> list[VolumeRef]:
    refs: list[VolumeRef] = []
    try:
        with compose_file.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  Parse failed: {compose_file.name}: {e}", file=sys.stderr)
        return refs
    if not isinstance(data, dict):
        return refs
    volumes = data.get("volumes") or {}
    if not isinstance(volumes, dict):
        return refs
    for alias, config in volumes.items():
        # 取得實體 name（解析 ${COMPOSE_PROJECT_NAME} 等變數）
        physical = alias
        if isinstance(config, dict) and "name" in config:
            physical = str(config["name"])
        physical = _expand_vars(physical, env)
        refs.append(VolumeRef(
            source_file=compose_file,
            alias=alias,
            physical_name=physical,
            logical_key=_logical_key(physical),
        ))
    return refs


def _scan_backup_scripts(repo: Path) -> list[VolumeRef]:
    """掃 backup 腳本內寫死的 volume name（pre_upgrade_backup.sh 等）。"""
    refs: list[VolumeRef] = []
    backup_dir = repo / "scripts" / "backup"
    if not backup_dir.exists():
        return refs
    name_pattern = re.compile(
        r"\b(ck_[a-z0-9_]+_(?:data|logs|uploads|cache))\b",
        re.IGNORECASE,
    )
    seen: set[tuple[str, str]] = set()  # (file, name) 去重
    for script in backup_dir.rglob("*.sh"):
        try:
            content = script.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in name_pattern.finditer(content):
            physical = match.group(1)
            key = (str(script), physical)
            if key in seen:
                continue
            seen.add(key)
            refs.append(VolumeRef(
                source_file=script,
                alias="(backup_script)",
                physical_name=physical,
                logical_key=_logical_key(physical),
            ))
    return refs


def _scan_host_orphans(repo: Path, declared_names: set[str]) -> tuple[list[str], str | None]:
    """掃 docker 主機上實際存在的 volumes，找出無 compose 宣告的 orphan。

    判定範圍：volume name 以 `<repo>_` 或 `ck_<repo>_` 開頭（case-insensitive），
    或 label `com.docker.compose.project` 等於 repo 目錄名（小寫）。

    Returns:
        (orphan_names, skip_reason) — skip_reason 非 None 時表示無法跑 docker。

    本函數刻意「軟失敗」：docker 不在 / 拒絕連線時回空清單 + reason，
    不 raise — 因為 CI 環境通常無 docker daemon。
    """
    repo_name_lower = repo.name.lower()
    try:
        proc = subprocess.run(
            ["docker", "volume", "ls", "--format", "{{.Name}}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if proc.returncode != 0:
            return [], f"docker exit {proc.returncode}: {proc.stderr.strip()[:200]}"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        return [], f"docker unavailable: {type(e).__name__}: {e}"

    declared_lower = {n.lower() for n in declared_names}
    orphans: list[str] = []
    # 同 repo 範圍判定：name prefix match（含大小寫變體 — L43 揭發 ghost 用了大寫前綴）
    prefix_variants = [
        f"{repo_name_lower}_",
        f"ck_{repo_name_lower.removeprefix('ck_')}_",  # 兼容 'CK_Missive' → 'ck_missive_'
    ]
    for vol_name in proc.stdout.splitlines():
        vol_name = vol_name.strip()
        if not vol_name:
            continue
        vol_lower = vol_name.lower()
        if not any(vol_lower.startswith(p) for p in prefix_variants):
            continue
        if vol_lower in declared_lower:
            continue
        orphans.append(vol_name)
    return sorted(orphans), None


def _detect_drift(result: AuditResult) -> None:
    # 同邏輯 key 收集所有實體 name + 來源
    by_key: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for ref in result.refs:
        by_key[ref.logical_key][ref.physical_name].append(ref.source_file)

    for key, names_map in by_key.items():
        if len(names_map) <= 1:
            continue
        # 同邏輯 key 有 2+ 種實體名 → drift
        msg_parts = []
        for name, files in names_map.items():
            file_names = sorted({f.name for f in files})
            msg_parts.append(f"{name} in [{', '.join(file_names)}]")
        result.violations.append(
            f"❌ Volume drift for '{key}': " + " VS ".join(msg_parts)
        )

    # 檢查 backup script vs compose 是否對齊
    compose_names_by_key: dict[str, set[str]] = defaultdict(set)
    for ref in result.refs:
        compose_names_by_key[ref.logical_key].add(ref.physical_name)
    for backup_ref in result.backup_refs:
        compose_set = compose_names_by_key.get(backup_ref.logical_key)
        if not compose_set:
            continue
        if backup_ref.physical_name not in compose_set:
            result.warnings.append(
                f"⚠️  Backup script `{backup_ref.source_file.name}` references "
                f"'{backup_ref.physical_name}' which doesn't match any compose declaration "
                f"in logical_key '{backup_ref.logical_key}' (compose has: {sorted(compose_set)})"
            )


def audit(repo: Path, check_orphans: bool = True) -> AuditResult:
    result = AuditResult()
    env = _load_env(repo)
    compose_files = _find_compose_files(repo)
    if not compose_files:
        result.warnings.append("⚠️  No docker-compose*.yml found")
        result.status = "yellow"
        return result
    for cf in compose_files:
        result.refs.extend(_parse_compose_volumes(cf, env))
    result.backup_refs = _scan_backup_scripts(repo)
    _detect_drift(result)
    if check_orphans:
        declared = {r.physical_name for r in result.refs}
        orphans, skip_reason = _scan_host_orphans(repo, declared)
        result.orphans = orphans
        if skip_reason:
            result.warnings.append(f"⚠️  Orphan scan skipped: {skip_reason}")
        else:
            for orphan in orphans:
                result.warnings.append(
                    f"⚠️  Orphan volume on host: '{orphan}' (not declared in any compose)"
                )
    if result.violations:
        result.status = "red"
    elif result.warnings:
        result.status = "yellow"
    else:
        result.status = "green"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="Exit 2 on any orphan (default: orphans are yellow warnings only)")
    parser.add_argument("--no-orphan-scan", action="store_true",
                        help="Skip host volume orphan detection (skip docker volume ls)")
    parser.add_argument("--repo", help="Repo path (default: parent of scripts/)")
    args = parser.parse_args()

    repo = Path(args.repo).resolve() if args.repo else REPO_ROOT

    print(f"🔍 docker_compose_volume_consistency (L43 防禦) — repo: {repo.name}\n")
    result = audit(repo, check_orphans=not args.no_orphan_scan)
    emoji = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(result.status, "❓")
    print(f"{emoji} Status: {result.status.upper()}")
    print(f"  compose volume refs:    {len(result.refs)}")
    print(f"  backup script refs:     {len(result.backup_refs)}")
    print(f"  host orphan volumes:    {len(result.orphans)}")
    print(f"  violations (drift):     {len(result.violations)}")
    print(f"  warnings:               {len(result.warnings)}\n")

    for v in result.violations:
        print(f"  {v}")
    for w in result.warnings:
        print(f"  {w}")

    if result.violations:
        print("\n💡 Lesson: L43 — Volume mount drift silent fail")
        print("   修法：所有 compose 內同邏輯 volume 必須指向同一 docker volume name")
    if result.orphans:
        print("\n💡 Orphan cleanup suggestion:")
        print("   1. 確認 orphan 內無重要資料：docker run --rm -v <name>:/d:ro alpine ls /d")
        print("   2. tar 留底（仿 backup/ghost_volume_cleanup_*）+ docker volume rm <name>")
        print("   3. 若是過渡期保留請註明在 docs/architecture/ARCHITECTURE_DEBT.md")

    # --strict: any orphan or drift fails. Default: only drift fails.
    if args.strict and (result.violations or result.orphans):
        return 2
    if result.status == "red":
        return 2
    if result.status == "yellow":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
