/**
 * 承攬案件「財務紀錄」Tab
 *
 * 整合 ERP 報價摘要 + 應收(billing) + 開票(invoice) + 應付(vendor_payable) + 費用核銷(expense)
 * 使用 /erp/expenses/case-finance API。
 */
import React from 'react';
import {
  Table, Tag, Empty, Button, Typography, Row, Col, Statistic, Card, Space,
} from 'antd';
import {
  PlusOutlined, DollarOutlined, ArrowRightOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../../api/client';
import { ERP_ENDPOINTS } from '../../../api/endpoints';
import { useCrossModuleLookup } from '../../../hooks/business/usePMCases';
import { ROUTES } from '../../../router/types';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

interface FinanceRecord {
  type: 'expense' | 'billing' | 'invoice';
  id: number;
  date: string | null;
  amount: number;
  description: string;
  category: string;
  status: string;
  source: string;
}

interface CaseFinanceData {
  case_code: string;
  records: FinanceRecord[];
  summary: {
    expense_count: number; expense_total: number;
    billing_count: number; billing_total: number;
    invoice_count: number; invoice_total: number;
  };
}

const TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  expense: { label: '費用核銷', color: 'orange' },
  billing: { label: '請款(應收)', color: 'blue' },
  invoice: { label: '開票', color: 'green' },
};

const STATUS_MAP: Record<string, string> = {
  pending: '待審核', manager_approved: '主管核准', finance_approved: '財務核准',
  verified: '已核准', rejected: '已駁回',
  unpaid: '未收款', partial: '部分收款', paid: '已收款', issued: '已開立',
};

interface Props {
  caseCode: string | null;
  projectCode?: string | null;
}

const FinanceTab: React.FC<Props> = ({ caseCode, projectCode }) => {
  const navigate = useNavigate();
  const lookupKey = caseCode || projectCode || null;

  // ERP 報價摘要
  const { data: crossData } = useCrossModuleLookup(lookupKey);
  const erp = crossData?.erp;

  // 案件財務紀錄
  const { data: financeData, isLoading } = useQuery<CaseFinanceData>({
    queryKey: ['case-finance', lookupKey],
    queryFn: async () => {
      const res = await apiClient.post<{ data: CaseFinanceData }>(
        ERP_ENDPOINTS.EXPENSES_CASE_FINANCE,
        { case_code: lookupKey },
      );
      return res.data;
    },
    enabled: !!lookupKey,
  });

  const records = financeData?.records ?? [];
  const summary = financeData?.summary;

  const columns: ColumnsType<FinanceRecord> = [
    {
      title: '類型', dataIndex: 'type', key: 'type', width: 110,
      render: (v: string) => {
        const cfg = TYPE_CONFIG[v] ?? { label: v, color: 'default' };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
      filters: [
        { text: '費用核銷', value: 'expense' },
        { text: '請款(應收)', value: 'billing' },
        { text: '開票', value: 'invoice' },
      ],
      onFilter: (value, record) => record.type === value,
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110, sorter: (a, b) => (a.date ?? '').localeCompare(b.date ?? '') },
    { title: '說明', dataIndex: 'description', key: 'desc', ellipsis: true },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
      sorter: (a, b) => a.amount - b.amount,
    },
    { title: '分類', dataIndex: 'category', key: 'cat', width: 100 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag>{STATUS_MAP[v] ?? v}</Tag>,
    },
  ];

  if (!lookupKey) {
    return <Empty description="此案件尚無案件代碼，無法查詢財務紀錄" />;
  }

  return (
    <>
      {/* ERP 報價摘要 (若有) */}
      {erp && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 8]} align="middle">
            <Col flex="auto">
              <Space size="large">
                <Statistic title="合約總價" value={Number(erp.total_price || 0)} precision={0} prefix="NT$" />
                <Statistic title="毛利" value={Number(erp.gross_profit || 0)} precision={0} prefix="NT$"
                  styles={{ content: { color: Number(erp.gross_profit || 0) >= 0 ? '#52c41a' : '#ff4d4f' } }} />
                <Statistic title="報價狀態" value={erp.status === 'confirmed' ? '已確認' : erp.status} />
              </Space>
            </Col>
            <Col>
              <Button icon={<ArrowRightOutlined />} onClick={() => navigate(`${ROUTES.ERP_QUOTATION_DETAIL}`.replace(':id', String(erp.id)))}>
                報價詳情
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 財務紀錄統計 */}
      {summary && (
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="應收(請款)" value={summary.billing_total} precision={0} prefix="NT$"
                suffix={<Text type="secondary"> ({summary.billing_count})</Text>}
                styles={{ content: { color: '#1890ff' } }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="開票" value={summary.invoice_total} precision={0} prefix="NT$"
                suffix={<Text type="secondary"> ({summary.invoice_count})</Text>}
                styles={{ content: { color: '#52c41a' } }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="費用核銷" value={summary.expense_total} precision={0} prefix="NT$"
                suffix={<Text type="secondary"> ({summary.expense_count})</Text>}
                styles={{ content: { color: '#fa8c16' } }} />
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card size="small">
              <Statistic title="紀錄總筆數" value={records.length} />
            </Card>
          </Col>
        </Row>
      )}

      {/* 操作列 */}
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">{records.length > 0 ? `共 ${records.length} 筆財務紀錄` : ''}</Text>
        <Button size="small" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${lookupKey}`)}>
          新增費用核銷
        </Button>
      </div>

      {/* 紀錄列表 */}
      {records.length === 0 && !isLoading ? (
        <Empty description="尚無財務紀錄">
          <Space>
            <Button type="primary" icon={<PlusOutlined />}
              onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${lookupKey}`)}>
              新增費用核銷
            </Button>
            {!erp && (
              <Button icon={<DollarOutlined />}
                onClick={() => navigate(ROUTES.PM_CASES)}>
                前往邀標報價建立 ERP 報價
              </Button>
            )}
          </Space>
        </Empty>
      ) : (
        <Table<FinanceRecord>
          columns={columns}
          dataSource={records}
          rowKey={(r) => `${r.type}-${r.id}`}
          loading={isLoading}
          size="small"
          pagination={records.length > 20 ? { pageSize: 20 } : false}
        />
      )}
    </>
  );
};

export default FinanceTab;
