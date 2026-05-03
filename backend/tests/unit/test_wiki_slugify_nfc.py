# -*- coding: utf-8 -*-
"""Wiki slugify NFC normalization tests (v6.7 E3)

驗證 _slugify 把 CJK Compatibility Ideograph（如 U+F9E9 「里」）正規化為
NFC 標準（U+91CC「里」），避免 wiki_compiler 寫出兩個外觀相同 byte 不同的檔。
"""
from __future__ import annotations


def test_slugify_normalizes_cjk_compatibility_ideograph_to_nfc():
    """U+F9E9（compatibility 里）→ U+91CC（NFC 里）。"""
    from app.services.wiki.service import _slugify

    compat = "南投縣埔" + chr(0xF9E9) + "地政事務所"
    nfc = "南投縣埔" + chr(0x91CC) + "地政事務所"

    # 確認來源確實 byte 不同
    assert compat.encode("utf-8") != nfc.encode("utf-8")

    # slugify 後應 byte 完全相同（兩端都產出 NFC 形式）
    assert _slugify(compat).encode("utf-8") == _slugify(nfc).encode("utf-8")
    assert _slugify(compat) == nfc.replace(" ", "_")  # 無空白，但驗證 NFC 形式


def test_slugify_idempotent_on_already_nfc_text():
    """已是 NFC 標準的文字，slugify 不該改變字元組成（除空白/特殊符號處理外）。"""
    from app.services.wiki.service import _slugify

    text = "桃園市政府"
    result = _slugify(text)
    assert result == "桃園市政府"


def test_slugify_unsafe_chars_replaced_after_nfc():
    """NFC 化後仍正確處理路徑不安全字元。"""
    from app.services.wiki.service import _slugify

    text = "桃園/市政府:測試"
    result = _slugify(text)
    assert "/" not in result
    assert ":" not in result
    assert "桃園" in result


def test_slugify_truncates_to_80():
    """長標題截 80 字。"""
    from app.services.wiki.service import _slugify
    long_text = "里" * 100
    result = _slugify(long_text)
    assert len(result) <= 80
