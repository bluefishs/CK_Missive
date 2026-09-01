#!/usr/bin/env python3
"""設定目錄 SSOT —— 專案根只允許兩個設定目錄（weekly 96）

## 為什麼

2026-09-01 owner：「另為設定為何散亂各處」。量出來的答案是
**三個設定目錄是三個時間點各自長出來的，沒有人合併過**：

    configs/        2025-12-30   15 檔   基礎設施（nginx／postgres／grafana）
    config/         2026-02-03    1 檔   ⚠️ 只裝一個過期複本
    backend/config/ 2026-02-26    5 檔   應用層（agent 策略／推論 profile）

`configs/` 與 `backend/config/` 的分工說得通。異常的是 `config/` ——
它憑空長出來，而且 `remote_backup.json` 因此有了**三份、內容都不同**，
沒有人知道哪一份是真的（`paths.py` 一度就指向了非權威的那一份）。

## 判準（兩條，都是機械式的）

1. **專案根不得出現第三個設定目錄**。允許清單寫死在下方，加新的要改這裡 ——
   那一刻就會有人問「為什麼不放進既有的兩個」。
2. **同名設定檔不得同時存在於多個受管目錄**，除非全部標了 `_deprecated`。
   這條擋的是「複製一份改一改」——今天那三份 `remote_backup.json` 的來歷。

## 這支不做什麼

* 不管 `shared-modules/` 底下 —— 每個共享套件本來就各有 `manifest.yml`／
  `package.json`，那是設計，不是散亂。誤報會讓人學會忽略這支。
* 不刪任何東西。標記與移除是 owner 的決定（A63 的 P2）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: 受管的設定目錄。**新增第三個之前先問「為什麼不放進這兩個」。**
SANCTIONED = ("configs", "backend/config")

#: 專案根不得出現的設定目錄名（除了受管的那些）
FORBIDDEN_AT_ROOT = ("config", "conf", "settings", "cfg")

CONFIG_EXT = (".json", ".yaml", ".yml", ".conf", ".ini", ".toml")


def _deprecated(p: Path) -> bool:
    """檔案有沒有標記待移除（標了的不算違規，但也不會讓它永遠留著）。"""
    try:
        if p.suffix == ".json":
            return "_deprecated" in json.loads(p.read_text(encoding="utf-8-sig"))
        return "_deprecated" in p.read_text(encoding="utf-8", errors="replace")[:600]
    except Exception:
        return False


def main() -> int:
    print("=== 設定目錄 SSOT（weekly 96）===\n")
    red: list[str] = []
    warn: list[str] = []

    # ① 專案根有沒有多餘的設定目錄
    print("  ── 專案根的設定目錄 ──")
    for name in FORBIDDEN_AT_ROOT:
        d = ROOT / name
        if not d.is_dir():
            continue
        files = [f for f in d.iterdir() if f.is_file() and f.suffix in CONFIG_EXT]
        marked = [f for f in files if _deprecated(f)]
        if files and len(marked) == len(files):
            warn.append(f"{name}/ 仍存在，但 {len(files)} 個檔已全部標記待移除")
            print(f"    ⚠ {name}/  {len(files)} 檔，全部已標記待移除（等 A63 的 P2）")
        else:
            red.append(f"專案根出現第三個設定目錄：{name}/（{len(files)} 個未標記的設定檔）")
            print(f"    ✗ {name}/  {len(files)} 檔，其中 {len(files) - len(marked)} 個未標記")
    for s in SANCTIONED:
        d = ROOT / s
        n = len([f for f in d.iterdir() if f.is_file() and f.suffix in CONFIG_EXT]) if d.is_dir() else 0
        print(f"    ✓ {s}/  {n} 檔（受管）")

    # ② 同名設定檔跨受管目錄
    print("\n  ── 同名設定檔（僅比對受管目錄與專案根）──")
    seen: dict[str, list[Path]] = {}
    for base in list(SANCTIONED) + list(FORBIDDEN_AT_ROOT):
        d = ROOT / base
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix in CONFIG_EXT:
                seen.setdefault(f.name, []).append(f)
    dup_found = False
    for name, paths in sorted(seen.items()):
        if len(paths) < 2:
            continue
        dup_found = True
        live = [p for p in paths if not _deprecated(p)]
        rel = [p.relative_to(ROOT).as_posix() for p in paths]
        if len(live) > 1:
            red.append(f"{name} 有 {len(live)} 份未標記的複本：{', '.join(rel)}")
            print(f"    ✗ {name}：{len(live)} 份未標記　{rel}")
        else:
            print(f"    ⚠ {name}：{len(paths)} 份，其中 {len(paths) - len(live)} 份已標記待移除　{rel}")
    if not dup_found:
        print("    ✓ 無同名設定檔")

    print()
    if red:
        print(f"[RED] {len(red)} 項：")
        for x in red:
            print(f"  · {x}")
        print("\n  設定只能放 configs/（基礎設施）或 backend/config/（應用層）。")
        print("  要新增第三個目錄，請先在 A63 說明為什麼不放進既有的兩個。")
        return 2
    if warn:
        print(f"[YELLOW] {len(warn)} 項待清（已標記，等移除日）：")
        for x in warn:
            print(f"  · {x}")
        return 1
    print("[GREEN] 設定目錄收斂完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
