# -*- coding: utf-8 -*-
"""
Taoyuan 派工單服務單元測試

測試 DispatchImportService、DispatchOrderService、ExcelImportService 的核心業務邏輯。
使用 Mock 資料庫，不需要實際連線。

執行方式:
    pytest tests/unit/test_services/test_taoyuan_services.py -v
"""
import io
import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession


# =========================================================================
# Mock 工廠
# =========================================================================

def make_mock_db() -> MagicMock:
    """建立標準 Mock DB session"""
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.get = AsyncMock(return_value=None)
    return db


def make_excel_bytes(rows: list[dict], sheet_name: str = "Sheet1") -> bytes:
    """建立測試用 Excel 檔案位元組"""
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()


def make_dispatch_order(**overrides):
    """建立 Mock 派工單物件"""
    obj = MagicMock()
    defaults = {
        "id": 1,
        "dispatch_no": "114年_派工單號001",
        "project_name": "測試工程",
        "work_type": "02.土地協議市價查估作業",
        "contract_project_id": 21,
        "agency_doc_number_raw": "桃工養字第1140001234號",
        "company_doc_number_raw": None,
        "agency_doc_id": None,
        "company_doc_id": None,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# =========================================================================
# DispatchImportService 測試
# =========================================================================

class TestDispatchImportServiceColumnMapping:
    """測試欄位映射與驗證邏輯"""

    def test_column_mapping_keys(self):
        """驗證必要的欄位映射存在"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)
        # 透過 import_from_excel 的 column_mapping 檢查
        # 這些是服務內部定義的，直接測試方法行為
        expected_keys = [
            '派工單號', '機關函文號', '工程名稱/派工事項', '作業類別',
            '分案名稱/派工備註', '履約期限', '案件承辦', '查估單位',
            '乾坤函文號', '雲端資料夾', '專案資料夾', '聯絡備註',
        ]
        # 不直接存取私有 mapping，但確認服務可初始化
        assert service.db is db
        assert service.repository is not None

    @pytest.mark.asyncio
    async def test_import_missing_required_columns(self):
        """缺少必要欄位時回傳錯誤"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        # 建立缺少必要欄位的 Excel
        bad_data = [{"姓名": "張三", "電話": "0912345678"}]
        excel_bytes = make_excel_bytes(bad_data)

        result = await service.import_from_excel(excel_bytes, contract_project_id=1)

        assert result["success"] is False
        assert result["error_count"] >= 1
        assert len(result["errors"]) >= 1

    @pytest.mark.asyncio
    async def test_import_invalid_excel_format(self):
        """非 Excel 格式的檔案回傳錯誤"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        result = await service.import_from_excel(b"not an excel file", contract_project_id=1)

        assert result["success"] is False
        assert "Excel 讀取失敗" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_import_sheet_detection_with_required_columns(self):
        """智慧工作表偵測 - 找到含必要欄位的 sheet"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        # 建立有正確欄位的 Excel
        valid_data = [{
            '派工單號': '114年_派工單號001',
            '工程名稱/派工事項': '測試工程',
            '作業類別': '02.土地協議市價查估作業',
        }]
        excel_bytes = make_excel_bytes(valid_data, sheet_name="派工紀錄")

        # Mock 內部依賴
        service._resolve_roc_year = AsyncMock(return_value=114)
        service._build_doc_number_map = AsyncMock(return_value={})
        service.repository.create = AsyncMock(return_value=make_dispatch_order())

        result = await service.import_from_excel(excel_bytes, contract_project_id=1)

        assert result["success"] is True
        assert result["total"] == 1


class TestDispatchImportServiceDeadlineParsing:
    """測試履約期限解析"""

    @pytest.mark.asyncio
    async def test_deadline_datetime_conversion(self):
        """datetime 格式自動轉民國年字串"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        # 建立含 datetime 型別期限的 Excel
        test_date = datetime(2025, 6, 30)
        valid_data = [{
            '派工單號': '114年_派工單號001',
            '工程名稱/派工事項': '測試工程',
            '作業類別': '02.土地協議市價查估作業',
            '履約期限': test_date,
        }]
        excel_bytes = make_excel_bytes(valid_data)

        created_records = []

        async def mock_create(data, auto_commit=True):
            created_records.append(data)
            return make_dispatch_order(**data)

        service._resolve_roc_year = AsyncMock(return_value=114)
        service._build_doc_number_map = AsyncMock(return_value={})
        service.repository.create = AsyncMock(side_effect=mock_create)

        result = await service.import_from_excel(excel_bytes, contract_project_id=1)

        assert result["success"] is True
        assert len(created_records) == 1
        # datetime(2025,6,30) -> 114年06月30日
        assert created_records[0]["deadline"] == "114年06月30日"


class TestDispatchImportServiceDocLinking:
    """測試公文關聯邏輯"""

    @pytest.mark.asyncio
    async def test_link_documents_by_number_found(self):
        """文號匹配到公文時建立關聯"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)
        service.doc_link_repo = MagicMock()
        service.doc_link_repo.link_dispatch_to_document = AsyncMock(return_value=MagicMock())

        doc_number_map = {
            "桃工養字第1140001234號": 100,
        }

        result = await service._link_documents_by_number(
            dispatch_id=1,
            agency_raw="桃工養字第1140001234號",
            company_raw=None,
            doc_number_map=doc_number_map,
        )

        assert result["linked_count"] >= 1
        assert result["agency_doc_id"] == 100

    @pytest.mark.asyncio
    async def test_link_documents_by_number_not_found(self):
        """文號未匹配時回傳 not_found"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)
        service.doc_link_repo = MagicMock()

        result = await service._link_documents_by_number(
            dispatch_id=1,
            agency_raw="不存在的文號",
            company_raw=None,
            doc_number_map={},
        )

        assert result["linked_count"] == 0
        assert result["agency_doc_id"] is None

    @pytest.mark.asyncio
    async def test_link_documents_already_linked(self):
        """已存在的關聯不重複建立"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)
        service.doc_link_repo = MagicMock()
        # link returns None => already linked
        service.doc_link_repo.link_dispatch_to_document = AsyncMock(return_value=None)

        doc_number_map = {"桃工養字第1140001234號": 100}

        result = await service._link_documents_by_number(
            dispatch_id=1,
            agency_raw="桃工養字第1140001234號",
            company_raw=None,
            doc_number_map=doc_number_map,
        )

        assert result["linked_count"] == 0
        assert result["already_linked"] == 1


class TestDispatchImportServiceROCYear:
    """測試民國年解析"""

    @pytest.mark.asyncio
    async def test_resolve_roc_year_from_project_name(self):
        """從承攬案件名稱解析民國年"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        # Mock 查詢回傳 project 物件
        mock_project = MagicMock()
        mock_project.project_name = "115年度桃園市測繪開口契約"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        db.execute.return_value = mock_result

        year = await service._resolve_roc_year(contract_project_id=1)
        assert year == 115

    @pytest.mark.asyncio
    async def test_resolve_roc_year_range(self):
        """支援年度範圍格式（取起始年）"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        mock_project = MagicMock()
        mock_project.project_name = "112至113年度測繪契約"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        db.execute.return_value = mock_result

        year = await service._resolve_roc_year(contract_project_id=1)
        assert year == 112

    @pytest.mark.asyncio
    async def test_resolve_roc_year_fallback(self):
        """找不到年度時使用當前年份"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        year = await service._resolve_roc_year(contract_project_id=1)
        expected = datetime.now().year - 1911
        assert year == expected


class TestDispatchImportTemplateGeneration:
    """測試匯入範本生成"""

    def test_generate_template_returns_bytes(self):
        """範本生成回傳有效的 Excel bytes"""
        from app.services.taoyuan.dispatch_import_service import DispatchImportService

        db = make_mock_db()
        service = DispatchImportService(db)

        template = service.generate_import_template()

        assert isinstance(template, bytes)
        assert len(template) > 0

        # 驗證可以被 pandas 讀取
        df = pd.read_excel(io.BytesIO(template))
        assert '派工單號' in df.columns
        assert '工程名稱/派工事項' in df.columns
        assert len(df) == 1  # 一行範例資料


# =========================================================================
# DispatchOrderService 測試
# =========================================================================

class TestDispatchOrderServiceCoreIdentifiers:
    """測試核心辨識詞提取"""

    def test_extract_dispatch_number(self):
        """提取派工單號"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        ids = DispatchOrderService._extract_core_identifiers("○○路拓寬工程 派工單013")
        assert "派工單013" in ids

    def test_extract_road_names(self):
        """提取路名"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        ids = DispatchOrderService._extract_core_identifiers("龍岡路三段拓寬工程")
        assert any("龍岡路" in i for i in ids)

    def test_extract_park_names(self):
        """提取公園名稱"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        ids = DispatchOrderService._extract_core_identifiers("霄裡公園周邊工程")
        assert "霄裡公園" in ids

    def test_extract_district(self):
        """提取行政區"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        ids = DispatchOrderService._extract_core_identifiers("中壢區道路工程")
        assert "中壢區" in ids

    def test_empty_project_name(self):
        """空名稱回傳空列表"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        ids = DispatchOrderService._extract_core_identifiers("")
        assert ids == []

        ids = DispatchOrderService._extract_core_identifiers(None)
        assert ids == []


class TestDispatchOrderServiceDocRelevance:
    """測試公文相關性評分"""

    def test_dispatch_number_exact_match(self):
        """派工單號完全匹配得到最高分"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        score = DispatchOrderService._score_document_relevance(
            doc={"subject": "有關派工單013查估作業案"},
            core_ids=["派工單013", "龍岡路"],
        )
        assert score == 1.0

    def test_generic_contract_document(self):
        """通用合約文件（契約書等）給予中等分數"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        score = DispatchOrderService._score_document_relevance(
            doc={"subject": "115年度桃園市開口契約契約書簽訂事宜"},
            core_ids=["龍岡路", "中壢區"],
        )
        assert score == 0.5

    def test_other_dispatch_location_excluded(self):
        """含其他派工單專屬地名時排除"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        score = DispatchOrderService._score_document_relevance(
            doc={"subject": "有關豐田路查估作業案"},
            core_ids=["龍岡路"],
            other_ids=["豐田路"],
        )
        assert score == 0.0

    def test_no_core_ids_returns_zero(self):
        """無核心辨識詞回傳 0"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        score = DispatchOrderService._score_document_relevance(
            doc={"subject": "一般公文"},
            core_ids=[],
        )
        assert score == 0.0

    def test_partial_match_ratio(self):
        """部分匹配按比率計算"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        score = DispatchOrderService._score_document_relevance(
            doc={"subject": "有關龍岡路拓寬案"},
            core_ids=["龍岡路", "中壢區"],
        )
        # "龍岡路" matches, "中壢區" does not => 0.5
        assert score == pytest.approx(0.5)


class TestDispatchOrderServiceSyncWorkType:
    """測試作業類別同步"""

    @pytest.mark.asyncio
    async def test_sync_work_type_empty_clears(self):
        """空字串清除所有關聯"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        db = make_mock_db()
        service = DispatchOrderService(db)

        await service._sync_work_type_links(dispatch_id=1, work_type_str="")

        # 應該執行 delete 但不 add
        db.execute.assert_called_once()
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_work_type_multiple(self):
        """逗號分隔的多個作業類別產生多筆關聯"""
        from app.services.taoyuan.dispatch_order_service import DispatchOrderService

        db = make_mock_db()
        service = DispatchOrderService(db)

        await service._sync_work_type_links(
            dispatch_id=1,
            work_type_str="02.土地協議市價查估作業, 03.土地徵收查估作業",
        )

        # delete 一次 + add 兩次
        assert db.add.call_count == 2


