#!/usr/bin/env python3
"""
後端服務行數監控 — CI 自動警告

掃描 backend/app/services/ 下的 Python 檔案，
若超過指定閾值 (預設 600L) 則輸出警告。

用法:
    python scripts/checks/service-line-count-check.py [--threshold 600] [--fail-on-warn]

退出碼:
    0 = 無警告
    1 = 有超過閾值的檔案 (僅在 --fail-on-warn 時)
"""
import argparse
import os
import sys


def count_lines(file_path: str) -> int:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def scan_services(base_dir: str, threshold: int) -> list[dict]:
    warnings = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in sorted(files):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(root, fname)
            lines = count_lines(fpath)
            if lines > threshold:
                rel_path = os.path.relpath(fpath, os.path.dirname(base_dir))
                warnings.append({
                    "file": rel_path,
                    "lines": lines,
                    "over": lines - threshold,
                })
    return sorted(warnings, key=lambda w: -w["lines"])


def main():
    parser = argparse.ArgumentParser(description="Service line count monitor")
    parser.add_argument("--threshold", type=int, default=600,
                        help="Line count threshold (default: 600)")
    parser.add_argument("--fail-on-warn", action="store_true",
                        help="Exit with code 1 if any warning")
    args = parser.parse_args()

    # 自動偵測專案根目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    services_dir = os.path.join(project_root, "backend", "app", "services")

    if not os.path.isdir(services_dir):
        print(f"ERROR: Services directory not found: {services_dir}")
        sys.exit(2)

    warnings = scan_services(services_dir, args.threshold)

    if not warnings:
        print(f"OK: All services under {args.threshold}L threshold")
        sys.exit(0)

    print(f"WARNING: {len(warnings)} service(s) exceed {args.threshold}L threshold:\n")
    print(f"{'File':<65} {'Lines':>6} {'Over':>6}")
    print("-" * 80)
    for w in warnings:
        print(f"  {w['file']:<63} {w['lines']:>6} {'+' + str(w['over']):>6}")

    print(f"\nTotal: {len(warnings)} file(s) over {args.threshold}L")

    if args.fail_on_warn:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
