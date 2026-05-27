#!/usr/bin/env python3
r"""
Container Host Dependency Audit (fitness step 52, v6.12 P3)

掃 backend services / endpoints 內對 host 環境的隱式依賴，
這類依賴在 PM2 native Windows mode 可用、進 docker container 必爆。

觸發歷史：
- 2026-05-27 OA-3 PM2 廢除後揭發
  - L49.A: backup service 用 `docker info` / `docker exec` subprocess → container 內無 docker CLI
  - L49.B: file storage `rglob('*')` 遇 Windows host 長中文檔名 OSError → 500
  - L49.C: file_path DB 內存 Windows `\` 分隔符 → Linux container `os.path.exists` 404

L41-L49 family meta-pattern：
  「跨平台/跨環境的隱式依賴沒有 audit enforce 一致性 → 環境切換時 silent dormant」

掃描規則：
  RED：subprocess.run([docker..., shutil.which('docker'), /var/run/docker.sock
  YELLOW：rglob('*') 無 OSError 容錯、attachment.file_path 直接 os.path.exists 無 normalize
  INFO：subprocess.run 任意 host binary（pg_dump/psql 已是 image 內建，OK）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Windows console emoji 支援
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend" / "app"

# RED patterns — container 內必爆
RED_PATTERNS = [
    (re.compile(r"""shutil\.which\(['"]docker['"]\)"""), "shutil.which('docker') — container 內無 docker CLI"),
    (re.compile(r"""subprocess\.run\(\s*\[\s*['"]?docker['"]?"""), "subprocess.run(['docker', ...]) — container 內無 docker CLI"),
    (re.compile(r"""['\"]docker\s+(?:exec|info|ps|inspect|run)"""), "docker subprocess command literal"),
    (re.compile(r"/var/run/docker\.sock"), "/var/run/docker.sock — 需 mount + 安全降級"),
]

# YELLOW patterns — 跨平台陷阱
# L49 (2026-05-28): regex 升級 — 排除已修法 callsite（避免大量 false positive）
YELLOW_PATTERNS = [
    # rglob 排除：同一行有 _safe_rglob 呼叫 / 註解內提及
    (re.compile(r"""(?<!_safe)\.rglob\(['"]\*['"]\)"""),
     "rglob('*') 無 OSError 容錯（Windows host 長中文檔名 mount 會炸）"),
    # file_path 排除：
    # 1. 同行 `.replace('\\', ...` 或 `.replace('\\\\', ...` 已做 backslash normalize
    # 2. 同行 `resolve_attachment_path(` 已過 SSOT helper
    # 3. 行末是 `or ''` 然後下一行才用 — regex 限制只在「實際 path operation 行」flag
    (re.compile(r"""attachment\.file_path(?!\s*(?:or|\.replace|\)?\s*\.\w+\()).*?(?<!resolve_attachment_path\()(?<!\.replace\()""", re.DOTALL),
     "attachment.file_path 直接使用，未做跨平台分隔符 normalize（Windows \\ vs Linux /）"),
]

# 白名單檔（已修 / 不適用）
WHITELIST = {
    # backup utils 故意留 backwards-compat alias，內部已轉用 pg_dump
    "backend/app/services/backup/utils.py",
    # 本 audit 自己
    "scripts/checks/container_host_dependency_audit.py",
    # tests 不算實際生產
}


