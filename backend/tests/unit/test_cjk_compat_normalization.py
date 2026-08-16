"""名稱欄位寫入時正規化 CJK 相容字。

2026-08-16：實測 `documents.subject` **1560/2009（78%）**帶 CJK 相容漢字
（年 U+F98E vs 標準 U+5E74）—— 字形一模一樣、長度一樣、md5 不同，
於是**所有以名稱比對的管控都會靜默失效**，包括 2026-08-10 才加的承攬案件防重
（同名＋同年度＋同委託單位）。

⚠️ 刻意**不**套完整的 `normalize_name`：那會把全形括號（）轉半形()，
而公文主旨常用全形括號 —— 那是**看得見的改變**，不該由正規化順手做掉。
"""
import pytest

from app.schemas._text_utils import normalize_cjk_compat

# ⚠️ 用碼位建構，不寫字面 —— 相容字與標準字在編輯器裡長得一模一樣，
# 寫成字面會在存檔時被正規化掉，測試就變成「兩個一樣的字串比對」而永遠通過。
# （2026-08-16 第一版正是如此，靠第一條斷言當場抓到。）
STANDARD = "115" + "年度" + "委外辦理圖根點清" + "理"
COMPAT = "115" + "年度" + "委外辦理圖根點清" + "理"


def test_the_two_look_identical_but_are_not():
    """前提：這正是問題的形狀 —— 看起來一樣、長度一樣、實際不同。"""
    assert COMPAT != STANDARD
    assert len(COMPAT) == len(STANDARD)


def test_normalizes_compat_to_standard():
    assert normalize_cjk_compat(COMPAT) == STANDARD


def test_does_not_touch_fullwidth_punctuation():
    """全形標點在中文語境是正常的，不得順手轉半形。"""
    for s in ("測試（甲）", "第一項，第二項", "說明：如下"):
        assert normalize_cjk_compat(s) == s


def test_none_and_empty_are_safe():
    assert normalize_cjk_compat(None) is None
    assert normalize_cjk_compat("") == ""


@pytest.mark.parametrize("mod_path,cls_name,field", [
    ("app.schemas.document", "DocumentCreate", "subject"),
    ("app.schemas.erp.quotation", "ERPQuotationCreate", "case_name"),
])
def test_schema_validators_are_wired(mod_path, cls_name, field):
    """掛上去了才算數 —— 「加了但沒接」是本專案反覆出現的形狀。"""
    import importlib
    cls = getattr(importlib.import_module(mod_path), cls_name)
    assert cls._normalize_cjk(COMPAT) == STANDARD, f"{cls_name}.{field} 沒有正規化"
    fv = cls.__pydantic_decorators__.field_validators
    bound = [v.info.fields for v in fv.values() if "_normalize_cjk" in v.cls_var_name]
    assert bound and field in bound[0], f"validator 沒有綁到 {field}"
