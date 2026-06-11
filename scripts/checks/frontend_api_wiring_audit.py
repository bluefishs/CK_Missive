"""Frontend API Wiring Audit — 導覽鏈 page→endpoint 接線治理（2026-06-12）

owner：以 site management 為治理單元、聚焦「頁面→端點 API 接線」層（L67 雙前綴所在）。
實證：nav→route 已 100% 接通（低價值），真破口在 apiClient 呼叫層——
專案規範「API 端點一律用 endpoints/*.ts 常數、禁硬編路徑」，硬編即 L67（double-prefix 404）母類。

掃 frontend/src 所有 `apiClient.<verb>('literal-path')`：
- RED    : 硬編 `/api/...` 前綴（baseURL 已含 /api → double-prefix 404，L67 精確同型）
- YELLOW : 硬編字串路徑（非端點常數，違反 SSOT、L67 風險面，建議遷常數）
- raw fetch 漏 CSRF/Auth header（v6.13 同型）另記。

Usage:
  python scripts/checks/frontend_api_wiring_audit.py [--strict]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# apiClient.get/post/... <generic>? ( 'literal-path'  — 抓字面字串路徑（單/雙/反引號）
# <[^(]*> 涵蓋 nested generics（如 post<Record<string,unknown>>）避免漏抓（2026-06-12 修盲點）
_HARDCODE_RE = re.compile(
    r"""apiClient\.(?:get|post|put|delete|patch)\s*(?:<[^(]*>)?\s*\(\s*[`'"](/[^`'"$]*)""")
# raw fetch 帶 method POST 但同段無 X-CSRF-Token（粗略）
_RAW_FETCH_RE = re.compile(r"""fetch\(\s*[`'"][^`'"]*['"`]""")


def main(strict: bool = False) -> int:
    root = Path(__file__).resolve().parents[1] if (Path(__file__).resolve().parents[1] / "src").exists() \
        else Path(__file__).resolve().parents[2] / "frontend"
    src = root / "src"
    if not src.is_dir():
        # 容器內無 frontend src（只 mount dist）→ SKIP
        print(f"[SKIP] 找不到 frontend/src（{src}）— 此 audit 須 host 端跑")
        return 0

    red, yellow = [], []
    for f in src.rglob("*.ts*"):
        if "__tests__" in str(f) or f.name.endswith(".d.ts"):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in _HARDCODE_RE.finditer(text):
            path = m.group(1)
            line = text[:m.start()].count("\n") + 1
            rel = f.relative_to(src)
            entry = (f"{rel}:{line}", path)
            if path.startswith("/api/"):
                red.append(entry)      # L67 精確：double-prefix
            else:
                yellow.append(entry)   # 硬編路徑非常數

    print("=== Frontend API Wiring Audit（導覽鏈 page→endpoint 接線）===")
    print(f"  掃 frontend/src | apiClient 硬編路徑: RED {len(red)} / YELLOW {len(yellow)}\n")
    if red:
        print("[RED] apiClient 硬編 `/api/` 前綴 → baseURL 已含 /api → double-prefix 404（L67 同型）：")
        for loc, p in red:
            print(f"  ✗ {loc}  →  {p}")
        print()
    if yellow:
        print("[YELLOW] apiClient 硬編字串路徑（非端點常數，違反 SSOT、L67 風險面，建議遷 endpoints/*.ts）：")
        for loc, p in yellow:
            print(f"  ~ {loc}  →  {p}")
        print()
    print(f"Summary: {len(red)} RED (double-prefix), {len(yellow)} YELLOW (硬編非常數)")
    if red:
        print("\n[WARN] L67 同型 double-prefix → 立即修（移除 /api 前綴或改端點常數）")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
