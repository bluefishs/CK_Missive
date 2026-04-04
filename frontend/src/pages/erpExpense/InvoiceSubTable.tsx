/**
 * 費用發票展開子表 — 分組展開後顯示單筆發票明細 + 審核操作
 *
 * 拆分自 ERPExpenseListPage.tsx
 */
import React from 'react';
import { Table, Tag, Button, Space, Spin } from 'antd';
import { App, Popconfirm } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import type { NavigateFunction } from 'react-router-dom';
import { useExpenses, useApproveExpense, useRejectExpense } from '../../hooks';
import type { ExpenseInvoice, ExpenseInvoiceQuery } from '../../types/erp';
import type { ExpenseInvoiceStatus } from '../../types/erp';
import {
  EXPENSE_STATUS_LABELS, EXPENSE_STATUS_COLORS,
  EXPENSE_SOURCE_LABELS,
} from '../../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../../router/types';

export interface ExpenseGroup {
  group_key: string;
  group_label: string;
  attribution_type: string;
  case_code: string | null;
  project_code?: string;
  total_amount: number;
  count: number;
  categories: Array<{ category: string; count: number; amount: number }>;
}

interface Props {
  record: ExpenseGroup;
  navigate: NavigateFunction;
  canApprove: boolean;
}

const InvoiceSubTable: React.FC<Props> = ({ record, navigate, canApprove }) => {
  const { message } = App.useApp();
  const approveMutation = useApproveExpense();
  const rejectMutation = useRejectExpense();

  const queryParams: ExpenseInvoiceQuery = {
    ...(record.case_code ? { case_code: record.case_code } : {}),
    attribution_type: record.attribution_type,
    skip: 0,
    limit: 100,
  };

  const { data, isLoading } = useExpenses(queryParams);
  const items = data?.items ?? [];

  const handleApprove = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
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

  const subColumns: ColumnsType<ExpenseInvoice> = [
    { title: '發票號碼', dataIndex: 'inv_num', key: 'inv_num', width: 140 },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
    },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (status: ExpenseInvoiceStatus) => (
        <Tag color={EXPENSE_STATUS_COLORS[status]}>{EXPENSE_STATUS_LABELS[status]}</Tag>
      ),
    },
    { title: '分類', dataIndex: 'category', key: 'category', width: 110 },
    {
      title: '來源', dataIndex: 'source', key: 'source', width: 100,
      render: (v: string) => EXPENSE_SOURCE_LABELS[v as keyof typeof EXPENSE_SOURCE_LABELS] ?? v,
    },
    ...(canApprove ? [{
      title: '操作', key: 'action', width: 140,
      render: (_: unknown, row: ExpenseInvoice) => {
        if (row.status === 'verified' || row.status === 'rejected') return null;
        return (
          <Space size="small" onClick={(e) => e.stopPropagation()}>
            <Button
              type="link" size="small" icon={<CheckCircleOutlined />}
              style={{ color: '#52c41a' }}
              onClick={(e) => handleApprove(row.id, e)}
              loading={approveMutation.isPending}
            >
              通過
            </Button>
            <Popconfirm title="確定駁回？" onConfirm={() => handleReject(row.id)} okText="駁回" cancelText="取消">
              <Button type="link" size="small" icon={<CloseCircleOutlined />} danger>駁回</Button>
            </Popconfirm>
          </Space>
        );
      },
    }] as ColumnsType<ExpenseInvoice> : []),
  ];

  if (isLoading) {
    return <Spin style={{ display: 'block', padding: 24, textAlign: 'center' }} />;
  }

  return (
    <Table<ExpenseInvoice>
      columns={subColumns}
      dataSource={items}
      rowKey="id"
      size="small"
      pagination={false}
      onRow={(row) => ({
        onClick: () => navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(row.id))),
        style: { cursor: 'pointer' },
      })}
    />
  );
};

export default InvoiceSubTable;
