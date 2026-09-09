# -*- coding: utf-8 -*-
"""SQLAlchemy mapper 必須在啟動期配置完（2026-09-09 owner「Google 登入 500」）。

懶配置＋容器被段錯誤拉回後的第一波併發 ⇒ registry 毒化（'_EventKey' object has no attribute 'dispatch'），
之後每個 ORM 請求 500 直到再重啟。鎖兩件事：lifespan 裡有 configure_mappers；全部模型可一次配置成功。
"""
import inspect

from sqlalchemy.orm import configure_mappers


def test_lifespan_configures_mappers():
    import main  # noqa: WPS433
    src = inspect.getsource(main.lifespan)
    assert "configure_mappers" in src
    # 要在服務開門（yield）之前
    assert src.index("configure_mappers") < src.index("yield")


def test_all_models_configure_cleanly():
    import app.extended.models  # noqa: F401
    configure_mappers()  # 任何 relationship／backref 錯都會在這裡炸，而不是在第一個請求
