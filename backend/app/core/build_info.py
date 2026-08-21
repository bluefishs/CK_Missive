"""runtime 版本 —— 回答「現在跑的是哪一份程式碼」。

## 為什麼有這支（2026-08-21）

owner 要求「版次皆已同步」。查文件版次時全部一致，但實測 runtime 發現
**四個來源四個值，而且 health 根本不回版本**：

    health.version              None        ← 完全沒有
    backend/main.py FastAPI     "3.0.1"     ← 註解寫「Trigger reload for audit fix」
    frontend/package.json       "0.0.0"
    CLAUDE.md                   v6.60

⇒ **沒有任何方式能知道公網跑的是哪一版。** 事故當下沒有人說得出
「現在線上是修好的版本還是沒修的版本」——而那正是最需要知道的時刻。

（CK_AaaP 同日發現同型：同一服務四個來源三個數字，且**沒有任何程式碼讀
平臺指定的 SSOT**。他們第一次只改了其中一處，重啟後 health 照樣回舊值，
畫面上完全看不出差別。）

## 為什麼是 commit 而不是一個人維護的數字

runtime 版本要回答的是「跑的是哪一份程式碼」，那由 commit 決定。
人維護的語意版本號（v6.60）回答的是另一個問題（這一輪做了什麼），
兩者都需要，但**不能互相冒充**。

## 讀不到就說讀不到

回 `"unknown"` 而不是某個看起來正常的預設值 —— 一個看起來正常的版本號
會讓人以為驗證過了，那比沒有更危險（本專案反覆記的判準）。
"""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

#: build 時由 docker build --build-arg 注入（見 backend/Dockerfile）。
#: 容器內沒有 .git，所以 runtime 推導不出來，只能在 build 當下釘住。
_ENV_COMMIT = "CK_BUILD_COMMIT"
_ENV_TIME = "CK_BUILD_TIME"

UNKNOWN = "unknown"


@lru_cache(maxsize=1)
def _git_commit() -> str:
    """host 開發時的後備 —— 容器內拿不到（沒有 .git），會回 unknown。"""
    try:
        root = Path(__file__).resolve().parents[3]
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        # 拿不到就是拿不到 —— 不編一個值出來
        pass
    return UNKNOWN


@lru_cache(maxsize=1)
def build_info() -> dict[str, str]:
    """回 runtime 的身分證。所有欄位都可能是 "unknown"，那是誠實的答案。"""
    commit = os.getenv(_ENV_COMMIT, "").strip() or _git_commit()
    return {
        "commit": commit or UNKNOWN,
        "built_at": os.getenv(_ENV_TIME, "").strip() or UNKNOWN,
        #: 來源是 build 注入還是 host 推導 —— 讓讀的人知道這個值有多可信。
        "source": "build-arg" if os.getenv(_ENV_COMMIT) else (
            "git" if commit != UNKNOWN else "none"),
    }
