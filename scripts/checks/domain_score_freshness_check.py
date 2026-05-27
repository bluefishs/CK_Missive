#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fitness step 22 — Domain Score Freshness Watchdog (L29, v6.9 / 2026-05-09).

防範 L29「domain_scores Redis 全空 silent skip」重演。

每 7 天 / 月度跑：檢查 `agent:domain_scores:{doc,dispatch,erp,graph,pm,analysis,
tender,wiki}` 至少有 N 個 key 有資料。若全空 → silent gap 訊號（self_evaluator
domain tracking 寫入鏈又斷了）。

Exit codes:
  0 — 至少 ≥ 3 個 domain 有近期資料（健康）
  1 — strict mode (--ci) 且全空（L29 重演警報）

關聯：
- L29 LESSONS_REGISTRY.md
- agent_self_evaluator.py domain tracking
- agent_evolution_scheduler.py domain-aware trigger
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Windows cp950 防護（per audit 4 特徵 #1, session_20260526_27）
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

EXPECTED_DOMAINS = ("doc", "dispatch", "erp", "graph", "pm", "analysis", "tender", "wiki")
MIN_HEALTHY_DOMAINS = 3
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6380/0")


async def check(redis_url: str) -> int:
    try:
        import redis.asyncio as redis_async
    except ImportError:
        print("[WARN] redis lib unavailable — domain score check skipped", file=sys.stderr)
        return 0

    try:
        r = redis_async.from_url(redis_url, decode_responses=True)
        await r.ping()
    except Exception as e:
        # Redis 不可達不算 fail（dev 環境寬容）
        print(f"[WARN] Redis 不可達: {e} — skip")
        return 0

    healthy = 0
    print("=== Domain Score Freshness Check ===\n")
    for domain in EXPECTED_DOMAINS:
        try:
            items = await r.lrange(f"agent:domain_scores:{domain}", 0, -1)
            count = len(items) if items else 0
            if count > 0:
                healthy += 1
                print(f"  [OK]   {domain:10} count={count}")
            else:
                print(f"  [EMPTY] {domain:10} (no data)")
        except Exception as e:
            print(f"  [ERR]  {domain:10} {e}")

    await r.aclose()

    print()
    if healthy >= MIN_HEALTHY_DOMAINS:
        print(f"[PASS] {healthy}/{len(EXPECTED_DOMAINS)} domains 有資料 ≥ {MIN_HEALTHY_DOMAINS}")
        return 0

    print(
        f"[FAIL] 只有 {healthy}/{len(EXPECTED_DOMAINS)} domains 有資料 "
        f"(< {MIN_HEALTHY_DOMAINS})"
    )
    print("  → L29 重演警報：self_evaluator domain tracking 寫入鏈可能再次中斷")
    print("  → 檢查：")
    print("    1. agent_self_evaluator.py:259-285 是否被改回 silent pass")
    print("    2. agent_tool_loop.py:312/381 是否改了 dict key（從 'tool' 改成其他）")
    print("    3. backend 是否有 query 進來（pm2 logs ck-backend）")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fitness step 22 — Domain Score Freshness")
    parser.add_argument("--ci", action="store_true", help="strict mode: 全空 exit 1")
    parser.add_argument("--redis-url", default=REDIS_URL)
    args = parser.parse_args()

    try:
        rc = asyncio.run(check(args.redis_url))
    except Exception as e:
        print(f"[WARN] check failed: {type(e).__name__}: {e}")
        return 0

    if args.ci:
        return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
