#!/usr/bin/env python3
"""frontend_bundle_size_drift_audit.py — fitness step 50

偵測 frontend Vite build artifact 是否 silent 膨脹超過閾值
（v6.12 P3 forward-looking）。

風險背景：
- CI bundle-size-check job 因 GitHub Actions 停用（feedback_no_github_actions_cost）
  → owner 必須手動 build + 手動跑 frontend/scripts/bundle-size-check.js
- 開發者每次 PR 不會跑這個 → bundle 大小可能 silent 漂移過閾值
- 既有閾值（per frontend/scripts/bundle-size-check.js）：
    totalRaw     ≤ 10.5 MB
    totalGzip    ≤  3.5 MB
    singleFile   ≤  1.5 MB
- 影響：行動端 / 弱網路下首屏載入時間飆升

判定邏輯：
1. 掃 frontend/dist/assets/ 所有 .js/.css/.html
2. 計算 total raw + total gzip + 找最大單檔
3. 任何一閾值超過 → 對應分級
   - RED：總 raw > 10.5 MB 或單檔 > 1.5 MB
   - YELLOW：總 gzip > 3.5 MB 或總 raw 在 90~100% 區間
   - GREEN：全部低於閾值 90%
4. 若 dist/ 不存在 → YELLOW（前端未 build，無法判定）

Usage:
    python scripts/checks/frontend_bundle_size_drift_audit.py [--strict]

Exit codes:
    0 = green (within thresholds with headroom)
    1 = yellow (近閾值 90%+ 或 gzip 超標)
    2 = red (任一硬閾值 raw 10.5MB / single 1.5MB 超標)
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = PROJECT_ROOT / "frontend" / "dist" / "assets"

# 閾值對齊 frontend/scripts/bundle-size-check.js (baseline + 15% headroom)
LIMITS = {
    "total_raw_mb": 10.5,
    "total_gzip_mb": 3.5,
    "single_file_raw_mb": 1.5,
}


def _human_mb(bytes_: int) -> float:
    return bytes_ / 1024 / 1024


def _scan_dist() -> list[dict] | None:
    """Scan dist/assets/ recursively for build artifacts."""
    if not DIST_DIR.exists():
        return None
    files: list[dict] = []
    for p in DIST_DIR.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".js", ".css", ".html"):
            continue
        try:
            raw = p.stat().st_size
            # gzip compress for accurate size (Vite uses gzip)
            gz = len(gzip.compress(p.read_bytes(), compresslevel=6))
        except Exception:
            continue
        files.append({"name": p.name, "raw": raw, "gz": gz, "ext": p.suffix})
    return files


def _classify(files: list[dict] | None) -> tuple[str, list[str], dict]:
    """Return (severity, reasons, stats)."""
    if files is None:
        return "YELLOW", ["dist/ 不存在 — frontend 未 build"], {}
    if not files:
        return "YELLOW", ["dist/assets/ 為空 — frontend 未 build 或 build 失敗"], {}

    total_raw = sum(f["raw"] for f in files)
    total_gz = sum(f["gz"] for f in files)
    biggest = max(files, key=lambda f: f["raw"])

    stats = {
        "file_count": len(files),
        "total_raw_mb": _human_mb(total_raw),
        "total_gzip_mb": _human_mb(total_gz),
        "biggest_file": biggest["name"],
        "biggest_raw_mb": _human_mb(biggest["raw"]),
    }

    reasons: list[str] = []
    severity = "GREEN"

    # RED triggers
    if stats["total_raw_mb"] > LIMITS["total_raw_mb"]:
        severity = "RED"
        reasons.append(
            f"total raw {stats['total_raw_mb']:.2f} MB > {LIMITS['total_raw_mb']} MB"
        )
    if stats["biggest_raw_mb"] > LIMITS["single_file_raw_mb"]:
        severity = "RED"
        reasons.append(
            f"biggest file {stats['biggest_file']} {stats['biggest_raw_mb']:.2f} MB "
            f"> {LIMITS['single_file_raw_mb']} MB"
        )

    # YELLOW triggers (only if not already RED)
    if severity != "RED":
        if stats["total_gzip_mb"] > LIMITS["total_gzip_mb"]:
            severity = "YELLOW"
            reasons.append(
                f"total gzip {stats['total_gzip_mb']:.2f} MB > "
                f"{LIMITS['total_gzip_mb']} MB"
            )
        # 接近 raw 閾值 90%
        raw_pct = stats["total_raw_mb"] / LIMITS["total_raw_mb"] * 100
        if raw_pct >= 90:
            if severity != "RED":
                severity = "YELLOW"
            reasons.append(
                f"total raw {raw_pct:.0f}% of threshold (approaching)"
            )

    if not reasons:
        reasons.append(
            f"total raw {stats['total_raw_mb']:.2f} MB / "
            f"gzip {stats['total_gzip_mb']:.2f} MB / "
            f"biggest {stats['biggest_raw_mb']:.2f} MB — all within headroom"
        )

    return severity, reasons, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="exit 2 on any warning")
    args = parser.parse_args()

    print("=" * 60)
    print("Frontend bundle size drift audit (v6.12 P3)")
    print("v1.0 / detect silent bundle inflation past CI thresholds")
    print("=" * 60)

    files = _scan_dist()
    severity, reasons, stats = _classify(files)
    indicator = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[severity]

    print(f"\n  dist path: {DIST_DIR}")
    if stats:
        print(f"  file count: {stats['file_count']}")
        print(f"  total raw:  {stats['total_raw_mb']:.2f} MB / {LIMITS['total_raw_mb']} MB")
        print(f"  total gzip: {stats['total_gzip_mb']:.2f} MB / {LIMITS['total_gzip_mb']} MB")
        print(f"  biggest:    {stats['biggest_file']} ({stats['biggest_raw_mb']:.2f} MB / {LIMITS['single_file_raw_mb']} MB)")

    print(f"\n  {indicator} {severity}")
    for r in reasons:
        print(f"    - {r}")

    if severity == "RED":
        print("\n💡 修法建議：")
        print("  1. `cd frontend && npm run build` 確認最新 dist 狀態")
        print("  2. `node scripts/bundle-size-check.js` 看詳細 per-file breakdown")
        print("  3. 檢視最大檔案是否可 code-split（懶載入 / dynamic import）")
        print("  4. 比對近期 commit 看是否誤引入大 lib（antd icons / moment / lodash 整包）")
        print("  5. 若是 vendor chunk 必要：申請 baseline 上調 + 寫 ADR 記錄")
    elif severity == "YELLOW":
        print("\n💡 informational：")
        print("  - 已接近閾值或 gzip 超標 — 觀察下次 build 是否變嚴重")
        print("  - 主要膨脹源：檢視 biggest 檔案是否屬於可拆 chunk")

    if severity == "RED":
        return 2
    if severity == "YELLOW" and args.strict:
        return 2
    if severity == "YELLOW":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
