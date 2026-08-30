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
import ast
from pathlib import Path

SCHED = Path(__file__).resolve().parents[2] / "app" / "core" / "scheduler.py"


def test_scheduler_has_job_defaults_misfire():
    """建構排程器時必須帶 job_defaults.misfire_grace_time。

    ⚠️ 2026-08-30 改用 AST：原本是 `src.find("AsyncIOScheduler(")` 取後 400 字元。
    A50 加了 `class _RecoveringAsyncIOScheduler(AsyncIOScheduler):` 之後，
    那個 find **先命中類別定義**而不是實例化 ⇒ 測試紅了，而 `job_defaults`
    其實還在（同一批的執行時測試一直是綠的）。
    **文字搜尋的判準會被無關的改動打斷** —— 改成找「真正被呼叫的建構式」。
    """
    tree = ast.parse(SCHED.read_text(encoding="utf-8"))
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id.endswith("AsyncIOScheduler")
    ]
    assert calls, "找不到任何 *AsyncIOScheduler(...) 的建構呼叫"

    for call in calls:
        kw = next((k for k in call.keywords if k.arg == "job_defaults"), None)
        assert kw is not None, (
            f"第 {call.lineno} 行的排程器建構沒有設 job_defaults —— "
            "misfire_grace_time 會回到 1 秒預設"
        )
        grace = None
        if isinstance(kw.value, ast.Dict):
            for k, v in zip(kw.value.keys, kw.value.values):
                if isinstance(k, ast.Constant) and k.value == "misfire_grace_time" \
                        and isinstance(v, ast.Constant):
                    grace = v.value
        assert grace is not None, f"第 {call.lineno} 行的 job_defaults 裡沒有 misfire_grace_time"
        assert grace >= 600, (
            f"misfire_grace_time 只有 {grace} 秒 —— "
            "小時級的 job 一次沒排到就整整少一小時"
        )


def test_runtime_scheduler_actually_carries_the_default():
    """設在原始碼不算數 —— 要真的建得出帶著那個預設的實例。"""
    from app.core.scheduler import get_scheduler
    s = get_scheduler()
    assert s._job_defaults.get("misfire_grace_time", 1) >= 600, (
        "實例上的 misfire_grace_time 不是預期值 —— 設了但沒生效"
    )
