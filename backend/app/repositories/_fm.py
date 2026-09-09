# -*- coding: utf-8 -*-
"""給 repository 用的經費指標中心服務**延遲代理**。

`app.services.stats.finance` 是唯一實作（SQL 片段＋SQLAlchemy Core 片段）。但 repository 模組層直接
`from app.services.stats import finance` 會在「以 repository 為入口匯入」時循環：
`app.services/__init__` → contract 服務 → `app.repositories`（初始化中）→ 這個 repository → `app.services`…
（2026-09-09 晚實測：app 啟動時因匯入順序不炸，腳本與測試直接匯入 repository 就炸）。

這裡只在**第一次取用屬性時**才匯入，實作仍只有那一份。用法：`from app.repositories._fm import fm as _fm`。
"""
from __future__ import annotations


class _LazyFinance:
    def __getattr__(self, name: str):
        from app.services.stats import finance  # 延遲到真正取用時
        return getattr(finance, name)


fm = _LazyFinance()
