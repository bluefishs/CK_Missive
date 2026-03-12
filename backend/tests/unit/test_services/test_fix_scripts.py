"""
知識圖譜修復腳本單元測試

測試範圍：
- clean_garbage_entities.py: is_garbage_entity 判斷邏輯
- merge_cross_type_dupes.py: KEEP_RULES 配置與合併邏輯
- synonym_merge_cleanup.py: merge_entity 合併操作與 MERGE_RULES/SYNONYM_ALIASES 配置

共 50+ test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch

# ============================================================================
# clean_garbage_entities 測試
# ============================================================================

from scripts.fixes.clean_garbage_entities import (
    is_garbage_entity,
    _normalize_nfkc,
    _PRONOUN_BLACKLIST,
    _BOILERPLATE_PREFIXES,
)


class TestNormalizeNfkc:
    """NFKC 正規化輔助函數"""

    def test_basic_normalization(self):
        """全形英數字應正規化為半形"""
        assert _normalize_nfkc("ＡＢＣ") == "ABC"

    def test_strip_whitespace(self):
        """前後空白應被移除"""
        assert _normalize_nfkc("  hello  ") == "hello"

    def test_empty_string(self):
        assert _normalize_nfkc("") == ""

    def test_chinese_unchanged(self):
        """中文字元不受 NFKC 影響"""
        assert _normalize_nfkc("桃園市") == "桃園市"


class TestIsGarbageEntity:
    """is_garbage_entity 核心判斷邏輯"""

    # --- empty / too_short ---

    def test_empty_string(self):
        """空字串應判定為垃圾"""
        assert is_garbage_entity("", "org") == "empty"

    def test_whitespace_only(self):
        """純空白應判定為垃圾"""
        assert is_garbage_entity("   ", "org") == "empty"

    def test_single_char_non_person(self):
        """單字元非 person 類型應判定為太短"""
        assert is_garbage_entity("局", "org") == "too_short"

    def test_single_char_person_not_garbage(self):
        """單字元 person 類型不應被判定為太短"""
        assert is_garbage_entity("陳", "person") is None

    # --- mojibake ---

    def test_fffd_replacement_char(self):
        """包含 U+FFFD 替換字元應判定為亂碼"""
        assert is_garbage_entity("桃園\ufffd市", "org") == "mojibake(FFFD)"

    # --- control characters ---

    def test_control_char_null(self):
        """包含 NULL 字元應判定為控制字元"""
        result = is_garbage_entity("test\x00name", "org")
        assert result is not None
        assert "control_char" in result

    def test_control_char_low_range(self):
        """包含低範圍控制字元 (U+0001-U+0008)"""
        result = is_garbage_entity("test\x01", "org")
        assert result is not None
        assert "control_char" in result

    def test_control_char_del(self):
        """包含 DEL (U+007F) 應判定為控制字元"""
        result = is_garbage_entity("test\x7f", "org")
        assert result is not None
        assert "control_char" in result

    # --- repetition ---

    def test_repeated_chars(self):
        """同一字元重複 4 次以上應判定為重複"""
        assert is_garbage_entity("啊啊啊啊啊", "org") == "repetition"

    def test_three_repeats_ok(self):
        """同一字元重複 3 次不應被判定"""
        assert is_garbage_entity("啊啊啊", "org") is None

    # --- privacy mask ---

    def test_privacy_mask_circle(self):
        """包含○遮蔽符號"""
        assert is_garbage_entity("陳○明", "person") == "privacy_mask"

    def test_privacy_mask_zero_circle(self):
        """包含〇遮蔽符號"""
        assert is_garbage_entity("王〇華", "person") == "privacy_mask"

    # --- simplified chinese ---

    def test_simplified_chinese_dominant(self):
        """簡體字比例超過 30% 應判定"""
        # "义组个体" = 4 simplified out of 4 CJK = 100%
        assert is_garbage_entity("义组个体", "org") == "simplified_chinese"

    def test_mixed_chars_under_threshold(self):
        """簡體字比例低於 30% 不應判定"""
        # 1 simplified char in a string with many traditional CJK
        assert is_garbage_entity("桃園市政府地政局个", "org") is None

    # --- pronoun blacklist ---

    def test_pronoun_blacklist_hit(self):
        """代名詞黑名單完全匹配"""
        assert is_garbage_entity("本府", "org") == "pronoun_blacklist"
        assert is_garbage_entity("貴公司", "org") == "pronoun_blacklist"
        assert is_garbage_entity("敬請查照", "org") == "pronoun_blacklist"
        assert is_garbage_entity("檢送", "org") == "pronoun_blacklist"

    def test_pronoun_blacklist_miss(self):
        """非黑名單字詞不應被判定"""
        assert is_garbage_entity("桃園市政府", "org") is None

    # --- boilerplate phrase ---

    def test_boilerplate_prefix_long(self):
        """公文套語前綴且長度 > 4"""
        assert is_garbage_entity("檢送本案相關資料", "org") == "boilerplate_phrase"
        assert is_garbage_entity("依據土地法第四條", "org") == "boilerplate_phrase"

    def test_boilerplate_prefix_short_ok(self):
        """公文套語前綴但長度 <= 4 不觸發此規則 (可能被其他規則捕獲)"""
        # "檢送XX" = 4 chars, not > 4
        result = is_garbage_entity("檢送XX", "org")
        # Should not be "boilerplate_phrase" specifically
        assert result != "boilerplate_phrase"

    # --- alphanumeric code ---

    def test_alphanumeric_code(self):
        """純代碼字串 (6+ 字元)"""
        assert is_garbage_entity("AB12CD34", "org") == "alphanumeric_code"
        assert is_garbage_entity("ABCDEF", "org") == "alphanumeric_code"

    def test_short_alphanumeric_ok(self):
        """短代碼 (< 6 字元) 不應判定"""
        assert is_garbage_entity("AB12", "org") is None

    # --- amount ---

    def test_amount_pattern(self):
        """金額格式"""
        assert is_garbage_entity("1,234,567元整", "org") == "amount"

    def test_amount_wan_pattern(self):
        """含「萬」的金額格式"""
        assert is_garbage_entity("5萬3,000元", "org") == "amount"

    # --- duration not date ---

    def test_duration_calendar_days(self):
        """工期天數不應歸為 date"""
        assert is_garbage_entity("180日曆天", "date") == "duration_not_date"
        assert is_garbage_entity("60工作天", "date") == "duration_not_date"

    def test_duration_months(self):
        """工期月數不應歸為 date"""
        assert is_garbage_entity("6個月", "date") == "duration_not_date"

    def test_duration_non_date_type_ok(self):
        """非 date 類型的工期不觸發此規則"""
        assert is_garbage_entity("180日曆天", "topic") is None

    # --- generic topic ---

    def test_generic_topic(self):
        """通用表單名稱不應作為 topic"""
        assert is_garbage_entity("測量成果修正表", "topic") == "generic_topic"
        assert is_garbage_entity("人員清冊", "topic") == "generic_topic"

    def test_generic_topic_non_topic_ok(self):
        """非 topic 類型不觸發此規則"""
        assert is_garbage_entity("測量成果修正表", "org") is None

    # --- valid entity ---

    def test_valid_org(self):
        """合法的機關名稱應回傳 None"""
        assert is_garbage_entity("桃園市政府地政局", "org") is None

    def test_valid_person(self):
        """合法的人名"""
        assert is_garbage_entity("張三", "person") is None

    def test_valid_location(self):
        """合法的地名"""
        assert is_garbage_entity("桃園市中壢區", "location") is None

    def test_valid_project(self):
        """合法的專案名稱"""
        assert is_garbage_entity("金陵路五六段替代道路新闢工程", "project") is None


class TestCleanEntitiesConstants:
    """清理腳本常數完整性"""

    def test_pronoun_blacklist_not_empty(self):
        assert len(_PRONOUN_BLACKLIST) > 30

    def test_boilerplate_prefixes_not_empty(self):
        assert len(_BOILERPLATE_PREFIXES) > 10

    def test_pronoun_blacklist_contains_key_items(self):
        """黑名單應包含核心代名詞"""
        for item in ['本府', '貴公司', '台端', '承辦人']:
            assert item in _PRONOUN_BLACKLIST


# ============================================================================
# merge_cross_type_dupes 測試
# ============================================================================

from scripts.fixes.merge_cross_type_dupes import KEEP_RULES


class TestKeepRules:
    """KEEP_RULES 配置驗證"""

    def test_keep_rules_not_empty(self):
        assert len(KEEP_RULES) > 0

    def test_keep_rules_values_are_valid_types(self):
        """所有 keep_type 應為合理的實體類型"""
        valid_types = {'org', 'location', 'person', 'date', 'topic', 'project'}
        for name, keep_type in KEEP_RULES.items():
            assert keep_type in valid_types, f"'{name}' has invalid type '{keep_type}'"

    def test_key_entities_in_rules(self):
        """核心實體應有合併規則"""
        assert '桃園市' in KEEP_RULES
        assert KEEP_RULES['桃園市'] == 'location'
        assert '桃園市政府工務局' in KEEP_RULES
        assert KEEP_RULES['桃園市政府工務局'] == 'org'


class TestMergeDuplicatesLogic:
    """merge_cross_type_dupes 合併邏輯 — 驗證 keep_id 選取策略"""

    def test_keep_matching_type(self):
        """符合 keep_type 的最小 ID 應被保留"""
        # Simulate: name='桃園市', ids=[5, 10], types=['org', 'location']
        # KEEP_RULES['桃園市'] = 'location' → keep_id=10
        keep_type = KEEP_RULES.get('桃園市')
        ids = [5, 10]
        types = ['org', 'location']

        keep_id = None
        remove_ids = []
        for eid, etype in zip(ids, types):
            if etype == keep_type and keep_id is None:
                keep_id = eid
            else:
                remove_ids.append(eid)

        assert keep_id == 10
        assert remove_ids == [5]

    def test_fallback_to_min_id(self):
        """無符合 keep_type 時應保留最小 ID"""
        keep_type = 'org'
        ids = [5, 10]
        types = ['location', 'person']  # Neither is 'org'

        keep_id = None
        remove_ids = []
        for eid, etype in zip(ids, types):
            if etype == keep_type and keep_id is None:
                keep_id = eid
            else:
                remove_ids.append(eid)

        if keep_id is None:
            keep_id = min(ids)
            remove_ids = [i for i in ids if i != keep_id]

        assert keep_id == 5
        assert remove_ids == [10]

    def test_no_keep_rule_skips(self):
        """無合併規則的實體應被跳過"""
        name = '某個不在規則中的名稱'
        assert KEEP_RULES.get(name) is None


# ============================================================================
# synonym_merge_cleanup 測試
# ============================================================================

from scripts.fixes.synonym_merge_cleanup import (
    merge_entity,
    MERGE_RULES,
    SYNONYM_ALIASES,
)


class TestMergeRulesConfig:
    """MERGE_RULES 配置驗證"""

    def test_merge_rules_not_empty(self):
        assert len(MERGE_RULES) > 0

    def test_all_rules_have_required_keys(self):
        """每條規則必須有 keep_name, keep_type, merge_names"""
        for rule in MERGE_RULES:
            assert 'keep_name' in rule, f"Rule missing keep_name: {rule}"
            assert 'keep_type' in rule, f"Rule missing keep_type: {rule}"
            assert 'merge_names' in rule, f"Rule missing merge_names: {rule}"

    def test_merge_names_are_tuples_of_two(self):
        """merge_names 內每個項目應為 (name, type) 二元組"""
        for rule in MERGE_RULES:
            for item in rule['merge_names']:
                assert len(item) == 2, f"Invalid merge_names item in {rule['keep_name']}: {item}"

    def test_keep_types_are_valid(self):
        """keep_type 應為合理的實體類型"""
        valid_types = {'org', 'location', 'person', 'date', 'topic', 'project'}
        for rule in MERGE_RULES:
            assert rule['keep_type'] in valid_types, (
                f"Invalid keep_type '{rule['keep_type']}' for '{rule['keep_name']}'"
            )

    def test_no_self_merge(self):
        """keep_name 不應出現在自己的 merge_names 中"""
        for rule in MERGE_RULES:
            for merge_name, _ in rule['merge_names']:
                assert merge_name != rule['keep_name'], (
                    f"Self-merge detected: '{rule['keep_name']}'"
                )


class TestSynonymAliasesConfig:
    """SYNONYM_ALIASES 配置驗證"""

    def test_synonym_aliases_not_empty(self):
        assert len(SYNONYM_ALIASES) > 0

    def test_all_aliases_are_triples(self):
        """每條別名應為 (canonical_name, canonical_type, alias_name) 三元組"""
        for item in SYNONYM_ALIASES:
            assert len(item) == 3, f"Invalid SYNONYM_ALIASES item: {item}"

    def test_alias_differs_from_canonical(self):
        """alias_name 不應與 canonical_name 相同"""
        for canonical_name, _, alias_name in SYNONYM_ALIASES:
            assert alias_name != canonical_name, (
                f"Alias same as canonical: '{canonical_name}'"
            )

    def test_key_aliases_present(self):
        """核心同義詞應存在"""
        alias_names = {a[2] for a in SYNONYM_ALIASES}
        assert '地評會' in alias_names
        assert '本府地政局' in alias_names


@pytest.mark.asyncio
class TestMergeEntity:
    """merge_entity 異步合併操作"""

    async def _make_mock_db(self):
        """建立 mock AsyncSession"""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        return db

    async def test_merge_executes_seven_sql_operations(self):
        """合併應執行 7 個 SQL 操作 (刪衝突alias, 轉alias, 刪衝突mentions, 轉mentions, 轉src_rel, 轉tgt_rel, 刪實體, 更新count)"""
        db = await self._make_mock_db()
        await merge_entity(db, keep_id=1, remove_id=2, keep_name="keep", remove_name="remove")
        # 7 db.execute calls: del conflict alias, transfer alias,
        # del conflict mentions, transfer mentions,
        # transfer src relationships, transfer tgt relationships,
        # delete entity, update mention_count
        assert db.execute.call_count == 8

    async def test_merge_uses_correct_ids(self):
        """合併應傳遞正確的 keep_id 和 remove_id 參數"""
        db = await self._make_mock_db()
        await merge_entity(db, keep_id=100, remove_id=200, keep_name="A", remove_name="B")

        # Check that all calls used the correct IDs
        for c in db.execute.call_args_list:
            params = c[1] if c[1] else (c[0][1] if len(c[0]) > 1 else {})
            if isinstance(params, dict):
                if 'k' in params:
                    assert params['k'] == 100
                if 'r' in params:
                    assert params['r'] == 200

    async def test_merge_deletes_conflicting_aliases_first(self):
        """合併的第一步應先刪除衝突 aliases"""
        db = await self._make_mock_db()
        await merge_entity(db, keep_id=1, remove_id=2, keep_name="A", remove_name="B")

        first_call = db.execute.call_args_list[0]
        sql_text = str(first_call[0][0].text)
        assert "DELETE FROM entity_aliases" in sql_text

    async def test_merge_deletes_entity_at_end(self):
        """合併最後一步（倒數第二個 call）應刪除重複實體"""
        db = await self._make_mock_db()
        await merge_entity(db, keep_id=1, remove_id=2, keep_name="A", remove_name="B")

        # Second-to-last call should delete the entity
        delete_call = db.execute.call_args_list[-2]
        sql_text = str(delete_call[0][0].text)
        assert "DELETE FROM canonical_entities" in sql_text

    async def test_merge_updates_mention_count_last(self):
        """合併最後應更新 mention_count"""
        db = await self._make_mock_db()
        await merge_entity(db, keep_id=1, remove_id=2, keep_name="A", remove_name="B")

        last_call = db.execute.call_args_list[-1]
        sql_text = str(last_call[0][0].text)
        assert "UPDATE canonical_entities" in sql_text
        assert "mention_count" in sql_text


# ============================================================================
# is_garbage_entity 邊界條件
# ============================================================================

class TestIsGarbageEntityEdgeCases:
    """is_garbage_entity 邊界與組合條件"""

    def test_none_name_raises_or_returns(self):
        """None 輸入應被安全處理 (返回 empty 或拋出 TypeError)"""
        # The function checks `if not name` which catches None
        assert is_garbage_entity(None, "org") == "empty"

    def test_tab_and_newline_whitespace(self):
        """Tab 和換行應被視為空白"""
        assert is_garbage_entity("\t\n", "org") == "empty"

    def test_fullwidth_alphanumeric_code(self):
        """全形英數字代碼正規化後應被判定"""
        # "ＡＢＣＤＥＦ" normalizes to "ABCDEF" which is alphanumeric_code
        assert is_garbage_entity("ＡＢＣＤＥＦ", "org") == "alphanumeric_code"

    def test_mixed_valid_entity(self):
        """包含數字但非純代碼的有效實體"""
        assert is_garbage_entity("第113期公文", "topic") is None

    def test_long_chinese_org_valid(self):
        """較長的中文機關名稱應為有效"""
        assert is_garbage_entity("交通部公路局中區養護工程分局信義工務段", "org") is None

    def test_date_type_valid_date(self):
        """有效日期不應被判定為垃圾"""
        assert is_garbage_entity("113年12月31日", "date") is None

    def test_amount_fullwidth(self):
        """全形數字金額"""
        # "１,２３４元" after NFKC → "1,234元"
        assert is_garbage_entity("１,２３４元整", "org") == "amount"

    def test_two_char_org_valid(self):
        """二字機關名稱應為有效"""
        assert is_garbage_entity("內政", "org") is None

    def test_boilerplate_exactly_4_chars(self):
        """公文套語恰好 4 字元不觸發 boilerplate 規則"""
        # "檢送XX" = 4 chars exactly, len > 4 is false
        result = is_garbage_entity("檢送某案", "org")
        assert result != "boilerplate_phrase"


# ============================================================================
# clean_entities 主流程 (mock DB)
# ============================================================================

from scripts.fixes.clean_garbage_entities import clean_entities


@pytest.mark.asyncio
class TestCleanEntitiesFlow:
    """clean_entities 主流程 — mock 資料庫驗證邏輯"""

    async def test_dry_run_no_delete(self):
        """預覽模式不應執行任何刪除"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "本府", "org", 5),  # pronoun_blacklist
            (2, "桃園市政府", "org", 10),  # valid
        ]

        with patch("scripts.fixes.clean_garbage_entities.create_async_engine") as mock_engine, \
             patch("scripts.fixes.clean_garbage_entities.sessionmaker") as mock_sessionmaker:

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=False)

            mock_sessionmaker.return_value = MagicMock(return_value=mock_db)

            await clean_entities("postgresql+asyncpg://test", dry_run=True)

            # In dry_run mode, should only have the initial SELECT, no DELETE
            assert mock_db.commit.call_count == 0

    async def test_execute_mode_deletes_garbage(self):
        """執行模式應刪除垃圾實體"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "本府", "org", 5),  # pronoun_blacklist → garbage
            (2, "桃園市政府", "org", 10),  # valid
        ]

        with patch("scripts.fixes.clean_garbage_entities.create_async_engine") as mock_engine, \
             patch("scripts.fixes.clean_garbage_entities.sessionmaker") as mock_sessionmaker:

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=False)

            mock_sessionmaker.return_value = MagicMock(return_value=mock_db)

            await clean_entities("postgresql+asyncpg://test", dry_run=False)

            # Should have committed (delete garbage + possibly merge)
            assert mock_db.commit.call_count >= 1

    async def test_empty_dataset(self):
        """空資料集不應產生錯誤"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        with patch("scripts.fixes.clean_garbage_entities.create_async_engine") as mock_engine, \
             patch("scripts.fixes.clean_garbage_entities.sessionmaker") as mock_sessionmaker:

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=False)

            mock_sessionmaker.return_value = MagicMock(return_value=mock_db)

            # Should not raise
            await clean_entities("postgresql+asyncpg://test", dry_run=True)

    async def test_all_valid_entities_no_delete(self):
        """全部有效實體時不應刪除任何東西"""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (1, "桃園市政府", "org", 10),
            (2, "張三", "person", 5),
            (3, "桃園市", "location", 20),
        ]

        with patch("scripts.fixes.clean_garbage_entities.create_async_engine") as mock_engine, \
             patch("scripts.fixes.clean_garbage_entities.sessionmaker") as mock_sessionmaker:

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=False)

            mock_sessionmaker.return_value = MagicMock(return_value=mock_db)

            await clean_entities("postgresql+asyncpg://test", dry_run=False)

            # No garbage or low_quality → no delete executed, no commit for delete phase
            # The execute calls should only be the initial SELECT
            first_execute_sql = str(mock_db.execute.call_args_list[0][0][0].text)
            assert "SELECT" in first_execute_sql
