/**
 * ERP Quotation「費用核銷」Tab
 *
 * 用 case_code 查詢 expense_invoices，顯示該案件的所有費用核銷紀錄。
 * 含統計卡片 + 列表 + 新增按鈕。
 */
import React from 'react';
import { Table, Tag, Empty, Button, Typography, Row, Col, Statistic, Card } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';
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

const STATUS_MAP: Record<string, string> = {
  pending: '待審核', manager_approved: '主管核准', finance_approved: '財務核准',
  verified: '已核准', rejected: '已駁回',
};

interface Props {
  caseCode: string;
}

const ExpensesTab: React.FC<Props> = ({ caseCode }) => {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery<CaseFinanceData>({
    queryKey: ['case-finance-expenses', caseCode],
    queryFn: async () => {
      const res = await apiClient.post<{ data: CaseFinanceData }>(
        ERP_ENDPOINTS.EXPENSES_CASE_FINANCE,
        { case_code: caseCode },
      );
      return res.data;
    },
    enabled: !!caseCode,
  });

  // 只取 expense 類型的紀錄
  const expenseRecords = (data?.records ?? []).filter(r => r.type === 'expense');
  const summary = data?.summary;

  const columns: ColumnsType<FinanceRecord> = [
    { title: '發票號碼', dataIndex: 'description', key: 'inv', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
    },
    { title: '分類', dataIndex: 'category', key: 'cat', width: 110 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const color = v === 'verified' ? 'green' : v === 'rejected' ? 'red' : 'orange';
        return <Tag color={color}>{STATUS_MAP[v] ?? v}</Tag>;
      },
    },
    {
      title: '來源', dataIndex: 'source', key: 'source', width: 90,
      render: (v: string) => <Tag>{v === 'manual' ? '手動' : v === 'qr_scan' ? 'QR' : v}</Tag>,
    },
  ];

  return (
    <>
      {/* 統計卡片 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="核銷筆數" value={summary?.expense_count ?? 0} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="核銷總額" value={summary?.expense_total ?? 0} precision={0} prefix="NT$" />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="請款筆數" value={summary?.billing_count ?? 0}
              styles={{ content: { color: '#1890ff' } }} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic title="開票筆數" value={summary?.invoice_count ?? 0}
              styles={{ content: { color: '#52c41a' } }} />
          </Card>
        </Col>
      </Row>

      {/* 操作列 */}
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">
          {expenseRecords.length > 0
            ? `共 ${expenseRecords.length} 筆費用核銷紀錄`
            : '尚無費用核銷紀錄'}
        </Text>
        <Button size="small" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}>
          新增核銷
        </Button>
      </div>

      {/* 列表 */}
      {expenseRecords.length === 0 && !isLoading ? (
        <Empty description="尚無費用核銷紀錄">
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}>
            新增核銷
          </Button>
        </Empty>
      ) : (
        <Table<FinanceRecord>
          columns={columns}
          dataSource={expenseRecords}
          rowKey={(r) => `expense-${r.id}`}
          loading={isLoading}
          size="small"
          pagination={false}
        />
      )}
    </>
  );
};

export default ExpensesTab;
