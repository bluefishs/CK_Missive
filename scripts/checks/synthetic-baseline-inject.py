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
    # 2026-04-29：修正 2 條無解 query（v5.10.2 #4 evolution 修復後配套）
    # - 「派工單 11301-001」格式錯（實際 dispatch_no 為「115年_派工單號021」）
    # - 「承辦人老蕭」系統內無此人（13 個 distinct case_handler 無「蕭」）
    # 兩條無解 query 每日 cron 3x 注入會誤導 evolution pattern，且
    # 04-23 diary 已觀察到 agent 在無解場景產生 hallucination（列 6 個無關
    # 公文後否認）→ 改用系統實際存在的單號 + 承辦人名
    {"q": "派工單 115年_派工單號021 的進度如何？", "domain": "dispatch"},
    {"q": "哪些派工單已逾期？", "domain": "dispatch"},
    {"q": "查估專區目前有幾件進行中？", "domain": "dispatch"},
    {"q": "承辦人劉虹吟負責的案件有哪些？", "domain": "dispatch"},
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

    stats = {
        "total": 0, "success": 0, "error": 0, "timeout": 0,
        "latencies": [],
        # P1-5 (2026-04-22)：內容衛生量測 — 偵測 bot 回應含類詐騙特徵
        "content_risk_hits": 0,       # 身分證/金額/長編號 擊中數
        "scam_keyword_hits": 0,       # 反詐騙詞彙擊中數
        "risky_samples": [],           # 最多保留 3 則樣本供人工檢視
    }
    # 延遲載入 sanitizer（單元模組，無 backend 依賴）
    try:
        sys.path.insert(0, str((__import__("pathlib").Path(__file__).resolve().parents[2] / "backend").resolve()))
        from app.services.common.telegram_content_sanitizer import (  # type: ignore
            sanitize, has_scam_keywords,
        )
    except Exception:
        sanitize = None  # type: ignore
        has_scam_keywords = None  # type: ignore

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
                    # P1-5：檢查 bot 回應內容衛生
                    if sanitize is not None:
                        try:
                            body = resp.json()
                            answer = body.get("answer") or body.get("result", {}).get("answer") or ""
                            cleaned = sanitize(answer)
                            if cleaned != answer:
                                stats["content_risk_hits"] += 1
                                if len(stats["risky_samples"]) < 3:
                                    stats["risky_samples"].append({
                                        "q": item["q"],
                                        "raw_snippet": answer[:120],
                                        "masked_snippet": cleaned[:120],
                                    })
                            if has_scam_keywords and has_scam_keywords(answer):
                                stats["scam_keyword_hits"] += 1
                        except Exception:
                            pass  # sanitizer 量測失敗不影響基線主流程
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

    # P1-5：內容衛生量測告警（若擊中 → 觸發 LINE admin push 觀察）
    risk = stats.get("content_risk_hits", 0) + stats.get("scam_keyword_hits", 0)
    if risk > 0:
        logger.warning(
            "⚠ 內容衛生告警：%d 次擊中（risk=%d scam_kw=%d）— bot 回應含類詐騙特徵，請檢查 LLM 輸出",
            risk, stats["content_risk_hits"], stats["scam_keyword_hits"],
        )
        if stats.get("risky_samples"):
            logger.warning("樣本：%s", json.dumps(stats["risky_samples"], ensure_ascii=False))

    # JSON 輸出供排程器採集
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    # 非零退出表示有問題
    if stats["success"] < stats["total"] * 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
