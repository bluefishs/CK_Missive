#!/usr/bin/env python3
"""Session 收尾完整性審計 — 未提交工作 × host↔容器部署對賬（fitness step 65）

觸發事故（2026-07-08 覆盤揭發）：07-07 session 寫好 LINE 主題合併
（line_digest_buffer + scheduler 改造 + 測試 8/8 綠）但既未 commit 也未
rebuild 部署 → 功能「存在於硬碟但不存在於系統」，L30（環節不連通）
× L51.7.1（host 碼≠容器碼）同族半接通。

偵測兩層：
1. 未提交逾時：git 工作樹中「非 runtime 產物」的 modified/untracked 檔，
   mtime 逾 STALE_HOURS（預設 12h）→ RED（寫好被遺忘）；未逾時 → YELLOW
   （進行中工作，僅提示）。runtime 產物白名單（wiki compile 寫穿、治理
   儀表板 regenerate、備份時戳）不計。
2. host↔容器對賬：modified 的 backend/app/**.py 逐一比對容器 /app 同路徑
   內容 md5 —— host 已改但容器仍舊碼 = 未部署（半接通確證，RED 加註）。

用法：
    python scripts/checks/uncommitted_work_audit.py            # 警示模式
    python scripts/checks/uncommitted_work_audit.py --strict   # RED 即 exit 1
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

# cp950 host 韌性（L49.8 同族）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
STALE_HOURS = float(os.getenv("UNCOMMITTED_STALE_HOURS", "12"))
CONTAINER = os.getenv("MISSIVE_BACKEND_CONTAINER", "ck_missive_backend")

# runtime 產物白名單（prefix 匹配，這些由 cron/排程自動寫，非人工工作）
RUNTIME_PREFIXES = (
    "wiki/",
    "docs/architecture/GOVERNANCE_INTEGRATED_DASHBOARD.md",
    "backend/config/remote_backup.json",
    "logs/",
    "backups/",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    ).stdout


def collect_pending() -> list[dict]:
    """回傳非 runtime 產物的 modified/untracked 檔清單（含 mtime 齡）。"""
    pending: list[dict] = []
    now = time.time()
    for line in _git("status", "--porcelain").splitlines():
        if len(line) < 4:
            continue
        status, rel = line[:2], line[3:].strip().strip('"')
        # git 對中文路徑輸出 octal escape，strip 引號後仍可能含跳脫 → 統一還原
        if "\\" in rel and not (REPO_ROOT / rel).exists():
            try:
                rel = rel.encode("latin-1", "backslashreplace").decode(
                    "unicode_escape").encode("latin-1").decode("utf-8")
            except Exception:
                pass
        if any(rel.startswith(p) for p in RUNTIME_PREFIXES):
            continue
        fp = REPO_ROOT / rel
        age_h = (now - fp.stat().st_mtime) / 3600 if fp.exists() else None
        pending.append({"path": rel, "status": status.strip(), "age_h": age_h})
    return pending


def container_drift(paths: list[str]) -> list[str]:
    """比對 modified backend/app py 檔 host vs 容器內容，回傳未部署清單。"""
    drifted: list[str] = []
    targets = [p for p in paths if p.startswith("backend/app/") and p.endswith(".py")]
    if not targets:
        return drifted
    for rel in targets:
        host_fp = REPO_ROOT / rel
        if not host_fp.exists():
            continue
        host_md5 = hashlib.md5(host_fp.read_bytes()).hexdigest()
        in_container = "/app/" + rel[len("backend/"):]
        try:
            r = subprocess.run(
                ["docker", "exec", CONTAINER, "md5sum", in_container],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                drifted.append(f"{rel}（容器內不存在＝新檔未部署）")
            elif r.stdout.split()[0] != host_md5:
                drifted.append(f"{rel}（host 已改、容器仍舊碼）")
        except Exception:
            return drifted  # docker 不可用時跳過本層（不誤報）
    return drifted


def main() -> int:
    strict = "--strict" in sys.argv
    pending = collect_pending()
    if not pending:
        print("✅ GREEN：工作樹 clean（非 runtime 產物 0 檔未提交）")
        return 0

    stale = [p for p in pending if p["age_h"] is not None and p["age_h"] >= STALE_HOURS]
    fresh = [p for p in pending if p not in stale]
    drifted = container_drift([p["path"] for p in pending])

    for p in fresh:
        print(f"🟡 進行中（<{STALE_HOURS:.0f}h）: {p['path']} [{p['status']}]")
    for p in stale:
        print(f"🔴 逾時未提交（{p['age_h']:.0f}h）: {p['path']} [{p['status']}] "
              "← 半接通信號：寫好被遺忘？commit＋部署＋驗證三步收尾")
    for d in drifted:
        print(f"🔴 未部署對賬: {d} ← 需 rebuild backend（L76 驗證）")

    red = bool(stale or drifted)
    print(f"\n結果：{'🔴 RED' if red else '🟡 YELLOW'}"
          f"（pending={len(pending)}, stale={len(stale)}, container_drift={len(drifted)}）")
    return 1 if (red and strict) else 0


if __name__ == "__main__":
    sys.exit(main())
