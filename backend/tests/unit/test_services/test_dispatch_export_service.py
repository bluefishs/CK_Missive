"""
DispatchExportService 單元測試

測試 5 個工作表產生器、輔助方法和匯出上限。
使用 MagicMock 模擬 ORM 模型，不需要資料庫連線。

@version 1.0.0
@date 2026-02-25
"""

import pytest
from datetime import datetime, date
from io import BytesIO
from unittest.mock import MagicMock, AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.taoyuan.dispatch_export_service import (
    DispatchExportService,
    MAX_EXPORT_ROWS,
    WORK_CATEGORY_LABELS,
    STATUS_LABELS,
)


# =========================================================================
# Mock 工廠
# =========================================================================

def make_dispatch(
    *,
    id: int = 1,
    dispatch_no: str = '114年_派工單號001',
    project_name: str = '測試工程',
    sub_case_name: str = '',
    work_type: str = '02.土地協議市價查估作業',
    case_handler: str = '王大明',
    survey_unit: str = '測試事務所',
    deadline: str = '114年06月30日前',
    contract_project_id: int = 21,
    created_at: datetime | None = None,
    document_links: list | None = None,
    attachments: list | None = None,
    payment=None,
) -> MagicMock:
    """建立 Mock TaoyuanDispatchOrder"""
    d = MagicMock()
    d.id = id
    d.dispatch_no = dispatch_no
    d.project_name = project_name
    d.sub_case_name = sub_case_name
    d.work_type = work_type
    d.case_handler = case_handler
    d.survey_unit = survey_unit
    d.deadline = deadline
    d.contract_project_id = contract_project_id
    d.created_at = created_at or datetime(2026, 1, 15, 10, 30)
    d.document_links = document_links or []
    d.attachments = attachments or []
    d.payment = payment
    return d


def make_doc_link(
    *,
    link_type: str = 'agency_incoming',
    doc_number: str = '桃工養字第001號',
    doc_date: date | None = None,
    subject: str = '測試來文',
) -> MagicMock:
    """建立 Mock TaoyuanDispatchDocumentLink (含 document)"""
    link = MagicMock()
    link.link_type = link_type

    doc = MagicMock()
    doc.doc_number = doc_number
    doc.doc_date = doc_date or date(2026, 1, 10)
    doc.subject = subject
    link.document = doc
    return link


def make_work_record(
    *,
    dispatch_order_id: int = 1,
    sort_order: int = 1,
    work_category: str = 'dispatch_notice',
    description: str = '派工通知',
    record_date: date | None = None,
    deadline_date: date | None = None,
    completed_date: date | None = None,
    status: str = 'pending',
    document=None,
    incoming_doc=None,
    outgoing_doc=None,
) -> MagicMock:
    """建立 Mock TaoyuanWorkRecord"""
    wr = MagicMock()
    wr.dispatch_order_id = dispatch_order_id
    wr.sort_order = sort_order
    wr.work_category = work_category
    wr.description = description
    wr.record_date = record_date or date(2026, 1, 20)
    wr.deadline_date = deadline_date
    wr.completed_date = completed_date
    wr.status = status
    wr.document = document
    wr.incoming_doc = incoming_doc
    wr.outgoing_doc = outgoing_doc
    return wr


