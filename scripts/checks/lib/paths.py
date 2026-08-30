#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""路徑的單一水源 —— 檢核腳本一律從這裡取，不要自己算。

## 為什麼有這一支

2026-08-30 實測：`scripts/checks/*.py` 共 182 支，其中 **110 支自己寫
`Path(__file__).resolve().parents[N]`**（122 處），而共用層的採用率只有 3.3%。

同一天這件事咬了兩次：

1. 我在 `cron_silent_dormant_check.py` 裡**重寫了一份**事件檔路徑推導，
   寫成 `parents[2]/"logs"` —— 而 compose 掛的是 `./backend/logs:/app/logs`。
   那個目錄**真的存在**（另一個同名檔）⇒ 不報錯、不回 None、
   **安靜地讀了錯的檔案回 0**。而**同一個檔案上方 100 行就有 `_cron_events_path()`**，
   它的註解正寫著那條路是錯的。
2. `.claude/hooks/route-sync-check.ps1` 用了**三層** `Split-Path`（應為兩層）
   ⇒ 算到 monorepo 根、找不到路由檔、每次 exit 1。從沒有人在跑它，所以沒人知道。

⇒ **路徑算錯是靜默的**：Windows 上 `Path("/app/logs")` 會解析成 `D:\app\`，
而那個目錄可能真的存在。**沒有例外、沒有訊息，只有錯的答案。**

## 用法

    from lib.paths import repo_root, docs_dir, cron_events_path

    ROOT = repo_root()

不要寫 `Path(__file__).resolve().parents[2]`。
新腳本這樣寫會被 `lib_adoption_audit`（weekly 93）擋下來。
"""
from __future__ import annotations

import os
from pathlib import Path

# 本檔位於 <repo>/scripts/checks/lib/paths.py ⇒ 往上三層才是 repo 根。
# ⚠️ 這個 3 是**整個 repo 唯一一處**該出現的深度常數。
_REPO_ROOT = Path(__file__).resolve().parents[3]


def repo_root() -> Path:
    """專案根（`CK_Missive/`）。"""
    return _REPO_ROOT


def monorepo_root() -> Path:
    """monorepo 根（`D:/CKProject/`）—— 只有跨 repo 稽核需要。"""
    return _REPO_ROOT.parent


def docs_dir() -> Path:
    return _REPO_ROOT / "docs"


def backend_dir() -> Path:
    return _REPO_ROOT / "backend"


def frontend_dir() -> Path:
    return _REPO_ROOT / "frontend"


def scripts_dir() -> Path:
    return _REPO_ROOT / "scripts"


def wiki_memory_dir() -> Path:
    return _REPO_ROOT / "wiki" / "memory"


def logs_dir() -> Path:
    """後端日誌目錄。

    ⚠️ 是 `backend/logs`，**不是 repo 根的 `logs/`** ——
    compose 掛的是 `./backend/logs:/app/logs`。
    repo 根確實也有一個 `logs/`，裡面是 pytest 在 host 上跑時寫的東西
    （504 筆、當天還在更新、連 detail 格式都是真的），
    **它已經騙過兩個讀者**。容器內則是 `/app/logs`。
    """
    container = Path("/app/logs")
    if os.name != "nt" and container.is_dir():
        return container
    return _REPO_ROOT / "backend" / "logs"


def cron_events_path() -> Path | None:
    """排程事件流 `cron_events.jsonl`；找不到回 None。

    回 None 而不是回一個不存在的路徑 —— 呼叫端才分得出
    「沒有事件」與「讀不到檔案」。
    """
    p = logs_dir() / "cron_events.jsonl"
    return p if p.is_file() else None
