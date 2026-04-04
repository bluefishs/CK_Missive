/**
 * PM Case 費用核銷 Tab — 顯示該案件所有費用發票
 */
import React from 'react';
import { Table, Tag, Empty, Button, Typography, Row, Col, Statistic, Card } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useExpenses } from '../../hooks';
import type { ExpenseInvoice } from '../../types/erp';
import { EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS } from '../../types/erp';
import { ROUTES } from '../../router/types';
import type { ColumnsType } from 'antd/es/table';

const { Text } = Typography;

interface Props {
  caseCode: string;
}

const ExpensesTab: React.FC<Props> = ({ caseCode }) => {
  const navigate = useNavigate();
  const { data, isLoading } = useExpenses({ case_code: caseCode, skip: 0, limit: 100 });
  const items = data?.items ?? [];
  const total = items.reduce((s, i) => s + Number(i.amount || 0), 0);

  const columns: ColumnsType<ExpenseInvoice> = [
    { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 120 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 100 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 110, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
    },
    { title: '分類', dataIndex: 'category', key: 'category', width: 100 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => (
        <Tag color={EXPENSE_STATUS_COLORS[v as keyof typeof EXPENSE_STATUS_COLORS] ?? 'default'}>
          {EXPENSE_STATUS_LABELS[v as keyof typeof EXPENSE_STATUS_LABELS] ?? v}
        </Tag>
      ),
    },
    { title: '來源', dataIndex: 'source', key: 'source', width: 80 },
  ];

  if (!isLoading && items.length === 0) {
    return (
      <Empty description="尚無費用核銷紀錄">
        <Button
          type="primary" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}
        >
          新增核銷
        </Button>
      </Empty>
    );
  }

  const pendingCount = items.filter(i => !['verified', 'rejected'].includes(i.status)).length;
  const verifiedTotal = items.filter(i => i.status === 'verified').reduce((s, i) => s + Number(i.amount || 0), 0);

  return (
    <>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="核銷筆數" value={items.length} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="核銷總額" value={total} precision={0} prefix="NT$" /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="已核准" value={verifiedTotal} precision={0} prefix="NT$" valueStyle={{ color: '#52c41a' }} /></Card></Col>
        <Col xs={12} sm={6}><Card size="small"><Statistic title="待審核" value={pendingCount} valueStyle={{ color: pendingCount > 0 ? '#faad14' : undefined }} /></Card></Col>
      </Row>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">共 {items.length} 筆，合計 NT$ {total.toLocaleString()}</Text>
        <Button
          size="small" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}
        >
          新增
        </Button>
      </div>
      <Table<ExpenseInvoice>
        columns={columns}
        dataSource={items}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={false}
        onRow={(record) => ({
          onClick: () => navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(record.id))),
          style: { cursor: 'pointer' },
        })}
      />
    </>
  );
};

export default ExpensesTab;
