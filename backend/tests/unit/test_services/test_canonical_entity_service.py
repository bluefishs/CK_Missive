"""
canonical_entity_service 正規化實體服務單元測試

測試範圍：
- _preprocess_entity_name 前處理
- _is_false_fuzzy_match 虛假匹配防護
- CanonicalEntityService.resolve_entity 4 階段策略
- CanonicalEntityService.merge_entities 合併邏輯
- CanonicalEntityService.add_mention 提及記錄
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.canonical_entity_service import (
    _preprocess_entity_name,
    CanonicalEntityService,
)
from app.services.ai.canonical_entity_matcher import CanonicalEntityMatcher


class TestPreprocessEntityName:
    """前處理實體名稱"""

    def test_normal_name(self):
        assert _preprocess_entity_name('桃園市政府工務局') == '桃園市政府工務局'

    def test_nfkc_normalization(self):
        # 全形空格、特殊字元正規化
        result = _preprocess_entity_name('桃園市政府　工務局')  # 全形空格
        assert '　' not in result  # NFKC 不一定移除全形空格，但應正規化

    def test_empty_string(self):
        assert _preprocess_entity_name('') is None

    def test_whitespace_only(self):
        assert _preprocess_entity_name('   ') is None

    def test_pronoun_blacklisted(self):
        assert _preprocess_entity_name('貴公司') is None
        assert _preprocess_entity_name('本局') is None

    def test_tax_id_prefix_stripped(self):
        result = _preprocess_entity_name('EB50819619 乾坤測繪科技有限公司')
        assert result == '乾坤測繪科技有限公司'

    def test_8_digit_tax_id_stripped(self):
        result = _preprocess_entity_name('50819619 乾坤測繪科技有限公司')
        assert result == '乾坤測繪科技有限公司'


class TestIsFalseFuzzyMatch:
    """虛假匹配防護"""

    def test_short_names_pass(self):
        # 短名稱不檢查
        assert CanonicalEntityMatcher.is_false_fuzzy_match('工務局', '地政局') is False

    def test_same_year_different_region(self):
        # 年度前綴相同但內容不同
        name = '115年度苗栗縣公共工程品質抽驗'
        candidate = '115年度桃園市公共工程品質抽驗'
        result = CanonicalEntityMatcher.is_false_fuzzy_match(name, candidate)
        assert result is True

    def test_same_content_passes(self):
        name = '115年度桃園市公共工程品質抽驗計畫'
        candidate = '115年度桃園市公共工程品質抽驗計畫書'
        result = CanonicalEntityMatcher.is_false_fuzzy_match(name, candidate)
        assert result is False

    def test_completely_different_long_names(self):
        name = '桃園市龍潭區某某某某某某某某某某某某某某某道路改善工程'
        candidate = '南投縣仁愛鄉某某某某某某某某某某某某某某某產業道路'
        result = CanonicalEntityMatcher.is_false_fuzzy_match(name, candidate)
        assert result is True


class TestResolveEntity:
    """resolve_entity 4 階段策略"""

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.scalar = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        return CanonicalEntityService(mock_db)

    @pytest.mark.asyncio
    async def test_reject_empty_name(self, service):
        with pytest.raises(ValueError, match="不可為空"):
            await service.resolve_entity('', 'org')

    @pytest.mark.asyncio
    async def test_reject_pronoun(self, service):
        with pytest.raises(ValueError, match="不可為空或為代名詞"):
            await service.resolve_entity('貴公司', 'org')

    @pytest.mark.asyncio
    async def test_exact_match_found(self, service, mock_db):
        """Stage 1: 精確匹配命中"""
        mock_entity = MagicMock()
        mock_entity.canonical_name = '桃園市政府工務局'
        with patch.object(service, '_exact_match', new_callable=AsyncMock, return_value=mock_entity):
            result = await service.resolve_entity('桃園市政府工務局', 'org')
            assert result.canonical_name == '桃園市政府工務局'

    @pytest.mark.asyncio
    async def test_fuzzy_match_found(self, service, mock_db):
        """Stage 2: 模糊匹配命中"""
        mock_entity = MagicMock()
        mock_entity.canonical_name = '桃園市政府工務局'
        mock_entity.id = 1
        mock_entity.alias_count = 1

        with patch.object(service, '_exact_match', new_callable=AsyncMock, return_value=None), \
             patch.object(service._matcher, 'fuzzy_match', new_callable=AsyncMock, return_value=mock_entity), \
             patch.object(service, '_add_alias', new_callable=AsyncMock):
            result = await service.resolve_entity('桃園市工務局', 'org')
            assert result.canonical_name == '桃園市政府工務局'

    @pytest.mark.asyncio
    async def test_create_new_entity(self, service, mock_db):
        """Stage 3: 新建實體"""
        mock_entity = MagicMock()
        mock_entity.canonical_name = '新機關名稱'

        with patch.object(service, '_exact_match', new_callable=AsyncMock, return_value=None), \
             patch.object(service._matcher, 'fuzzy_match', new_callable=AsyncMock, return_value=None), \
             patch.object(service, '_create_entity', new_callable=AsyncMock, return_value=mock_entity), \
             patch.object(service, '_add_alias', new_callable=AsyncMock):
            result = await service.resolve_entity('新機關名稱', 'org')
            assert result.canonical_name == '新機關名稱'


class TestAddMention:
    """add_mention 提及記錄"""

    @pytest.mark.asyncio
    async def test_mention_increments_count(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        service = CanonicalEntityService(mock_db)

        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.mention_count = 5

        mention = await service.add_mention(
            document_id=100,
            canonical_entity=mock_entity,
            mention_text="工務局",
            confidence=0.9,
            context="某段內容提到工務局",
        )
        assert mock_entity.mention_count == 6
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_mention_truncates_context(self):
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        service = CanonicalEntityService(mock_db)

        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.mention_count = 0

        long_context = "A" * 1000
        await service.add_mention(
            document_id=100,
            canonical_entity=mock_entity,
            mention_text="工務局",
            context=long_context,
        )
        # 驗證 add 被呼叫（context 應被截斷到 500）
        call_args = mock_db.add.call_args[0][0]
        assert len(call_args.context) == 500

    @pytest.mark.asyncio
    async def test_mention_none_count(self):
        """mention_count 為 None 時應初始化"""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        service = CanonicalEntityService(mock_db)

        mock_entity = MagicMock()
        mock_entity.id = 1
        mock_entity.mention_count = None

        await service.add_mention(
            document_id=100,
            canonical_entity=mock_entity,
            mention_text="工務局",
        )
        assert mock_entity.mention_count == 1
