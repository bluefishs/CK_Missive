"""LINE 主題摘要緩衝 — 推播減量合併（owner 2026-06-30 決議、07-07 落地）

背景：LINE 免費月配額 200 則，06 月下旬用罄。各主題 job（自省 22:00 / cron 健康
06:30 / 吹哨者 00:30 / 標案訂閱 ×3/日）過去各自單推 → 4-10 則/日 × N 管理員。

機制：各主題 job 改呼叫 queue_digest(topic, text) 把「本要單推的文字」存入
Redis list（TTL 48h），每日 08:00 晨報 morning_report_job drain_digest() 取走、
以「昨日主題摘要」段併入唯一一則晨報推播 → 常規 1 則/日/管理員 ≈ 31×N/月。

容錯：Redis 不可用 → in-memory fallback（同進程有效；重啟丟失可接受——內容
皆另有 DB/wiki 落地，LINE 摘要屬 best-effort 通知層）。任何失敗絕不 raise
（通知層不得影響主流程，ADR-0028 吞錯理由：best-effort delivery）。

v1.0（2026-07-07）
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Dict, List
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_KEY = "line:digest:pending"
_TTL_S = 48 * 3600
TZ = ZoneInfo("Asia/Taipei")

# Redis 不可用時的同進程 fallback（best-effort）
_memory_buffer: List[dict] = []

# 測試隔離開關（2026-08-04）
# ---------------------------------------------------------------------------
# 08-03 把 5 個 job 從 Telegram 改走 digest 後，conftest 的「對外通知封鎖」安全網
# 就漏了：它擋的是**送出去**（抽掉 LINE/Telegram token），而 digest 是**寫進去、
# 明早才送**——寫的還是正式環境那把 Redis key。實測跑一次 unit test 就把 6 則假
# 告警（"job_a"、"DB connection lost"、假日期）塞進 owner 隔天的晨報；而 weekly
# 的 test_suite_health 每週都會跑全套 ⇒ **檢核機制本身會污染正式輸出**。
# 沿用安全網 v3 的思路：不替換任何方法，改為**拿掉它抵達正式狀態的能力**。
_ISOLATION_ENV = "CK_NOTIFY_TEST_ISOLATION"


def _is_isolated() -> bool:
    return os.getenv(_ISOLATION_ENV, "").strip().lower() in {"1", "true", "yes"}


def reset_memory_buffer() -> None:
    """測試用：清空同進程 fallback，避免跨測試互相污染。"""
    _memory_buffer.clear()

# 併入晨報時的總長上限（LINE 單則 5000 字；晨報本體 + 摘要留餘裕）
DIGEST_TAIL_MAX_CHARS = 1800


async def queue_digest(topic: str, text: str) -> bool:
    """主題 job 呼叫：把本要單推 LINE 的文字暫存，待晨報合併推送。"""
    item = {
        "topic": topic,
        "text": (text or "").strip(),
        "ts": datetime.now(TZ).strftime("%m-%d %H:%M"),
    }
    if not item["text"]:
        return False
    if _is_isolated():
        _memory_buffer.append(item)
        return True
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            await redis.lpush(_KEY, json.dumps(item, ensure_ascii=False))
            await redis.expire(_KEY, _TTL_S)
            logger.info("[line-digest] queued topic=%s len=%d", topic, len(item["text"]))
            return True
    except Exception as e:
        logger.warning("[line-digest] redis queue 失敗，落 in-memory: %s", e)
    _memory_buffer.append(item)
    logger.info("[line-digest] queued(memory) topic=%s", topic)
    return True


async def drain_digest() -> List[dict]:
    """晨報 job 呼叫：取走並清空所有暫存主題條目（Redis + memory，舊→新排序）。"""
    items: List[dict] = []
    if _is_isolated():
        items.extend(_memory_buffer)
        _memory_buffer.clear()
        return items
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            raw = await redis.lrange(_KEY, 0, -1)
            await redis.delete(_KEY)
            for r in reversed(raw):  # lpush 後 lrange 是新→舊，反轉回時序
                try:
                    items.append(json.loads(r))
                except Exception:
                    continue
    except Exception as e:
        logger.warning("[line-digest] redis drain 失敗: %s", e)
    if _memory_buffer:
        items.extend(_memory_buffer)
        _memory_buffer.clear()
    return items


async def restore_digest(items: List[dict]) -> int:
    """把 drain 出來但**沒能送出去**的條目放回佇列（2026-08-29）。

    ## 為什麼需要這支

    `drain_digest()` 是「讀取後立刻 delete」，而真正的送出在**幾十行之後**
    （scheduler 的 Step 4）。中間那段若失敗——最現實的情況是
    **LINE 月配額用罄**（本檔同族的 `_call_line_api` 有 429 monthly limit
    短路，配額用盡時直接回 False 不送）——那批主題摘要已經從 Redis 刪掉了，
    **永久遺失且沒有任何痕跡**。

    這與 CK_Website 2026-08-29 在他們 Worker `flushDigest` 上找到的是同一族：
    **「呼叫的返回被當成對方收到」**——我方單方面就能判定成功，不需要對方確認。
    他們提醒我掃自己的送出路徑，掃出了這一條。

    語意：digest 是**同一份內容送給多人**，所以「至少一個管道送達」即視為
    已送出、不回填；**全部失敗**才放回去等下一次晨報。
    回填用 rpush（佇列尾端）以維持時序：drain 時是 lrange + reversed，
    舊的在前，rpush 進去的會排在既有新條目之後仍屬正確時序。
    """
    if not items:
        return 0
    if _is_isolated():
        _memory_buffer.extend(items)
        return len(items)
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        if redis:
            for it in items:
                await redis.rpush(_KEY, json.dumps(it, ensure_ascii=False))
            await redis.expire(_KEY, _TTL_S)
            logger.warning(
                "[line-digest] %d 則主題摘要**未送達**，已放回佇列等下次晨報", len(items),
            )
            return len(items)
    except Exception as e:
        logger.error("[line-digest] 回填失敗，%d 則將遺失: %s", len(items), e, exc_info=True)
    _memory_buffer.extend(items)
    return len(items)


def build_digest_tail(items: List[dict]) -> str:
    """把主題條目組成晨報尾段（依主題分組、時序保留、總長 cap）。純函式可測。"""
    if not items:
        return ""
    grouped: Dict[str, List[dict]] = {}
    order: List[str] = []
    for it in items:
        t = it.get("topic") or "其他"
        if t not in grouped:
            grouped[t] = []
            order.append(t)
        grouped[t].append(it)

    lines: List[str] = ["", "━━ 昨日主題摘要 ━━"]
    for topic in order:
        lines.append(f"\n【{topic}】")
        for it in grouped[topic]:
            ts = it.get("ts", "")
            text = it.get("text", "")
            lines.append(f"({ts}) {text}" if ts else text)

    tail = "\n".join(lines)
    if len(tail) > DIGEST_TAIL_MAX_CHARS:
        tail = tail[: DIGEST_TAIL_MAX_CHARS - 20] + "\n…（其餘見系統內通知）"
    return tail
