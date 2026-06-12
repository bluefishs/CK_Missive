"""Config Settings Drift Audit — AST 衍生全域版（2026-06-11，強化圖譜治理）

取代 container_env_alignment_audit 的「寫死群組清單」：用 AST 掃描 backend/app
**所有** settings 讀取（`getattr(settings,'X')` / `settings.X`），逐一比對
config.py 定義 × host .env × docker-compose 注入，系統級揭發同型 config-drift。

揭發背景（L70 + 盤點）：
- GOOGLE_CALENDAR_ID：compose 漏注入 → 容器退回 'primary'（服務帳號隱形日曆），1044 事件無人可見。
- GOOGLE_REDIRECT_URI：compose 漏注入 → 容器退回 localhost 預設（prod .env=missive.cksurvey.tw）。
兩者皆「.env 有值 + code 讀取 + compose 未注入 → 容器靜默用 config 預設」同型。

判級（僅針對「code 真讀取」的 settings）：
- RED    : .env 有值 + compose 未注入 → 容器用預設，靜默 drift（高風險）
- YELLOW : code 讀取但 .env 無值 → 用預設（可能 prod 暫缺；或預設即正確）
- GREEN  : compose 已注入（值由 .env/compose 控制）

Usage:
  python scripts/checks/config_settings_drift_audit.py
  python scripts/checks/config_settings_drift_audit.py --strict   # RED → exit 1（fitness gate）
"""
from __future__ import annotations

# cp950 host 韌性（L49.8 同族）：印 CJK 到 Windows 終端會 UnicodeEncodeError
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import ast
import sys
from pathlib import Path


def get_config_fields(config_path: Path) -> dict[str, object]:
    """從 config.py 抓所有大寫 settings 欄位 + 預設值"""
    fields: dict[str, object] = {}
    if not config_path.exists():
        return fields
    tree = ast.parse(config_path.read_text(encoding="utf-8", errors="ignore"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if not name.isupper():
                continue
            default: object = "<none>"
            if node.value is not None:
                try:
                    default = ast.literal_eval(node.value)
                except Exception:
                    # Field(default=X) / Field(X, ...) → 取 default
                    if isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "default":
                                try:
                                    default = ast.literal_eval(kw.value)
                                except Exception:
                                    default = "<expr>"
                                break
                        else:
                            if node.value.args:
                                try:
                                    default = ast.literal_eval(node.value.args[0])
                                except Exception:
                                    default = "<expr>"
                    else:
                        default = "<expr>"
            fields[name] = default
    return fields


def scan_settings_reads(app_dir: Path) -> dict[str, set[str]]:
    """AST 掃描所有 settings 讀取 → {setting_name: {files}}"""
    reads: dict[str, set[str]] = {}
    for py in app_dir.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for node in ast.walk(tree):
            # getattr(settings, 'X', ...)
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "getattr" and len(node.args) >= 2
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == "settings"
                    and isinstance(node.args[1], ast.Constant)
                    and isinstance(node.args[1].value, str)):
                reads.setdefault(node.args[1].value, set()).add(py.name)
            # settings.X（X 全大寫）
            if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and node.value.id == "settings" and node.attr.isupper()):
                reads.setdefault(node.attr, set()).add(py.name)
    return reads


def parse_env_file(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def parse_compose_injected(path: Path) -> set[str]:
    """backend service environment 注入的 VAR 名（含 ${VAR} 與 - VAR= 兩式）"""
    import re
    result: set[str] = set()
    if not path.exists():
        return result
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^  backend:\n(.*?)(?=^  [a-z_][a-z_-]*:\n|\Z)", text, re.MULTILINE | re.DOTALL)
    block = m.group(1) if m else text
    for mm in re.finditer(r"^\s*-\s*([A-Z_][A-Z0-9_]*)\s*=", block, re.MULTILINE):
        result.add(mm.group(1))
    return result


def main(strict: bool = False) -> int:
    root = Path(__file__).resolve().parents[2]
    config_fields = get_config_fields(root / "backend" / "app" / "core" / "config.py")
    reads = scan_settings_reads(root / "backend" / "app")
    env_vars = parse_env_file(root / ".env")
    compose = parse_compose_injected(root / "docker-compose.production.yml")

    print("=== Config Settings Drift Audit (AST 衍生全域版) ===")
    print(f"  config.py 欄位: {len(config_fields)} | code 讀取 settings: {len(reads)} | "
          f".env: {len(env_vars)} | compose 注入: {len(compose)}\n")

    red, latent, yellow, green = [], [], [], []
    # 只稽核「code 真讀取」且「config.py 有定義」的 settings（排除 framework 內建）
    for name in sorted(reads):
        if name not in config_fields:
            continue
        in_env = name in env_vars and bool(env_vars[name])
        in_compose = name in compose
        if in_compose:
            green.append(name)
        elif in_env:
            # 值比對：.env 值 != config 預設 → 真 drift（RED）；== 預設 → 潛在無害（LATENT）
            default_str = str(config_fields.get(name)).lower()
            env_str = env_vars[name].lower()
            if env_str != default_str:
                red.append(name)
            else:
                latent.append(name)
        else:
            yellow.append(name)

    if red:
        print("[RED] .env 值≠預設 + compose 未注入 → 容器靜默用「錯的」預設（真 drift，同 GOOGLE_CALENDAR_ID）：")
        for n in red:
            print(f"  ✗ {n:28} .env={env_vars[n]!r} 但容器用預設={config_fields.get(n)!r}  ({len(reads[n])} 檔讀取)")
        print()
    if latent:
        print("[LATENT] .env 值==預設 + compose 未注入 → 目前無害但 .env 一改即 drift（建議仍注入）：")
        for n in latent:
            print(f"  ~ {n:28} .env={env_vars[n]!r}（==預設）")
        print()
    if yellow:
        print(f"[YELLOW] code 讀取但 .env 無值（純用預設）: {', '.join(yellow)}\n")
    print(f"Summary: {len(green)} GREEN, {len(latent)} LATENT, {len(yellow)} YELLOW, {len(red)} RED")

    if red:
        print(f"\n[WARN] {len(red)} 個真 config-drift（值不符）→ 補 compose 注入")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="RED → exit 1（fitness gate）")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