# =========================================================================
# ExcelImportService 測試
# =========================================================================

class TestExcelImportServiceFieldMapping:
    """測試 ExcelImportService 欄位映射"""

    def test_field_mapping_completeness(self):
        """確認核心欄位都有映射"""
        from app.services.excel_import_service import ExcelImportService

        expected_fields = ['公文ID', '公文字號', '主旨', '類別', '發文單位', '受文單位']
        for field in expected_fields:
            assert field in ExcelImportService.FIELD_MAPPING

    def test_required_fields(self):
        """確認必填欄位定義正確"""
        from app.services.excel_import_service import ExcelImportService

        assert '公文字號' in ExcelImportService.REQUIRED_FIELDS
        assert '主旨' in ExcelImportService.REQUIRED_FIELDS
        assert '類別' in ExcelImportService.REQUIRED_FIELDS

    def test_ignored_fields(self):
        """確認忽略欄位定義"""
        from app.services.excel_import_service import ExcelImportService

        assert '附件紀錄' in ExcelImportService.IGNORED_FIELDS
        assert '建立時間' in ExcelImportService.IGNORED_FIELDS


class TestExcelImportServiceValidation:
    """測試 ExcelImportService 驗證邏輯"""

    @pytest.mark.asyncio
    async def test_validate_preview_row_insert(self):
        """新增模式（無公文ID）的驗證"""
        from app.services.excel_import_service import ExcelImportService

        db = make_mock_db()
        service = ExcelImportService(db, auto_create_events=False)

        row_data = {
            '公文ID': '',
            '類別': '收文',
            '公文類型': '函',
            '公文字號': 'TEST-001',
            '主旨': '測試主旨',
        }
        result_dict = {
            "validation": {
                "invalid_categories": [],
                "invalid_doc_types": [],
                "duplicate_doc_numbers": [],
                "existing_in_db": [],
                "will_insert": 0,
                "will_update": 0,
            }
        }

        status = service._validate_preview_row(
            row_num=2,
            row_data=row_data,
            doc_numbers_seen=set(),
            existing_doc_numbers=set(),
            result=result_dict,
        )

        assert status["action"] == "insert"
        assert result_dict["validation"]["will_insert"] == 1

    @pytest.mark.asyncio
    async def test_validate_preview_row_update(self):
        """更新模式（有公文ID）的驗證"""
        from app.services.excel_import_service import ExcelImportService

        db = make_mock_db()
        service = ExcelImportService(db, auto_create_events=False)

        row_data = {
            '公文ID': '42',
            '類別': '收文',
            '公文類型': '函',
            '公文字號': 'TEST-001',
            '主旨': '測試主旨',
        }
        result_dict = {
            "validation": {
                "invalid_categories": [],
                "invalid_doc_types": [],
                "duplicate_doc_numbers": [],
                "existing_in_db": [],
                "will_insert": 0,
                "will_update": 0,
            }
        }

        status = service._validate_preview_row(
            row_num=2,
            row_data=row_data,
            doc_numbers_seen=set(),
            existing_doc_numbers=set(),
            result=result_dict,
        )

        assert status["action"] == "update"
        assert result_dict["validation"]["will_update"] == 1

    @pytest.mark.asyncio
    async def test_validate_preview_row_duplicate(self):
        """檔案內重複公文字號檢測"""
        from app.services.excel_import_service import ExcelImportService

        db = make_mock_db()
        service = ExcelImportService(db, auto_create_events=False)

        row_data = {
            '公文ID': '',
            '類別': '收文',
            '公文類型': '函',
            '公文字號': 'DUPLICATE-001',
            '主旨': '測試',
        }
        result_dict = {
            "validation": {
                "invalid_categories": [],
                "invalid_doc_types": [],
                "duplicate_doc_numbers": [],
                "existing_in_db": [],
                "will_insert": 0,
                "will_update": 0,
            }
        }

        # 第一次插入到 seen set
        doc_numbers_seen = {"DUPLICATE-001"}

        status = service._validate_preview_row(
            row_num=3,
            row_data=row_data,
            doc_numbers_seen=doc_numbers_seen,
            existing_doc_numbers=set(),
            result=result_dict,
        )

        assert "檔案內重複公文字號" in str(status["issues"])

    @pytest.mark.asyncio
    async def test_validate_preview_row_db_existing(self):
        """資料庫已存在的公文字號檢測"""
        from app.services.excel_import_service import ExcelImportService

        db = make_mock_db()
        service = ExcelImportService(db, auto_create_events=False)

        row_data = {
            '公文ID': '',
            '類別': '收文',
            '公文類型': '函',
            '公文字號': 'EXISTING-001',
            '主旨': '測試',
        }
        result_dict = {
            "validation": {
                "invalid_categories": [],
                "invalid_doc_types": [],
                "duplicate_doc_numbers": [],
                "existing_in_db": [],
                "will_insert": 0,
                "will_update": 0,
            }
        }

        status = service._validate_preview_row(
            row_num=2,
            row_data=row_data,
            doc_numbers_seen=set(),
            existing_doc_numbers={"EXISTING-001"},
            result=result_dict,
        )

        assert "資料庫已存在此公文字號" in str(status["issues"])

    @pytest.mark.asyncio
    async def test_validate_preview_row_missing_required(self):
        """缺少必填欄位時標記 warning"""
        from app.services.excel_import_service import ExcelImportService

        db = make_mock_db()
        service = ExcelImportService(db, auto_create_events=False)

        row_data = {
            '公文ID': '',
            '類別': '',
            '公文類型': '函',
            '公文字號': '',
            '主旨': '',
        }
        result_dict = {
            "validation": {
                "invalid_categories": [],
                "invalid_doc_types": [],
                "duplicate_doc_numbers": [],
                "existing_in_db": [],
                "will_insert": 0,
                "will_update": 0,
            }
        }

        status = service._validate_preview_row(
            row_num=2,
            row_data=row_data,
            doc_numbers_seen=set(),
            existing_doc_numbers=set(),
            result=result_dict,
        )

        assert status["status"] == "warning"
        assert any("缺少必填欄位" in issue for issue in status["issues"])


class TestExcelImportServiceFormatVersion:
    """測試格式版本"""

    def test_format_version(self):
        """確認格式版本"""
        from app.services.excel_import_service import ExcelImportService
        assert ExcelImportService.FORMAT_VERSION == "2.0"