def make_payment(
    *,
    current_amount: float = 50000,
    cumulative_amount: float = 120000,
    remaining_amount: float = 80000,
    acceptance_date: date | None = None,
    **work_amounts,
) -> MagicMock:
    """建立 Mock TaoyuanContractPayment"""
    p = MagicMock()
    p.current_amount = current_amount
    p.cumulative_amount = cumulative_amount
    p.remaining_amount = remaining_amount
    p.acceptance_date = acceptance_date

    # 7 項作業金額
    for idx in range(1, 8):
        date_attr = f'work_{idx:02d}_date'
        amount_attr = f'work_{idx:02d}_amount'
        setattr(p, date_attr, work_amounts.get(date_attr))
        setattr(p, amount_attr, work_amounts.get(amount_attr))

    return p


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture
def mock_db():
    """建立 Mock 資料庫 session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def service(mock_db):
    """建立 DispatchExportService"""
    return DispatchExportService(mock_db)


# =========================================================================
# 輔助方法測試
# =========================================================================

class TestFmtDate:
    """_fmt_date 日期格式化"""

    def test_none(self):
        assert DispatchExportService._fmt_date(None) == ''

    def test_date(self):
        assert DispatchExportService._fmt_date(date(2026, 3, 15)) == '2026-03-15'

    def test_datetime(self):
        assert DispatchExportService._fmt_date(datetime(2026, 3, 15, 10, 30)) == '2026-03-15'

    def test_string_passthrough(self):
        assert DispatchExportService._fmt_date('114年06月30日') == '114年06月30日'


class TestFmtDatetime:
    """_fmt_datetime 日期時間格式化"""

    def test_none(self):
        assert DispatchExportService._fmt_datetime(None) == ''

    def test_datetime(self):
        assert DispatchExportService._fmt_datetime(datetime(2026, 3, 15, 14, 30)) == '2026-03-15 14:30'

    def test_date_only(self):
        assert DispatchExportService._fmt_datetime(date(2026, 3, 15)) == '2026-03-15'

    def test_string_passthrough(self):
        assert DispatchExportService._fmt_datetime('custom') == 'custom'


class TestGetRecordDocNumber:
    """_get_record_doc_number 公文字號提取"""

    def test_primary_document(self):
        doc = MagicMock()
        doc.doc_number = 'DOC-001'
        wr = make_work_record(document=doc)
        assert DispatchExportService._get_record_doc_number(wr) == 'DOC-001'

    def test_incoming_doc_fallback(self):
        incoming = MagicMock()
        incoming.doc_number = '桃工養字第001號'
        wr = make_work_record(document=None, incoming_doc=incoming)
        assert DispatchExportService._get_record_doc_number(wr) == '桃工養字第001號'

    def test_outgoing_doc_fallback(self):
        outgoing = MagicMock()
        outgoing.doc_number = '乾字第001號'
        wr = make_work_record(document=None, incoming_doc=None, outgoing_doc=outgoing)
        assert DispatchExportService._get_record_doc_number(wr) == '乾字第001號'

    def test_no_doc_returns_empty(self):
        wr = make_work_record(document=None, incoming_doc=None, outgoing_doc=None)
        assert DispatchExportService._get_record_doc_number(wr) == ''

    def test_doc_number_is_none(self):
        doc = MagicMock()
        doc.doc_number = None
        wr = make_work_record(document=doc, incoming_doc=None, outgoing_doc=None)
        assert DispatchExportService._get_record_doc_number(wr) == ''


class TestGetCurrentStage:
    """_get_current_stage 當前階段識別"""

    def test_empty_records(self):
        assert DispatchExportService._get_current_stage([]) == ''

    def test_all_completed(self):
        records = [
            make_work_record(sort_order=1, status='completed'),
            make_work_record(sort_order=2, status='completed'),
        ]
        assert DispatchExportService._get_current_stage(records) == '全部完成'

    def test_latest_non_completed(self):
        records = [
            make_work_record(sort_order=1, status='completed', work_category='dispatch_notice'),
            make_work_record(sort_order=2, status='in_progress', work_category='work_result'),
            make_work_record(sort_order=3, status='pending', work_category='survey_notice'),
        ]
        # Reversed: finds sort_order=3 first
        assert DispatchExportService._get_current_stage(records) == '查估通知'

    def test_unknown_category(self):
        records = [
            make_work_record(sort_order=1, status='pending', work_category='unknown_type'),
        ]
        assert DispatchExportService._get_current_stage(records) == 'unknown_type'

    def test_single_pending(self):
        records = [
            make_work_record(sort_order=1, status='pending', work_category='meeting_notice'),
        ]
        assert DispatchExportService._get_current_stage(records) == '會議通知'


# =========================================================================
# Sheet Builder 測試
# =========================================================================

class TestBuildSheet1:
    """Sheet 1: 派工總表"""

    def test_empty_dispatches(self, service):
        df = service._build_sheet1([], {})
        assert len(df) == 0

    def test_single_dispatch(self, service):
        incoming = make_doc_link(link_type='agency_incoming')
        outgoing = make_doc_link(link_type='company_outgoing', doc_number='乾字第001號')

        dispatch = make_dispatch(
            id=1,
            dispatch_no='114年_派工單號001',
            document_links=[incoming, outgoing],
            attachments=[MagicMock(), MagicMock()],
            payment=make_payment(current_amount=50000, cumulative_amount=120000),
        )

        records = [
            make_work_record(status='completed'),
            make_work_record(sort_order=2, status='in_progress'),
        ]
        wr_by_dispatch = {1: records}

        df = service._build_sheet1([dispatch], wr_by_dispatch)

        assert len(df) == 1
        row = df.iloc[0]
        assert row['派工單號'] == '114年_派工單號001'
        assert row['來文數'] == 1
        assert row['覆文數'] == 1
        assert row['作業紀錄數'] == 2
        assert row['已完成數'] == 1
        assert row['本次金額'] == 50000
        assert row['累進金額'] == 120000
        assert row['附件數'] == 2

    def test_dispatch_without_payment(self, service):
        dispatch = make_dispatch(payment=None)
        df = service._build_sheet1([dispatch], {})

        row = df.iloc[0]
        assert row['本次金額'] is None
        assert row['累進金額'] is None

    def test_dispatch_without_records(self, service):
        dispatch = make_dispatch()
        df = service._build_sheet1([dispatch], {})

        row = df.iloc[0]
        assert row['作業紀錄數'] == 0
        assert row['已完成數'] == 0
        assert row['當前階段'] == ''


class TestBuildSheet2:
    """Sheet 2: 作業紀錄明細"""

    def test_empty_records(self, service):
        df = service._build_sheet2([], [])
        assert len(df) == 0

    def test_records_with_dispatch_lookup(self, service):
        dispatches = [make_dispatch(id=1, dispatch_no='D001', project_name='工程A')]

        doc = MagicMock()
        doc.doc_number = '桃工養字第100號'

        records = [
            make_work_record(
                dispatch_order_id=1,
                sort_order=1,
                work_category='dispatch_notice',
                description='派工通知說明',
                status='completed',
                completed_date=date(2026, 2, 1),
                document=doc,
            ),
            make_work_record(
                dispatch_order_id=1,
                sort_order=2,
                work_category='work_result',
                description='成果繳交',
                status='pending',
                document=None,
                incoming_doc=None,
                outgoing_doc=None,
            ),
        ]

        df = service._build_sheet2(dispatches, records)

        assert len(df) == 2
        assert df.iloc[0]['派工單號'] == 'D001'
        assert df.iloc[0]['工程名稱'] == '工程A'
        assert df.iloc[0]['分類'] == '派工通知'
        assert df.iloc[0]['狀態'] == '已完成'
        assert df.iloc[0]['關聯公文字號'] == '桃工養字第100號'
        assert df.iloc[1]['分類'] == '作業成果'
        assert df.iloc[1]['狀態'] == '待處理'
        assert df.iloc[1]['關聯公文字號'] == ''

    def test_unknown_dispatch_id(self, service):
        """作業紀錄的 dispatch_order_id 無對應派工單"""
        records = [make_work_record(dispatch_order_id=999)]
        df = service._build_sheet2([], records)

        assert len(df) == 1
        assert df.iloc[0]['派工單號'] == ''
        assert df.iloc[0]['工程名稱'] == ''


class TestBuildSheet3:
    """Sheet 3: 公文對照矩陣 (3 階段配對)"""

    def test_empty(self, service):
        df = service._build_sheet3([], {})
        assert len(df) == 0

    def test_dispatch_with_no_links_no_records(self, service):
        dispatch = make_dispatch(document_links=[])
        df = service._build_sheet3([dispatch], {})
        assert len(df) == 0

    def test_unassigned_date_proximity_pairing(self, service):
        """未指派公文透過日期接近度配對"""
        incoming = make_doc_link(
            link_type='agency_incoming',
            doc_number='桃工養字第001號',
            subject='來文主旨A',
            doc_date=date(2026, 1, 10),
        )
        outgoing = make_doc_link(
            link_type='company_outgoing',
            doc_number='乾坤字第001號',
            subject='覆文主旨A',
            doc_date=date(2026, 1, 20),
        )
        dispatch = make_dispatch(dispatch_no='D001', document_links=[incoming, outgoing])
        df = service._build_sheet3([dispatch], {})

        assert len(df) == 1
        row = df.iloc[0]
        assert row['派工單號'] == 'D001'
        assert row['來文字號'] == '桃工養字第001號'
        assert row['覆文字號'] == '乾坤字第001號'

    def test_unbalanced_more_incoming(self, service):
        """來文多於覆文時有 standalone 列"""
        incoming1 = make_doc_link(
            link_type='agency_incoming', doc_number='IN-001', doc_date=date(2026, 1, 1)
        )
        incoming2 = make_doc_link(
            link_type='agency_incoming', doc_number='IN-002', doc_date=date(2026, 2, 1)
        )
        outgoing1 = make_doc_link(
            link_type='company_outgoing', doc_number='乾坤字OUT-001', doc_date=date(2026, 1, 15)
        )

        dispatch = make_dispatch(document_links=[incoming1, incoming2, outgoing1])
        df = service._build_sheet3([dispatch], {})

        assert len(df) == 2
        # IN-001 配對 OUT-001 (date proximity: 1/1 -> 1/15)
        assert df.iloc[0]['來文字號'] == 'IN-001'
        assert df.iloc[0]['覆文字號'] == '乾坤字OUT-001'
        # IN-002 standalone
        assert df.iloc[1]['來文字號'] == 'IN-002'
        assert df.iloc[1]['覆文字號'] == ''


class TestPairDocumentsPhase1:
    """Phase 1: parent_record_id chain pairing"""

    def test_chain_pairing(self, service):
        """透過 parent_record_id 配對"""
        in_doc = MagicMock()
        in_doc.id = 100
        in_doc.doc_number = 'IN-001'
        in_doc.doc_date = date(2026, 1, 10)
        in_doc.subject = '來文'

        out_doc = MagicMock()
        out_doc.id = 200
        out_doc.doc_number = '乾坤字OUT-001'
        out_doc.doc_date = date(2026, 1, 20)
        out_doc.subject = '覆文'

        r_in = make_work_record(
            dispatch_order_id=1, sort_order=1,
            incoming_doc=in_doc, outgoing_doc=None, document=None,
        )
        r_in.id = 10

        r_out = make_work_record(
            dispatch_order_id=1, sort_order=2,
            incoming_doc=None, outgoing_doc=out_doc, document=None,
        )
        r_out.id = 20
        r_out.parent_record_id = 10  # chain → r_in

        pairs = service._pair_documents_for_dispatch([r_in, r_out], [])

        assert len(pairs) == 1
        inc, out = pairs[0]
        assert inc['doc_number'] == 'IN-001'
        assert out['doc_number'] == '乾坤字OUT-001'


class TestPairDocumentsPhase2:
    """Phase 2: date proximity greedy pairing"""

    def test_date_proximity_selects_closest(self, service):
        """選擇日期最接近的覆文"""
        in_doc = MagicMock()
        in_doc.id = 100
        in_doc.doc_number = 'IN-001'
        in_doc.doc_date = date(2026, 1, 10)
        in_doc.subject = '來文'

        out_doc1 = MagicMock()
        out_doc1.id = 201
        out_doc1.doc_number = '乾坤字A'
        out_doc1.doc_date = date(2026, 3, 1)  # 遠
        out_doc1.subject = '遠覆文'

        out_doc2 = MagicMock()
        out_doc2.id = 202
        out_doc2.doc_number = '乾坤字B'
        out_doc2.doc_date = date(2026, 1, 15)  # 近
        out_doc2.subject = '近覆文'

        r_in = make_work_record(incoming_doc=in_doc, outgoing_doc=None, document=None)
        r_in.id = 10
        r_out1 = make_work_record(incoming_doc=None, outgoing_doc=out_doc1, document=None)
        r_out1.id = 20
        r_out2 = make_work_record(incoming_doc=None, outgoing_doc=out_doc2, document=None)
        r_out2.id = 21

        pairs = service._pair_documents_for_dispatch([r_in, r_out1, r_out2], [])

        # IN-001 應配對 乾坤字B (1/15，最接近 1/10)
        paired_in, paired_out = pairs[0]
        assert paired_in['doc_number'] == 'IN-001'
        assert paired_out['doc_number'] == '乾坤字B'

    def test_outgoing_before_incoming_becomes_standalone(self, service):
        """覆文日期早於所有來文時成為 standalone"""
        in_doc = MagicMock()
        in_doc.id = 100
        in_doc.doc_number = 'IN-001'
        in_doc.doc_date = date(2026, 3, 1)
        in_doc.subject = '來文'

        out_doc = MagicMock()
        out_doc.id = 200
        out_doc.doc_number = '乾坤字OUT'
        out_doc.doc_date = date(2026, 1, 1)  # 早於來文
        out_doc.subject = '覆文'

        r_in = make_work_record(incoming_doc=in_doc, outgoing_doc=None, document=None)
        r_in.id = 10
        r_out = make_work_record(incoming_doc=None, outgoing_doc=out_doc, document=None)
        r_out.id = 20

        pairs = service._pair_documents_for_dispatch([r_in, r_out], [])

        assert len(pairs) == 2
        # 應各自 standalone (因覆文日期 < 來文日期)
        doc_numbers = [
            (p[0]['doc_number'] if p[0] else None, p[1]['doc_number'] if p[1] else None)
            for p in pairs
        ]
        assert (None, '乾坤字OUT') in doc_numbers
        assert ('IN-001', None) in doc_numbers


class TestPairDocumentsNewFormat:
    """新格式 document 欄位的方向判斷"""

    def test_new_format_outgoing_detection(self, service):
        """乾坤開頭的 doc_number 判定為覆文"""
        doc = MagicMock()
        doc.id = 300
        doc.doc_number = '乾坤測字第001號'
        doc.doc_date = date(2026, 2, 1)
        doc.subject = '覆文測試'

        r = make_work_record(incoming_doc=None, outgoing_doc=None, document=doc)
        r.id = 30
        r.incoming_doc_id = None
        r.outgoing_doc_id = None

        pairs = service._pair_documents_for_dispatch([r], [])

        assert len(pairs) == 1
        assert pairs[0][0] is None  # 無來文
        assert pairs[0][1]['doc_number'] == '乾坤測字第001號'

    def test_new_format_incoming_detection(self, service):
        """非乾坤開頭判定為來文"""
        doc = MagicMock()
        doc.id = 301
        doc.doc_number = '桃工養字第999號'
        doc.doc_date = date(2026, 2, 1)
        doc.subject = '來文測試'

        r = make_work_record(incoming_doc=None, outgoing_doc=None, document=doc)
        r.id = 31
        r.incoming_doc_id = None
        r.outgoing_doc_id = None

        pairs = service._pair_documents_for_dispatch([r], [])

        assert len(pairs) == 1
        assert pairs[0][0]['doc_number'] == '桃工養字第999號'
        assert pairs[0][1] is None  # 無覆文


class TestIsOutgoing:
    """is_outgoing_doc_number 方向判斷 (SSOT: app.utils.doc_helpers)"""

    def test_outgoing(self):
        from app.utils.doc_helpers import is_outgoing_doc_number
        assert is_outgoing_doc_number('乾坤測字第001號') is True

    def test_incoming(self):
        from app.utils.doc_helpers import is_outgoing_doc_number
        assert is_outgoing_doc_number('桃工養字第001號') is False

    def test_empty(self):
        from app.utils.doc_helpers import is_outgoing_doc_number
        assert is_outgoing_doc_number('') is False


class TestBuildSheet4:
    """Sheet 4: 契金摘要"""

    def test_empty(self, service):
        df = service._build_sheet4([])
        assert len(df) == 0

    def test_dispatch_without_payment_skipped(self, service):
        dispatch = make_dispatch(payment=None)
        df = service._build_sheet4([dispatch])
        assert len(df) == 0

    def test_payment_columns(self, service):
        payment = make_payment(
            current_amount=30000,
            cumulative_amount=90000,
            remaining_amount=60000,
            acceptance_date=date(2026, 6, 30),
            work_01_amount=10000,
            work_01_date=date(2026, 2, 1),
            work_02_amount=20000,
        )
        dispatch = make_dispatch(dispatch_no='D001', payment=payment)
        df = service._build_sheet4([dispatch])

        assert len(df) == 1
        row = df.iloc[0]
        assert row['派工單號'] == 'D001'
        assert row['本次金額'] == 30000
        assert row['累進金額'] == 90000
        assert row['剩餘金額'] == 60000
        assert row['驗收日期'] == '2026-06-30'
        assert row['01.地上物查估(金額)'] == 10000
        assert row['01.地上物查估(日期)'] == '2026-02-01'


class TestBuildSheet5:
    """Sheet 5: 統計摘要"""

    def test_basic_stats(self, service):
        incoming = make_doc_link(link_type='agency_incoming')
        outgoing = make_doc_link(link_type='company_outgoing')

        dispatches = [
            make_dispatch(
                id=1,
                document_links=[incoming, outgoing],
                payment=make_payment(cumulative_amount=100000),
            ),
            make_dispatch(
                id=2,
                document_links=[make_doc_link(link_type='agency_incoming')],
                payment=make_payment(cumulative_amount=50000),
            ),
        ]
        records = [
            make_work_record(status='completed'),
            make_work_record(status='pending'),
            make_work_record(status='completed'),
        ]

        df = service._build_sheet5(dispatches, records, '全部')

        # 轉為 dict 方便查找
        stats = dict(zip(df['項目'], df['值']))

        assert stats['派工單總數'] == 2
        assert stats['作業紀錄總數'] == 3
        assert stats['已完成紀錄'] == 2
        assert stats['來文總數'] == 2
        assert stats['覆文總數'] == 1
        assert stats['契金累計總額'] == 150000
        assert stats['篩選條件'] == '全部'

    def test_empty_data(self, service):
        df = service._build_sheet5([], [], '全部')

        stats = dict(zip(df['項目'], df['值']))
        assert stats['派工單總數'] == 0
        assert stats['作業紀錄總數'] == 0
        assert stats['契金累計總額'] == 0


# =========================================================================
# 匯出上限測試
# =========================================================================

class TestExportMasterMatrix:
    """export_master_matrix 整合行為"""

    @pytest.mark.asyncio
    async def test_exceeds_max_rows_raises(self, service, mock_db):
        """超過 MAX_EXPORT_ROWS 應拋出 ValueError"""
        # 模擬查詢回傳超過上限的結果
        too_many = [make_dispatch(id=i) for i in range(MAX_EXPORT_ROWS + 1)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_unique = MagicMock()
        mock_unique.all.return_value = too_many
        mock_scalars.unique.return_value = mock_unique
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match='匯出上限'):
            await service.export_master_matrix()

    @pytest.mark.asyncio
    async def test_success_returns_bytesio(self, service, mock_db):
        """正常匯出回傳 BytesIO"""
        dispatches = [make_dispatch(id=1, payment=None)]

        # Mock dispatch query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_unique = MagicMock()
        mock_unique.all.return_value = dispatches
        mock_scalars.unique.return_value = mock_unique
        mock_result.scalars.return_value = mock_scalars

        # Mock work record query (empty)
        mock_wr_result = MagicMock()
        mock_wr_scalars = MagicMock()
        mock_wr_unique = MagicMock()
        mock_wr_unique.all.return_value = []
        mock_wr_scalars.unique.return_value = mock_wr_unique
        mock_wr_result.scalars.return_value = mock_wr_scalars

        mock_db.execute.side_effect = [mock_result, mock_wr_result]

        result = await service.export_master_matrix()

        assert isinstance(result, BytesIO)
        # 確認是有效的 Excel 檔案 (XLSX magic bytes: PK)
        content = result.getvalue()
        assert len(content) > 0
        assert content[:2] == b'PK'  # ZIP/XLSX magic bytes

    @pytest.mark.asyncio
    async def test_empty_dispatches_returns_valid_excel(self, service, mock_db):
        """無資料也應回傳有效 Excel"""
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_unique = MagicMock()
        mock_unique.all.return_value = []
        mock_scalars.unique.return_value = mock_unique
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.export_master_matrix()

        assert isinstance(result, BytesIO)
        content = result.getvalue()
        assert content[:2] == b'PK'


# =========================================================================
# 常數驗證
# =========================================================================

class TestConstants:
    """驗證常數定義完整性"""

    def test_work_category_labels(self):
        assert len(WORK_CATEGORY_LABELS) == 7
        assert 'dispatch_notice' in WORK_CATEGORY_LABELS
        assert 'other' in WORK_CATEGORY_LABELS

    def test_status_labels(self):
        assert len(STATUS_LABELS) == 5
        assert 'pending' in STATUS_LABELS
        assert 'completed' in STATUS_LABELS

    def test_max_export_rows(self):
        assert MAX_EXPORT_ROWS == 2000