def scan(path: Path, patterns: List[Tuple[re.Pattern, str]]) -> List[Tuple[Path, int, str, str]]:
    """掃單檔回傳 (file, lineno, matched_line, reason) list"""
    hits = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits

    # L49 (2026-05-28): docstring tracking — 跳過 """ ~ """ 內所有行（含 module / function docstring）
    in_docstring = False
    docstring_delim = None

    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        # 跳過註解行
        if stripped.startswith("#"):
            continue

        # docstring 偵測（跳過 """ 或 ''' 區段）
        if in_docstring:
            if docstring_delim and docstring_delim in stripped:
                in_docstring = False
                docstring_delim = None
            continue
        else:
            # 行內偵測 """ 或 '''
            for delim in ('"""', "'''"):
                if delim in stripped:
                    # 單行 docstring 還是多行起始？
                    cnt = stripped.count(delim)
                    if cnt >= 2:
                        # 單行 docstring（同行有對 delim）— 跳過此行
                        line = ""
                        break
                    else:
                        # 多行起始
                        in_docstring = True
                        docstring_delim = delim
                        line = ""
                        break
            if not line.strip():
                continue

        # L49: line-level whitelist — 已修法 callsite / helper 本身的合法實作
        # 1. resolve_attachment_path(attachment.file_path) 完整呼叫 — 是修法本體不是違規
        if "resolve_attachment_path(attachment.file_path" in stripped:
            continue
        # 2. truthy 檢查 — 不是 path operation
        if re.match(r"^if\s+attachment\.file_path:?$", stripped):
            continue
        # 3. _safe_rglob helper 內部的 root.rglob — helper 本身是合法 OSError-tolerant
        if "root.rglob" in stripped and "_safe_rglob" in text[:text.find(stripped)]:
            # 在 _safe_rglob 函式定義內
            continue
        # 4. files/storage.py _scan_files 已修為 OSError-tolerant iterator
        if "storage_path.rglob" in stripped and "while True:" in text:
            # _scan_files 已用 while + try/except OSError 模式
            continue

        for pat, reason in patterns:
            if pat.search(line):
                hits.append((path, i, line.strip(), reason))
                break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Container host dependency audit")
    parser.add_argument("--strict", action="store_true", help="RED 觸發 exit 1")
    args = parser.parse_args()

    red_hits: List[Tuple[Path, int, str, str]] = []
    yellow_hits: List[Tuple[Path, int, str, str]] = []

    if not BACKEND_DIR.exists():
        print(f"⚠️  backend dir not found: {BACKEND_DIR}")
        return 0

    for py_file in BACKEND_DIR.rglob("*.py"):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        if rel in WHITELIST:
            continue
        red_hits.extend(scan(py_file, RED_PATTERNS))
        yellow_hits.extend(scan(py_file, YELLOW_PATTERNS))

    print("=" * 72)
    print("[52/52] Container Host Dependency Audit (v6.12 P3)")
    print("=" * 72)

    if red_hits:
        print(f"\n🔴 RED — {len(red_hits)} site(s) — container 內必爆：\n")
        for path, lineno, content, reason in red_hits:
            rel = path.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}:{lineno}")
            print(f"    └─ {reason}")
            print(f"       {content[:120]}")

    if yellow_hits:
        print(f"\n🟡 YELLOW — {len(yellow_hits)} site(s) — 跨平台陷阱：\n")
        for path, lineno, content, reason in yellow_hits[:20]:
            rel = path.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}:{lineno}")
            print(f"    └─ {reason}")
            print(f"       {content[:120]}")
        if len(yellow_hits) > 20:
            print(f"  ... and {len(yellow_hits) - 20} more")

    if not red_hits and not yellow_hits:
        print("\n🟢 GREEN — no container host dependency violations detected")
        return 0

    print(f"\nSummary: {len(red_hits)} RED, {len(yellow_hits)} YELLOW")
    print("\n修法指引：")
    print("  - RED docker CLI：改用 image 內建二進制（pg_dump/psql 已示範）+ docker network 名連線")
    print("  - YELLOW rglob：用 try/except OSError 包個別 next(iterator)，跳過壞 entry")
    print("  - YELLOW file_path：用 resolve_attachment_path() helper（files/common.py）")
    print("\nL41-L49 family meta-pattern：跨環境隱式依賴 → 立法 + audit + ADR 三件套")

    if args.strict and red_hits:
        print("\n🔴 STRICT mode → exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
