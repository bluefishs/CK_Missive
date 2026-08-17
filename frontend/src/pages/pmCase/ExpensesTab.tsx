/**
 * PM Case 費用/財務 Tab — 整合顯示 費用報銷 + ERP 請款 + ERP 開票
 *
 * 使用 /erp/expenses/case-finance API 一次取得案件所有財務紀錄。
 */
import React from 'react';
import { EXPENSE_STATUS_LABELS } from '../../types/erp';
import { Tag, Empty, Button, Typography, Row, Col, Statistic, Card } from 'antd';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import apiClient from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';
import type { ColumnsType } from 'antd/es/table';
// 2026-07-31 SSOT：型別由 types/erp 統一，對應後端 CaseFinanceResponse
// （原本兩個 ExpensesTab 各自宣告一份，後端改欄位不會有人發現）
import type { CaseFinanceRecord as FinanceRecord, CaseFinanceData } from '../../types/erp';

const { Text } = Typography;



interface Props {
  caseCode: string;
}

const TYPE_LABELS: Record<string, { label: string; color: string }> = {
  expense: { label: '費用報銷', color: 'orange' },
  billing: { label: '請款', color: 'blue' },
  invoice: { label: '開票', color: 'green' },
};

// 2026-08-17：費用狀態改由 types/erp.ts 的 SSOT 供應（原本自寫一份，
// 流程簡化拿掉「財務核准」時不會跟著改）。
// 帳款狀態（unpaid/partial/paid/issued）是**不同語意**，保留在這裡。
const STATUS_LABELS: Record<string, string> = {
  ...EXPENSE_STATUS_LABELS,
  unpaid: '未收款', partial: '部分收款', paid: '已收款',
  issued: '已開立',
};

const ExpensesTab: React.FC<Props> = ({ caseCode }) => {
  const navigate = useNavigate();

  const { data: financeData, isLoading } = useQuery<CaseFinanceData>({
    queryKey: ['case-finance', caseCode],
    queryFn: async () => {
      const res = await apiClient.post<{ data: CaseFinanceData }>(
        ERP_ENDPOINTS.EXPENSES_CASE_FINANCE,
        { case_code: caseCode },
      );
      return res.data;
    },
    enabled: !!caseCode,
  });

  const records = financeData?.records ?? [];
  const summary = financeData?.summary;

  const columns: ColumnsType<FinanceRecord> = [
    {
      title: '類型', dataIndex: 'type', key: 'type', width: 100,
      render: (v: string) => {
        const info = TYPE_LABELS[v] ?? { label: v, color: 'default' };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
      filters: [
        { text: '費用報銷', value: 'expense' },
        { text: '請款', value: 'billing' },
        { text: '開票', value: 'invoice' },
      ],
      onFilter: (value, record) => record.type === value,
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '說明', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '金額', dataIndex: 'amount', key: 'amount', width: 130, align: 'right',
      render: (v: number) => `NT$ ${Number(v).toLocaleString()}`,
    },
    { title: '分類', dataIndex: 'category', key: 'category', width: 100 },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string) => <Tag>{STATUS_LABELS[v] ?? v}</Tag>,
    },
  ];

  // 2026-07-30（owner「費用核銷 已核准 但無法檢視該紀錄」）：
  // 此表原本只呈現數字、沒有任何鑽取入口 → 看得到卻點不進去。
  // 費用報銷類可直接開原始核銷紀錄；請款/開票暫無獨立詳情頁故不提供（避免死連結）。
  const onRow = (row: FinanceRecord) => ({
    onClick: () => {
      if (row.type === 'expense') {
        navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(row.id)));
      }
    },
    style: { cursor: row.type === 'expense' ? 'pointer' : 'default' },
  });

  if (!isLoading && records.length === 0) {
    return (
      <Empty description="尚無財務紀錄">
        <Button
          type="primary" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}
        >
          新增核銷
        </Button>
      </Empty>
    );
  }

  return (
    <>
      {summary && (
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={8}><Card size="small"><Statistic title="費用報銷" value={summary.expense_total} precision={0} prefix="NT$" suffix={<Text type="secondary"> ({summary.expense_count} 筆)</Text>} /></Card></Col>
          <Col xs={12} sm={8}><Card size="small"><Statistic title="請款金額" value={summary.billing_total} precision={0} prefix="NT$" suffix={<Text type="secondary"> ({summary.billing_count} 筆)</Text>} styles={{ content: { color: '#1890ff' } }} /></Card></Col>
          <Col xs={12} sm={8}><Card size="small"><Statistic title="開票金額" value={summary.invoice_total} precision={0} prefix="NT$" suffix={<Text type="secondary"> ({summary.invoice_count} 筆)</Text>} styles={{ content: { color: '#52c41a' } }} /></Card></Col>
        </Row>
      )}
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary">共 {records.length} 筆財務紀錄</Text>
        <Button
          size="small" icon={<PlusOutlined />}
          onClick={() => navigate(`${ROUTES.ERP_EXPENSE_CREATE}?case_code=${caseCode}`)}
        >
          新增核銷
        </Button>
      </div>
      <EnhancedTable<FinanceRecord>
        columns={columns}
        dataSource={records}
        rowKey={(r) => `${r.type}-${r.id}`}
        loading={isLoading}
        size="small"
        pagination={false}
        onRow={onRow}
      />
    </>
  );
};

export default ExpensesTab;
