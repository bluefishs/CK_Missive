# -*- coding: utf-8 -*-
r"""回歸鎖：向量搜尋的 SQL 不得使用 `:param::type` 轉型語法。

## 鎖的是什麼

2026-08-31：`POST /api/knowledge-base/search` 對**每一個查詢都回 500**。

根因是 SQLAlchemy 的 bind param 正則：

    BIND_PARAMS = re.compile(r"(?<![:\w\$]):([\w\$]+)(?![:\w\$])")

結尾那個否定前瞻的意思是「參數名後面不可以再接冒號」，而 PostgreSQL 的
轉型語法正是 `::`。於是 `:embedding::vector` 裡的 `:embedding`
**完全不被視為參數**，原樣送進資料庫：

    syntax error at or near ":"
    [SQL: ... 1 - (embedding <=> :embedding::vector) ... LIMIT $1]
    [parameters: (3,)]      ← 只有 limit 被綁定

⚠️ **它不是「偶爾失敗」，是從來沒有成功過。**而端點的
`if vector_results:` 兜底寫在這一層之外，例外直接往上拋 ——
**連退回文字搜尋都沒有發生**。

同型前例就在本 repo：`auth/login_history.py:178` 的註解寫著
「asyncpg 不支援 :param::type」並改用動態 WHERE 繞開。
有人踩過、繞過了，而向量搜尋這裡沒有跟上。

## 為什麼用靜態斷言而不是打資料庫

這一條**不需要 DB 也能鎖住**：問題出在 SQL 字串本身，
而「跑得到 DB 的測試」在 CI 與本機的可用性不一致。
拿 SQLAlchemy 自己的正則來驗，判準與真實行為同源 —— 這是本 repo
今天反覆得到的教訓：**判準要和被檢查的程式碼用同一個算法。**
"""
import ast
import inspect
import re

from app.services.ai.misc import kb_embedding

# SQLAlchemy 的 BIND_PARAMS（原樣抄自 sqlalchemy/sql/elements.py）
_BIND_PARAMS = re.compile(r"(?<![:\w\$]):([\w\$]+)(?![:\w\$])", re.UNICODE)
# `:name::type` —— 冒號參數緊接 PostgreSQL 轉型
_COLON_CAST = re.compile(r":[A-Za-z_]\w*::\w+")


def _sql_literals() -> list:
    """只取真正傳給 `text(...)` 的字串字面量。

    ⚠️ **不能用 `inspect.getsource()` 掃整份模組。**首版就是那樣寫的，
    結果測試當場失敗 —— 因為 `kb_embedding.py` 的註解裡寫著
    `:embedding::vector` 這個**反例**，而判準把它當成真的違規。

    這是本 repo 今天第三次踩到同一件事（`knowledge_base_consistency_check`
    掃到自己的 docstring、掃描視窗吃到相鄰內容）：
    **判準的掃描範圍不得包含描述該判準的文字。**
    AST 只看真正的字串字面量，註解與 docstring 都不在其中。
    """
    tree = ast.parse(inspect.getsource(kb_embedding))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = getattr(fn, "id", None) or getattr(fn, "attr", None)
        if name != "text":
            continue
        for a in node.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append(a.value)
    return out


def _vector_sql() -> str:
    """取那一段查 kb_chunks 的向量 SQL。找不到就讓測試失敗（不靜默略過）。"""
    for sql in _sql_literals():
        if "kb_chunks" in sql and "embedding" in sql and "ORDER BY" in sql.upper():
            return sql
    raise AssertionError(
        "在 kb_embedding 的 text(...) 字面量裡找不到向量查詢 SQL —— "
        "可能被改寫成別的形式，請一併更新本測試。"
        f"目前找到 {len(_sql_literals())} 段 SQL。"
    )


def test_no_colon_cast_after_bind_param():
    """`:param::type` 會讓該參數綁不到 —— 一律改用 CAST(x AS type)。"""
    bad = [s for s in _sql_literals() if _COLON_CAST.search(s)]
    assert not bad, (
        f"{len(bad)} 段 SQL 使用了 `:param::type`。"
        "SQLAlchemy 的 BIND_PARAMS 正則有否定前瞻，參數名後面接冒號時"
        "**不會被視為參數**，SQL 會語法錯誤。改用 CAST(:param AS type)。"
    )


def test_vector_search_sql_binds_embedding():
    """向量搜尋的 SQL 裡，`embedding` 與 `limit` 必須真的是 bind param。"""
    sql = _vector_sql()
    names = set(_BIND_PARAMS.findall(sql))
    assert "embedding" in names, (
        "`embedding` 沒有被 SQLAlchemy 的 BIND_PARAMS 正則辨識為參數。"
        f"目前辨識到：{sorted(names)}。最可能是寫成了 `:embedding::vector`。"
    )
    assert "limit" in names, f"`limit` 也應該是 bind param，目前：{sorted(names)}"


def test_cast_form_is_used():
    """正向：確認用的是 CAST 形式（避免有人改成別的寫法而前兩項剛好都過）。"""
    assert "CAST(:embedding AS vector)" in _vector_sql(), (
        "向量搜尋應使用 `CAST(:embedding AS vector)`；"
        "若改寫成別的等價形式，請一併更新本測試的斷言。"
    )
