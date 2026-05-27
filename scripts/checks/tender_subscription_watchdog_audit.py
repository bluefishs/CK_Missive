#!/usr/bin/env python3
"""
Tender Subscription Scheduler Watchdog (fitness step 53, v6.12 P3 L48 family)

監測 `tender_subscription_check_total` Prometheus counter，
24h 內若 0 次 invocation → RED（同 L48 cron silent dormant 教訓）。

觸發背景：
- L48 揭發 PCC scraper 50 天 silent dormant — scheduler job 缺 cron entry
- 同型風險：subscription_scheduler.check_all_subscriptions() 若未排程
  將 silent dormant，標案訂閱通知系統靜默失效

檢查邏輯：
1. 從 backend /metrics 抓 `tender_subscription_check_total{status}` 值
2. 與本地檔 .checks-state/tender_subscription_last_count.json 對比
3. 24h 內 invocation 數 == 0 → RED
4. 接著更新 state 檔（記錄本次 count + timestamp）

Fail mode：
- backend 不可達 → YELLOW（環境問題，非邏輯議題）
- counter 不存在 → YELLOW（metric module 沒裝）
- count 24h 0 increase → RED（真實 silent dormant）

Version: 1.0.0
Created: 2026-05-28 Step 5C
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

try:
    import httpx
except ImportError:
    print("⚠️  httpx not installed — install with: pip install httpx")
    sys.exit(2)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_DIR = REPO_ROOT / ".checks-state"
STATE_FILE = STATE_DIR / "tender_subscription_last_count.json"
METRICS_URL = os.environ.get("METRICS_URL", "http://localhost:8001/metrics")
DORMANT_THRESHOLD_HOURS = 24


def fetch_counter() -> Optional[Dict[str, float]]:
    """從 /metrics 抓 tender_subscription_check_total 各 status 值。

    回傳 {status: float, ...} 或 None（無法取得時）。
    """
    try:
        r = httpx.get(METRICS_URL, timeout=10.0)
        if r.status_code != 200:
            print(f"⚠️  /metrics returned {r.status_code}")
            return None
        text = r.text
    except Exception as e:
        print(f"⚠️  cannot reach {METRICS_URL}: {e}")
        return None

    # parse prometheus exposition format
    # tender_subscription_check_total{status="invoked"} 42.0
    counters: Dict[str, float] = {}
    metric_name = "tender_subscription_check_total"
    for line in text.splitlines():
        if not line.startswith(metric_name):
            continue
        if "{" not in line or "}" not in line:
            continue
        # extract status label
        labels_part = line[line.index("{") + 1:line.index("}")]
        value_part = line[line.index("}") + 1:].strip()
        status = None
        for kv in labels_part.split(","):
            k, _, v = kv.partition("=")
            if k.strip() == "status":
                status = v.strip().strip('"')
                break
        if status is None:
            continue
        try:
            counters[status] = float(value_part)
        except ValueError:
            continue

    return counters if counters else None


def load_state() -> Optional[Dict]:
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state(state: Dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender subscription scheduler watchdog")
    parser.add_argument("--strict", action="store_true", help="RED 觸發 exit 1")
    args = parser.parse_args()

    print("=" * 72)
    print("[53/53] Tender Subscription Scheduler Watchdog (L48 family)")
    print("=" * 72)

    counters = fetch_counter()
    if counters is None:
        print(f"\n🟡 YELLOW — 無法取得 metric (backend not running?)")
        print(f"  metrics_url = {METRICS_URL}")
        print(f"  跳過此次檢查（環境問題，非邏輯議題）")
        return 0

    invoked_count = counters.get("invoked", 0)
    success_count = counters.get("success", 0)
    error_count = counters.get("error", 0)
    no_subs_count = counters.get("no_subs", 0)

    print(f"\n當前 metric snapshot:")
    print(f"  invoked: {invoked_count:.0f}")
    print(f"  success: {success_count:.0f}")
    print(f"  no_subs: {no_subs_count:.0f}")
    print(f"  error  : {error_count:.0f}")

    now = datetime.utcnow()
    state = load_state()

    if state is None:
        # 首次跑 — 初始化 state，不判定 RED（無歷史可比）
        print(f"\n🟢 GREEN — first run, initializing state (no history to compare)")
        save_state({
            "last_invoked_count": invoked_count,
            "last_check_at": now.isoformat(),
        })
        return 0

    last_count = state.get("last_invoked_count", 0)
    last_check_str = state.get("last_check_at", "")
    try:
        last_check = datetime.fromisoformat(last_check_str)
    except Exception:
        last_check = now - timedelta(hours=DORMANT_THRESHOLD_HOURS + 1)

    elapsed_hours = (now - last_check).total_seconds() / 3600
    delta = invoked_count - last_count

    print(f"\n與上次比對 (elapsed={elapsed_hours:.1f}h):")
    print(f"  last_count = {last_count:.0f}")
    print(f"  current    = {invoked_count:.0f}")
    print(f"  delta      = {delta:+.0f}")

    # 更新 state（無論結果如何）
    save_state({
        "last_invoked_count": invoked_count,
        "last_check_at": now.isoformat(),
    })

    # 判定
    if elapsed_hours < 1:
        # 太短，跳過判定
        print(f"\n🟢 GREEN — elapsed < 1h, defer judgment to next run")
        return 0

    if elapsed_hours >= DORMANT_THRESHOLD_HOURS and delta == 0:
        print(f"\n🔴 RED — subscription scheduler 24h+ no invocation (silent dormant)")
        print(f"  修法指引：")
        print(f"  1. 檢查 main.py startup 是否 register check_all_subscriptions 排程")
        print(f"  2. 檢查 APScheduler 是否 running")
        print(f"  3. 對照 L48 lesson — cron entry 遺漏")
        if args.strict:
            return 1
        return 0

    if delta > 0:
        rate_per_hour = delta / max(elapsed_hours, 1)
        print(f"\n🟢 GREEN — invocation rate {rate_per_hour:.1f}/h (healthy)")
    else:
        print(f"\n🟡 YELLOW — delta=0 in {elapsed_hours:.1f}h "
              f"(<24h, monitor closely)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
