"""回歸鎖：排程持久化 + 錯過的觸發要救得回來（A50 / L117）。

## 這支鎖的是什麼

2026-08-30 之前 `AsyncIOScheduler(...)` **沒有指定 jobstore ⇒ 預設
`MemoryJobStore`**。重啟後 job 是全新註冊的，**根本不存在「錯過的觸發」
這筆紀錄** —— `misfire_grace_time` 防的是「排程器活著但忙過頭」，
防不了重啟。實據：`optimization_pipeline`（每日 03:00）08-29／08-30
兩天沒跑，而 08-30 的 `scheduler_start` 落在 **03:00:19**。

⚠️ **光加持久化不夠**。讀 APScheduler 3.11.1 `BaseScheduler._real_add_job`：

    if not hasattr(job, "next_run_time"):
        replacements["next_run_time"] = job.trigger.get_next_fire_time(None, now)
    ...
    except ConflictingIdError:
        if replace_existing:
            store.update_job(job)      # 用剛算的未來時間覆蓋掉存起來的

而本 repo 56 處 `add_job` **全部**帶 `replace_existing=True`。
容器內實測（複製正式程式的順序：先 add_job 再 start）：

    修法版 執行次數 = 1（接回 fixjob）
    原生版 執行次數 = 0   ← 只有持久化、沒有修法 ⇒ 錯過的觸發被靜靜丟掉

⇒ 三個結構事實缺一不可，本測試逐一鎖住。

## 為什麼用 AST 不連真的 DB

真跑要 Postgres、要等排程執行緒，會讓單元測試變慢且不穩；
而這三件事是**純結構**的，靜態就驗得出來。行為層的證據留在
上面那段實測紀錄與 L117。
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHED = ROOT / "backend/app/core/scheduler.py"


def _tree() -> ast.AST:
    return ast.parse(SCHED.read_text(encoding="utf-8"))


def test_scheduler_uses_persistent_jobstore():
    """`get_scheduler()` 必須帶 jobstores —— 少了它就退回 MemoryJobStore。"""
    tree = _tree()
    found = False
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or fn.name != "get_scheduler":
            continue
        for n in ast.walk(fn):
            if isinstance(n, ast.Call) and any(
                kw.arg == "jobstores" for kw in n.keywords
            ):
                found = True
    assert found, (
        "get_scheduler() 沒有傳 jobstores ⇒ APScheduler 會用 MemoryJobStore，"
        "重啟時錯過的觸發會被靜靜丟掉（A50 / L117）"
    )


def test_recovering_scheduler_overrides_real_add_job():
    """必須覆寫 `_real_add_job` —— 那是唯一能在 jobstore 已 start 後、
    且在 next_run_time 被重算前介入的點。"""
    tree = _tree()
    cls = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.ClassDef) and n.name == "_RecoveringAsyncIOScheduler"),
        None,
    )
    assert cls is not None, "_RecoveringAsyncIOScheduler 不見了（A50 修法的核心）"
    methods = {m.name for m in cls.body if isinstance(m, ast.FunctionDef)}
    assert "_real_add_job" in methods, (
        "沒有覆寫 _real_add_job ⇒ replace_existing=True 會把錯過的觸發沖掉，"
        "持久化等於白做"
    )


def test_every_add_job_still_uses_replace_existing():
    """56 處 add_job 全帶 replace_existing —— 這正是修法必須存在的前提。

    若日後有人拿掉某一處，重啟會拋 ConflictingIdError；
    若全部拿掉，本修法就不再必要。兩種情況都該有人看一眼，故鎖住。
    """
    tree = _tree()
    total = missing = 0
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "add_job"):
            continue
        # ⚠️ 排除子類別自己的委派呼叫 `super().add_job(*args, **kwargs)` ——
        #    它沒有具名參數是理所當然的。首版判準沒排除它，於是報
        #    「1/56 沒有 replace_existing」這個假陽性（2026-08-30）。
        if isinstance(n.func.value, ast.Call) and \
                isinstance(n.func.value.func, ast.Name) and \
                n.func.value.func.id == "super":
            continue
        total += 1
        if not any(kw.arg == "replace_existing" for kw in n.keywords):
            missing += 1
    assert total >= 50, f"只掃到 {total} 個 add_job（預期 50+）—— 本測試可能已失效"
    assert missing == 0, (
        f"{missing}/{total} 個 add_job 沒有 replace_existing ⇒ "
        "持久化 jobstore 下重啟會拋 ConflictingIdError"
    )
