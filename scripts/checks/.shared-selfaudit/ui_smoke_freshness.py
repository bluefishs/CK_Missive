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
import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MAX_AGE_HOURS = 30  # 每日排程 + 6h 寬限


def _find_config() -> Path:
    """往上找 selfaudit.config.json —— 引擎位置可能是原生或 vendored（深度不同），
    不可寫死上推層數（2026-08-01 CK_Missive 改 vendored 消費時立刻指錯）。"""
    env = os.environ.get("SELFAUDIT_CONFIG")
    if env and Path(env).exists():
        return Path(env)
    here = Path(__file__).resolve().parent
    for _ in range(6):
        cand = here / "selfaudit.config.json"
        if cand.exists():
            return cand
        if here.parent == here:
            break
        here = here.parent
    raise SystemExit("找不到 selfaudit.config.json（頁面層檢核未設定）")


# 監看路徑必須**與引擎的輸出設定同源**——初版兩邊各寫一份，
# 改了 config 的 output 之後這裡仍看舊路徑 → 檢核器自己回報「從未執行」。
# 這正是本專案一再治理的「同一事實兩份來源」（異質同工）。
_CFG_PATH = _find_config()
_CFG = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
ROOT = _CFG_PATH.parent
TARGETS = [
    ("流程檢核", _CFG["output"]["flow_result"]),
    ("全站掃描", _CFG["output"]["sweep_result"]),
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
    # 入口腳本名各 repo 不同（Missive=run_ui_smoke.sh、lvrland=run_selfaudit.sh）
    # → 從 config 取，不寫死；寫死的話提示會叫人去跑不存在的檔案。
    entry = _CFG.get("entry_script", "scripts/checks/run_selfaudit.sh")
    print(f"修法：bash {entry}        （流程檢核）")
    print(f"      bash {entry} --sweep（全站掃描）")
    installer = _CFG.get("schedule_installer")
    if installer:
        print(f"      排程未安裝：powershell -File {installer}")
    return 1 if args.ci else 0


if __name__ == "__main__":
    sys.exit(main())
