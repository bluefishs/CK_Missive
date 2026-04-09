"""
實體提取服務單元測試

測試範圍：
- _build_extraction_text: 組合公文文本
- _extract_json_from_text: 多策略 JSON 解析
- _validate_entities: 實體驗證與過濾
- _validate_relations: 關係驗證
- _is_garbled_text: 亂碼偵測
- _has_corruption_signs: 損壞字元偵測
- _normalize_entity_spacing: 空白標點正規化
- _is_boilerplate_phrase: 公文套語偵測
- _parse_extraction_response: 完整解析流程
- extract_entities_for_document: 主流程 (async)

共 10 test cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.document.entity_extraction_service import (
    _build_extraction_text,
    _extract_json_from_text,
    _validate_entities,
    _validate_relations,
    _is_garbled_text,
    _has_corruption_signs,
    _normalize_entity_spacing,
    _is_boilerplate_phrase,
    _parse_extraction_response,
    extract_entities_for_document,
    VALID_ENTITY_TYPES,
)


# ============================================================================
# _build_extraction_text
# ============================================================================

class TestBuildExtractionText:
    """組合公文文本測試"""

    def test_full_document(self):
        doc = MagicMock()
        doc.subject = "道路改善工程"
        doc.doc_number = "桃工字第123號"
        doc.sender = "桃園市政府"
        doc.receiver = "乾坤測繪"
        doc.category = "收文"
        doc.doc_type = "函"
        doc.content = "本案請查照辦理"
        doc.notes = "備註資訊"
        text = _build_extraction_text(doc)
        assert "主旨：道路改善工程" in text
        assert "文號：桃工字第123號" in text
        assert "發文單位：桃園市政府" in text
        assert "受文單位：乾坤測繪" in text

    def test_empty_fields_skipped(self):
        doc = MagicMock()
        doc.subject = "測試"
        doc.doc_number = None
        doc.sender = ""
        doc.receiver = None
        doc.category = None
        doc.doc_type = None
        doc.content = None
        doc.notes = None
        text = _build_extraction_text(doc)
        assert "主旨：測試" in text
        assert "文號" not in text
        assert "發文單位" not in text


# ============================================================================
# _extract_json_from_text
# ============================================================================

class TestExtractJsonFromText:
    """多策略 JSON 解析測試"""

    def test_strategy1_direct_json(self):
        raw = '{"entities": [{"name": "桃園市政府", "type": "org"}], "relations": []}'
        result = _extract_json_from_text(raw)
        assert result is not None
        assert len(result["entities"]) == 1

    def test_strategy2_markdown_code_block(self):
        raw = 'Here is the result:\n```json\n{"entities": [{"name": "張三", "type": "person"}], "relations": []}\n```'
        result = _extract_json_from_text(raw)
        assert result is not None
        assert result["entities"][0]["name"] == "張三"

    def test_strategy3_largest_json_object(self):
        raw = 'Some text {"entities": [{"name": "台北", "type": "location"}], "relations": []} more text'
        result = _extract_json_from_text(raw)
        assert result is not None
        assert result["entities"][0]["name"] == "台北"

    def test_returns_none_for_invalid_input(self):
        result = _extract_json_from_text("This is not JSON at all")
        assert result is None


# ============================================================================
# _validate_entities
# ============================================================================

class TestValidateEntities:
    """實體驗證與過濾"""

    def test_valid_entity_passes(self):
        entities = [{"name": "桃園市政府", "type": "org", "confidence": 0.9}]
        result = _validate_entities(entities)
        assert len(result) == 1
        assert result[0]["name"] == "桃園市政府"

    def test_invalid_type_filtered(self):
        entities = [{"name": "某個東西", "type": "unknown_type", "confidence": 0.9}]
        result = _validate_entities(entities)
        assert len(result) == 0

    def test_pronoun_blacklist_filtered(self):
        entities = [{"name": "本府", "type": "org", "confidence": 0.9}]
        result = _validate_entities(entities)
        assert len(result) == 0

    def test_doc_number_filtered(self):
        entities = [{"name": "桃工用字第1140045160號", "type": "org", "confidence": 0.9}]
        result = _validate_entities(entities)
        assert len(result) == 0

    def test_person_honorific_stripped(self):
        entities = [{"name": "陳大明先生", "type": "person", "confidence": 0.9}]
        result = _validate_entities(entities)
        assert len(result) == 1
        assert result[0]["name"] == "陳大明"

    def test_low_confidence_filtered(self):
        entities = [{"name": "桃園市政府", "type": "org", "confidence": 0.1}]
        result = _validate_entities(entities)
        assert len(result) == 0


# ============================================================================
# _validate_relations
# ============================================================================

class TestValidateRelations:
    """關係驗證測試"""

    def test_valid_relation_passes(self):
        relations = [{
            "source": "桃園市政府",
            "source_type": "org",
            "target": "道路改善工程",
            "target_type": "project",
            "relation": "manages",
            "confidence": 0.9,
        }]
        result = _validate_relations(relations)
        assert len(result) == 1

    def test_empty_source_filtered(self):
        relations = [{
            "source": "",
            "target": "目標",
            "relation": "manages",
            "confidence": 0.9,
        }]
        result = _validate_relations(relations)
        assert len(result) == 0


# ============================================================================
# 亂碼偵測
# ============================================================================

class TestGarbledAndCorruption:
    """亂碼與損壞字元偵測"""

    def test_garbled_simplified_chars(self):
        # 超過 30% 簡體字
        assert _is_garbled_text("义组个体与专业严") is True

    def test_normal_traditional_chinese(self):
        assert _is_garbled_text("桃園市政府工務局") is False

    def test_privacy_mask_detected(self):
        assert _is_garbled_text("桃園區○○路段") is True

    def test_corruption_replacement_char(self):
        assert _has_corruption_signs("桃園\ufffd市") is True

    def test_corruption_repeated_chars(self):
        assert _has_corruption_signs("哈哈哈哈哈") is True

    def test_no_corruption_normal_text(self):
        assert _has_corruption_signs("桃園市政府工務局") is False


# ============================================================================
# 其他輔助函數
# ============================================================================

class TestHelperFunctions:
    """輔助函數測試"""

    def test_normalize_spacing(self):
        result = _normalize_entity_spacing("桃園市，政府。工務局")
        assert result == "桃園市政府工務局"

    def test_boilerplate_short_ignored(self):
        assert _is_boilerplate_phrase("依據") is False

    def test_boilerplate_long_detected(self):
        assert _is_boilerplate_phrase("檢送本公司相關文件") is True


# ============================================================================
# _parse_extraction_response
# ============================================================================

class TestParseExtractionResponse:
    """完整解析流程測試"""

    def test_valid_response(self):
        raw = '{"entities": [{"name": "桃園市政府", "type": "org", "confidence": 0.9}], "relations": []}'
        entities, relations = _parse_extraction_response(raw)
        assert len(entities) == 1
        assert entities[0]["name"] == "桃園市政府"

    def test_invalid_response_returns_empty(self):
        entities, relations = _parse_extraction_response("not json")
        assert entities == []
        assert relations == []


# ============================================================================
# extract_entities_for_document (async)
# ============================================================================

class TestExtractEntitiesForDocument:
    """主流程 async 測試"""

    @pytest.mark.asyncio
    async def test_document_not_found(self):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        result = await extract_entities_for_document(db, doc_id=999)
        assert result["skipped"] is True
        assert "不存在" in result.get("reason", "")

    @pytest.mark.asyncio
    async def test_empty_text_skipped(self):
        db = AsyncMock()
        doc = MagicMock()
        doc.subject = None
        doc.doc_number = None
        doc.sender = None
        doc.receiver = None
        doc.category = None
        doc.doc_type = None
        doc.content = None
        doc.notes = None

        # First call returns doc, second returns count=0
        result_doc = MagicMock()
        result_doc.scalar_one_or_none.return_value = doc
        result_count = MagicMock()
        result_count.scalar.return_value = 0
        db.execute.side_effect = [result_doc, result_count]

        result = await extract_entities_for_document(db, doc_id=1)
        assert result["skipped"] is True
        assert "無可提取文本" in result.get("reason", "")
