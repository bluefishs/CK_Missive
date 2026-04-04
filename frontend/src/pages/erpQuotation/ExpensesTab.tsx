/**
 * ERP Quotation「費用核銷」Tab — 完整 CRUD
 *
 * 用 case_code 查詢 expense_invoices，含新增/編輯/刪除/審核操作。
 */
import React from 'react';
import {
  Table, Tag, Empty, Button, Typography, Row, Col,
  Statistic, Card, Space, Popconfirm, App,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import {
  useApproveExpense, useRejectExpense, useDeleteExpense,
} from '../../hooks';
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

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '待審核', color: 'orange' },
  manager_approved: { label: '主管核准', color: 'blue' },
  finance_approved: { label: '財務核准', color: 'cyan' },
  verified: { label: '已核准', color: 'green' },
  rejected: { label: '已駁回', color: 'red' },
};

interface Props {
  caseCode: string;
}

const ExpensesTab: React.FC<Props> = ({ caseCode }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();
  const deleteMutation = useDeleteExpense();

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

  const expenseRecords = (data?.records ?? []).filter(r => r.type === 'expense');
  const summary = data?.summary;

  const handleApprove = (id: number) => {
    approveMutation.mutate(id, {
      onSuccess: () => message.success('審核通過'),
      onError: () => message.error('審核失敗'),
    });
  };

  const handleReject = (id: number) => {
    rejectMutation.mutate({ id, reason: '' }, {
      onSuccess: () => message.success('已駁回'),
      onError: () => message.error('駁回失敗'),
    });
  };

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => message.success('已刪除'),
      onError: (err: unknown) => {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(detail || '刪除失敗');
      },
    });
  };

  const columns: ColumnsType<FinanceRecord> = [
    { title: '發票號碼', dataIndex: 'description', key: 'inv', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
    },
    { title: '分類', dataIndex: 'category', key: 'cat', width: 100 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100,
      render: (v: string) => {
        const cfg = STATUS_MAP[v] ?? { label: v, color: 'default' };
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: '操作', key: 'actions', width: 180,
      render: (_: unknown, record: FinanceRecord) => {
        const canEdit = ['pending', 'rejected'].includes(record.status);
        const canApprove = !['verified', 'rejected'].includes(record.status);
        return (
          <Space size="small">
            {canEdit && (
              <Button type="link" size="small" icon={<EditOutlined />}
                onClick={() => navigate(`${ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.id))}`)}
              >
                編輯
              </Button>
            )}
            {canApprove && (
              <Button type="link" size="small" icon={<CheckCircleOutlined />}
                style={{ color: '#52c41a' }}
                onClick={() => handleApprove(record.id)}
                loading={approveMutation.isPending}
              >
                審核
              </Button>
            )}
            {canApprove && (
              <Popconfirm title="確定駁回？" onConfirm={() => handleReject(record.id)} okText="駁回" cancelText="取消">
                <Button type="link" size="small" icon={<CloseCircleOutlined />} danger>駁回</Button>
              </Popconfirm>
            )}
            {canEdit && (
              <Popconfirm title="確定刪除此筆費用？" onConfirm={() => handleDelete(record.id)} okText="刪除" cancelText="取消">
                <Button type="link" size="small" icon={<DeleteOutlined />} danger>刪除</Button>
              </Popconfirm>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="核銷筆數" value={summary?.expense_count ?? 0} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="核銷總額" value={summary?.expense_total ?? 0} precision={0} prefix="NT$" /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="請款筆數" value={summary?.billing_count ?? 0}
            styles={{ content: { color: '#1890ff' } }} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small"><Statistic title="開票筆數" value={summary?.invoice_count ?? 0}
            styles={{ content: { color: '#52c41a' } }} /></Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">
          {expenseRecords.length > 0 ? `共 ${expenseRecords.length} 筆費用核銷紀錄` : '尚無費用核銷紀錄'}
        </Text>
        <Button type="primary" size="small" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}>
          新增核銷
        </Button>
      </div>

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
