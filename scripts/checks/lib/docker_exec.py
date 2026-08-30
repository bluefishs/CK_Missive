#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""在容器裡跑東西的單一入口 —— 不要自己拼 `docker exec`。

## 為什麼有這一支

2026-08-30 實測：`scripts/checks/*.py` 裡 **39 支自己開 `docker exec`**，
而每一支都得自己處理下面這幾個陷阱，漏一個就是靜默的錯：

| 陷阱 | 漏掉的後果 |
|---|---|
| **`MSYS_NO_PATHCONV=1`** | Git Bash 會把 `/app/logs` 改寫成 `D:/Program Files/Git/app/logs` ⇒ 容器裡找不到檔，而錯誤訊息看起來像「檔案不存在」 |
| **容器不在時的回傳** | 回 `""` 與回「容器沒跑」分不出來 ⇒ 「查不到」被當成「沒問題」 |
| **逾時** | 沒設就可能吊死整個 weekly |
| **編碼** | 容器輸出是 UTF-8，Windows 預設 cp950 ⇒ 中文變亂碼或直接拋例外 |

⇒ 這四件事應該只寫一次。

## 用法

    from lib.docker_exec import exec_in, container_running

    if not container_running():
        return 2          # 不可判定 ≠ 沒問題

    out = exec_in(["python", "-c", "print(1)"])
    if out is None:
        return 2          # 執行失敗，同樣不是通過

## 為什麼回 None 而不是空字串

「容器沒跑」「指令失敗」「輸出真的是空的」是三件不同的事。
回 `None` 讓呼叫端**必須**面對前兩種 —— 本 repo 反覆記過
「查不到」與「沒問題」在輸出上長得一樣的事故。
"""
from __future__ import annotations

import os
import subprocess
from typing import Optional, Sequence

DEFAULT_CONTAINER = "ck_missive_backend"


def _env() -> dict:
    """Git Bash 的路徑改寫是這裡最常見的坑，統一關掉。"""
    e = dict(os.environ)
    e["MSYS_NO_PATHCONV"] = "1"
    return e


def container_running(name: str = DEFAULT_CONTAINER) -> bool:
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=30, env=_env(),
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def exec_in(
    args: Sequence[str],
    container: str = DEFAULT_CONTAINER,
    timeout: int = 120,
    stdin: Optional[str] = None,
) -> Optional[str]:
    """在容器裡執行；成功回 stdout，**失敗或容器不在回 None**。"""
    try:
        r = subprocess.run(
            ["docker", "exec", "-i", container, *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env=_env(), input=stdin,
        )
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def python_in(code: str, container: str = DEFAULT_CONTAINER,
              timeout: int = 120) -> Optional[str]:
    """在容器裡跑一段 Python（自動補 `sys.path` 與 UTF-8 輸出）。"""
    prelude = (
        "import sys\n"
        "sys.path.insert(0, '/app')\n"
        "try:\n"
        "    sys.stdout.reconfigure(encoding='utf-8')\n"
        "except Exception:\n"
        "    pass\n"
    )
    return exec_in(["python", "-c", prelude + code], container, timeout)
