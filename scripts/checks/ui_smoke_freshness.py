# -*- coding: utf-8 -*-
"""UI 自我檢核產出新鮮度（fitness step 77，2026-07-31）

owner：「無法針對前後端與頁面 UI 等管控與檢測」。

治理缺口：既有 fitness 只驗**原始碼與資料**（路由註冊、型別 SSOT、cron 產出），
端點探針只驗 **API 狀態碼** —— 兩者都不會告訴你「這一頁打開來是壞的」。
2026-07-31 當日多起缺陷正是「API 200、程式碼看起來對，但畫面上沒有那個東西」。

UI 檢核（ui_flow_smoke / ui_page_sweep）由 Windows 排程每日執行，
本步驟只做兩件事：
  1. 產出是否新鮮（沒跑就是沒跑，避免「以為有在檢核」）
  2. 上次結果有沒有 FAIL

刻意**不在此步驟啟動瀏覽器**：fitness 是可重複、快速、無副作用的靜態檢查，
把耗時的瀏覽器工作留給排程；此處只驗其成果（同 CF Tunnel 驗證的作法）。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
MAX_AGE_HOURS = 30  # 每日排程 + 6h 寬限

TARGETS = [
    ("流程檢核", "wiki/memory/integration-health/ui-flow.json"),
    ("全站掃描", "wiki/memory/integration-health/ui-sweep.json"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true", help="有問題即 exit 1")
    args = ap.parse_args()

    print("=" * 60)
    print("UI 自我檢核產出新鮮度（頁面層管控）")
    print("=" * 60)

    problems: list[str] = []
    for label, rel in TARGETS:
        p = ROOT / rel
        if not p.exists():
            print(f"  [RED  ] {label}：尚未產出 {rel}")
            problems.append(f"{label} 從未執行")
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  [RED  ] {label}：結果檔無法解析 — {e}")
            problems.append(f"{label} 結果檔損毀")
            continue

        ts = data.get("checked_at", "")
        try:
            when = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_h = (datetime.now(timezone.utc) - when).total_seconds() / 3600
        except Exception:
            age_h = 9999.0

        n_fail = int(data.get("fail", 0))
        n_pass = int(data.get("pass", 0))

        if age_h > MAX_AGE_HOURS:
            print(f"  [RED  ] {label}：{age_h:.1f}h 前（門檻 {MAX_AGE_HOURS}h）— 排程可能沒在跑")
            problems.append(f"{label} 產出過期 {age_h:.0f}h")
        elif n_fail:
            fails = data.get("failures", [])
            print(f"  [RED  ] {label}：{age_h:.1f}h 前 / PASS {n_pass} / **FAIL {n_fail}**")
            for f in fails[:5]:
                who = f.get("route") or f.get("name") or f.get("id") or "?"
                why = f.get("reason") or "; ".join(f.get("problems", []))
                print(f"           - {who} — {str(why)[:90]}")
            problems.append(f"{label} 有 {n_fail} 項失敗")
        else:
            print(f"  [GREEN] {label}：{age_h:.1f}h 前 / PASS {n_pass} / FAIL 0")

    print()
    if not problems:
        print("GREEN — 頁面層檢核持續在跑且無失敗")
        return 0

    print(f"RED — {len(problems)} 項：")
    for x in problems:
        print(f"  - {x}")
    print()
    print("修法：bash scripts/checks/run_ui_smoke.sh        （流程檢核）")
    print("      bash scripts/checks/run_ui_smoke.sh --sweep（全站掃描）")
    print("      排程未安裝：powershell -File scripts/deploy/install-ui-smoke-task.ps1")
    return 1 if args.ci else 0


if __name__ == "__main__":
    sys.exit(main())
