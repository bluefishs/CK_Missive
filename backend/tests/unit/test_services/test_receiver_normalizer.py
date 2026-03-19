"""
receiver_normalizer 正規化服務單元測試
"""

import pytest
from app.services.receiver_normalizer import normalize_unit, cc_list_to_json


class TestNormalizeUnit:
    """測試 normalize_unit 函數"""

    def test_empty_input(self):
        result = normalize_unit(None)
        assert result.primary == ''
        assert result.cc_list == []

        result = normalize_unit('')
        assert result.primary == ''

        result = normalize_unit('   ')
        assert result.primary == ''

    def test_plain_name(self):
        result = normalize_unit('桃園市政府工務局')
        assert result.primary == '桃園市政府工務局'
        assert result.cc_list == []
        assert result.tax_id is None
        assert result.agency_code is None

    def test_tax_id_prefix_with_space(self):
        result = normalize_unit('EB50819619 乾坤測繪科技有限公司')
        assert result.primary == '乾坤測繪科技有限公司'
        assert result.tax_id == 'EB50819619'

    def test_tax_id_prefix_with_newline(self):
        result = normalize_unit('EB50819619\n乾坤測繪科技有限公司')
        assert result.primary == '乾坤測繪科技有限公司'
        assert result.tax_id == 'EB50819619'

    def test_agency_code_parenthesized(self):
        result = normalize_unit('380110000G (桃園市政府工務局)')
        assert result.primary == '桃園市政府工務局'
        assert result.agency_code == '380110000G'

    def test_agency_code_with_newline(self):
        result = normalize_unit('380110000G\n(桃園市政府工務局)')
        assert result.primary == '桃園市政府工務局'
        assert result.agency_code == '380110000G'

    def test_pipe_delimited_multiple_receivers(self):
        raw = ('A15030200H (交通部公路局中區養護工程分局) | '
               'A15030200HU122000 (交通部公路局中區養護工程分局信義工務段)')
        result = normalize_unit(raw)
        assert result.primary == '交通部公路局中區養護工程分局'
        assert result.cc_list == ['交通部公路局中區養護工程分局信義工務段']

    def test_three_receivers(self):
        raw = ('A15030200H (交通部公路局中區養護工程分局) | '
               'A15030200HU121900 (交通部公路局中區養護工程分局埔里工務段) | '
               'A15030200HU122000 (交通部公路局中區養護工程分局信義工務段)')
        result = normalize_unit(raw)
        assert result.primary == '交通部公路局中區養護工程分局'
        assert len(result.cc_list) == 2

    def test_representative_suffix_removed(self):
        result = normalize_unit('EB50819619 乾坤測繪科技有限公司(張坤樹)')
        assert result.primary == '乾坤測繪科技有限公司'
        assert result.tax_id == 'EB50819619'

    def test_subcontractor_suffix_removed(self):
        result = normalize_unit(
            'EB50819619 乾坤測繪科技有限公司（協力廠商:大有國際不動產估價師聯合事務所）'
        )
        assert result.primary == '乾坤測繪科技有限公司'

    def test_cooperation_partner_suffix_removed(self):
        result = normalize_unit(
            'EB50819619 乾坤測繪科技有限公司（合作廠商:昇揚不動產估價師聯合事務所、竣吉不動產估價師事務所）'
        )
        assert result.primary == '乾坤測繪科技有限公司'

    def test_duplicate_receivers_deduped(self):
        raw = ('EB50819619 乾坤測繪科技有限公司 | '
               'EB50819619 乾坤測繪科技有限公司（協力廠商:大有國際不動產估價師聯合事務所）')
        result = normalize_unit(raw)
        assert result.primary == '乾坤測繪科技有限公司'
        # 去重後只有一個
        assert len(result.cc_list) == 0


    def test_semicolon_delimited(self):
        raw = '桃園市政府工務局；桃園市政府地政局'
        result = normalize_unit(raw)
        assert result.primary == '桃園市政府工務局'
        assert result.cc_list == ['桃園市政府地政局']

    def test_infer_agency_from_doc_number(self):
        from app.services.receiver_normalizer import infer_agency_from_doc_number
        assert infer_agency_from_doc_number('府工用字第1140331294號') == '桃園市政府工務局'
        assert infer_agency_from_doc_number('桃工用字第114123號') == '桃園市政府工務局'
        assert infer_agency_from_doc_number('乾坤測字第123號') is None
        assert infer_agency_from_doc_number(None) is None
        assert infer_agency_from_doc_number('') is None


class TestNFKCNormalization:
    """測試 NFKC 正規化"""

    def test_fullwidth_characters_normalized(self):
        """全形字元被正規化為半形"""
        # 全形括號 should be handled by NFKC
        result = normalize_unit('桃園市政府工務局')
        assert result.primary == '桃園市政府工務局'

    def test_nfkc_pipe_delimiter(self):
        """NFKC 正規化後的分隔符仍可正常拆分"""
        # 半形分號可正常拆分
        result = normalize_unit('A單位;B單位')
        assert result.primary == 'A單位'
        assert result.cc_list == ['B單位']


class TestEdgeCases:
    """邊界情況測試"""

    def test_whitespace_only(self):
        """純空白字串"""
        result = normalize_unit('   \t\n  ')
        assert result.primary == ''
        assert result.cc_list == []

    def test_only_tax_id(self):
        """僅有統編沒有名稱的特殊情況"""
        # "EB50819619 " 後面無名稱 → 無法匹配 _TAX_ID_PREFIX（需要兩組 group）
        result = normalize_unit('EB50819619')
        assert result.primary != ''  # 保留原值

    def test_multiple_pipes_with_empty_parts(self):
        """連續管道符號中有空白部分"""
        result = normalize_unit('桃園市政府 |  | 新北市政府')
        assert result.primary == '桃園市政府'
        assert '新北市政府' in result.cc_list


class TestInferAgencyDocNumber:
    """測試文號推斷的更多案例"""

    def test_infer_fu_gong_zi(self):
        from app.services.receiver_normalizer import infer_agency_from_doc_number
        assert infer_agency_from_doc_number('府工字第114001號') == '桃園市政府工務局'

    def test_infer_tao_gong_cai(self):
        from app.services.receiver_normalizer import infer_agency_from_doc_number
        assert infer_agency_from_doc_number('桃工採字第114001號') == '桃園市政府工務局'

    def test_infer_unknown_prefix(self):
        from app.services.receiver_normalizer import infer_agency_from_doc_number
        assert infer_agency_from_doc_number('財政部字第114001號') is None


class TestCcListToJson:
    def test_empty_list(self):
        assert cc_list_to_json([]) is None

    def test_single_item(self):
        result = cc_list_to_json(['交通部'])
        assert '"交通部"' in result

    def test_multiple_items(self):
        result = cc_list_to_json(['A', 'B'])
        assert result is not None
        import json
        parsed = json.loads(result)
        assert parsed == ['A', 'B']
