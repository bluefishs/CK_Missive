"""排程器必須有夠長的 misfire_grace_time。

2026-08-16：`ezbid_cache_refresh`（每小時）最後執行停在 01:26，
14:15 那次排定時刻**完全沒有 Running job 紀錄** —— 被靜靜 misfire 掉。

根因：APScheduler 的 `misfire_grace_time` **預設是 1 秒**，
排定時刻起算超過 1 秒沒被排到就整個跳過，而且不留下任何錯誤。
5 分鐘週期的 job 一天有 288 次機會，偶爾錯過看不出來；
**每小時的 job 一次沒排到就整整少一小時**。

這是 L72 的同一個根因（當時修 cleanup_events/security_scan/fitness_daily
三支「02:00 壅塞 skip 從不執行」），但當時只修了那三支 ——
全檔 52 個 add_job 有 38 個沒有這個參數。改設在 job_defaults：
一個地方，不會有第 39 個漏網的。
"""
import re
from pathlib import Path

SCHED = Path(__file__).resolve().parents[2] / "app" / "core" / "scheduler.py"


def test_scheduler_has_job_defaults_misfire():
    src = SCHED.read_text(encoding="utf-8")
    # 原始碼裡的建構是多行的（含註解），用 DOTALL 抓 AsyncIOScheduler( 之後那一段
    i = src.find("AsyncIOScheduler(")
    assert i > 0, "找不到 AsyncIOScheduler 建構"
    body = src[i:i + 400]
    assert "job_defaults" in body, "沒有設 job_defaults —— misfire_grace_time 會回到 1 秒預設"
    grace = re.search(r'"misfire_grace_time":\s*(\d+)', body)
    assert grace, "job_defaults 裡沒有 misfire_grace_time"
    assert int(grace.group(1)) >= 600, (
        f"misfire_grace_time 只有 {grace.group(1)} 秒 —— "
        "小時級的 job 一次沒排到就整整少一小時"
    )


def test_runtime_scheduler_actually_carries_the_default():
    """設在原始碼不算數 —— 要真的建得出帶著那個預設的實例。"""
    from app.core.scheduler import get_scheduler
    s = get_scheduler()
    assert s._job_defaults.get("misfire_grace_time", 1) >= 600, (
        "實例上的 misfire_grace_time 不是預期值 —— 設了但沒生效"
    )
