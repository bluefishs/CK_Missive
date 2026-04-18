#!/usr/bin/env python3
"""
Synthetic Baseline Inject — 注入模擬查詢到 /api/ai/agent/query_sync 以加速 Hermes 基線採集。

每次執行注入 N 筆（預設 20），覆蓋 5 大領域 × 多種 query pattern。
shadow_logger 會自動記錄成功/失敗/延遲。

Usage:
    python scripts/checks/synthetic-baseline-inject.py [--count 20] [--base-url http://localhost:8001]

Schedule via PM2 / cron:
    每日 09:00、14:00、20:00 各執行一次，3 天可累積 180+ 筆。

Version: 1.0.0
Created: 2026-04-17
"""
import argparse
import json
import logging
import random
import sys
import time
from typing import List, Dict

try:
    import httpx
except ImportError:
    print("需要 httpx: pip install httpx", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 5 大領域 × 多種 query，模擬真實用戶問法
QUERY_POOL: List[Dict[str, str]] = [
    # 公文查詢
    {"q": "最近有哪些收文？", "domain": "document"},
    {"q": "桃園市政府的來文有幾封？", "domain": "document"},
    {"q": "今天到期的公文", "domain": "document"},
    {"q": "幫我查 113 年的發文清單", "domain": "document"},
    # 派工/作業
    {"q": "派工單 11301-001 的進度如何？", "domain": "dispatch"},
    {"q": "哪些派工單已逾期？", "domain": "dispatch"},
    {"q": "查估專區目前有幾件進行中？", "domain": "dispatch"},
    {"q": "承辦人老蕭負責的案件有哪些？", "domain": "dispatch"},
    # ERP 財務
    {"q": "本月費用報銷總額多少？", "domain": "erp"},
    {"q": "哪些案件有未審批的費用？", "domain": "erp"},
    {"q": "統一帳本餘額查��", "domain": "erp"},
    {"q": "應付帳款到期提醒", "domain": "erp"},
    # 標案
    {"q": "搜尋桃園市測量相關標案", "domain": "tender"},
    {"q": "最近有什麼新決標？", "domain": "tender"},
    {"q": "查詢底價分析", "domain": "tender"},
    {"q": "推薦適合我們的標案", "domain": "tender"},
    # 跨領域 / Agent 能力
    {"q": "今天的晨報內容", "domain": "cross"},
    {"q": "你有什麼功能？", "domain": "cross"},
    {"q": "幫我整理本週工作���要", "domain": "cross"},
    {"q": "知識圖譜有多少實體？", "domain": "cross"},
    # 閒聊 / 邊界（快速回應，不觸發工具，Ollama 1-3s）
    {"q": "你好", "domain": "chitchat"},
    {"q": "天氣如何？", "domain": "chitchat"},
    {"q": "謝謝你的幫助", "domain": "chitchat"},
    {"q": "可以幫我訂便當嗎", "domain": "chitchat"},
    # 短問句（加速基線累積，p95 < 5s）
    {"q": "嗨", "domain": "fast"},
    {"q": "早安", "domain": "fast"},
    {"q": "OK", "domain": "fast"},
    {"q": "了解", "domain": "fast"},
    {"q": "再見", "domain": "fast"},
    {"q": "你是誰", "domain": "fast"},
    {"q": "功能", "domain": "fast"},
    {"q": "幫我", "domain": "fast"},
    {"q": "測試", "domain": "fast"},
    {"q": "狀態", "domain": "fast"},
    {"q": "謝謝", "domain": "fast"},
    {"q": "好的", "domain": "fast"},
]


def inject_queries(base_url: str, count: int, timeout: float = 120.0, token: str = "") -> dict:
    """注入 count 筆查詢，回傳統計結果。"""
    selected = random.sample(QUERY_POOL, min(count, len(QUERY_POOL)))
    if count > len(QUERY_POOL):
        selected += random.choices(QUERY_POOL, k=count - len(QUERY_POOL))

    stats = {"total": 0, "success": 0, "error": 0, "timeout": 0, "latencies": []}
    url = f"{base_url}/api/ai/agent/query"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["X-Service-Token"] = token

    with httpx.Client(timeout=timeout, verify=False, headers=headers) as client:
        for i, item in enumerate(selected):
            stats["total"] += 1
            payload = {
                "question": item["q"],
                "channel": "web",
                "session_id": f"synthetic-{int(time.time())}-{i}",
            }
            t0 = time.monotonic()
            try:
                resp = client.post(url, content=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                latency_ms = int((time.monotonic() - t0) * 1000)
                stats["latencies"].append(latency_ms)
                if resp.status_code == 200:
                    stats["success"] += 1
                    logger.info(
                        "[%d/%d] OK %dms domain=%s q=%s",
                        i + 1, count, latency_ms, item["domain"], item["q"][:40],
                    )
                else:
                    stats["error"] += 1
                    logger.warning(
                        "[%d/%d] HTTP %d %dms q=%s",
                        i + 1, count, resp.status_code, latency_ms, item["q"][:40],
                    )
            except httpx.TimeoutException:
                latency_ms = int((time.monotonic() - t0) * 1000)
                stats["timeout"] += 1
                stats["latencies"].append(latency_ms)
                logger.error("[%d/%d] TIMEOUT %dms q=%s", i + 1, count, latency_ms, item["q"][:40])
            except Exception as e:
                stats["error"] += 1
                logger.error("[%d/%d] ERROR q=%s: %s", i + 1, count, item["q"][:40], e)

            # 隨機間隔（短問句快速、複雜問句慢）
            time.sleep(random.uniform(0.5, 1.5))

    # 計算百分位
    latencies = sorted(stats["latencies"])
    if latencies:
        stats["p50"] = latencies[len(latencies) // 2]
        stats["p95"] = latencies[int(len(latencies) * 0.95)]
        stats["mean"] = sum(latencies) // len(latencies)
    return stats


def main():
    parser = argparse.ArgumentParser(description="Synthetic baseline query injection")
    parser.add_argument("--count", type=int, default=20, help="Number of queries to inject")
    parser.add_argument("--base-url", default="http://localhost:8001", help="Backend base URL")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout (seconds)")
    parser.add_argument("--token", default="", help="X-Service-Token (reads MCP_SERVICE_TOKEN from .env if empty)")
    args = parser.parse_args()

    # Auto-read token from .env if not provided
    token = args.token
    if not token:
        import pathlib
        env_path = pathlib.Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("MCP_SERVICE_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    logger.info("=== Synthetic Baseline Inject ===")
    logger.info("Target: %s, Count: %d, Token: %s", args.base_url, args.count, "set" if token else "none")

    stats = inject_queries(args.base_url, args.count, args.timeout, token=token)

    logger.info("=== Results ===")
    logger.info(
        "Total=%d Success=%d Error=%d Timeout=%d",
        stats["total"], stats["success"], stats["error"], stats["timeout"],
    )
    if stats.get("p50"):
        logger.info("Latency p50=%dms p95=%dms mean=%dms", stats["p50"], stats["p95"], stats["mean"])

    # JSON 輸出供排程器採集
    print(json.dumps(stats, indent=2))

    # 非零退出表示有問題
    if stats["success"] < stats["total"] * 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
