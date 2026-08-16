/**
 * ERP Quotation「費用核銷」Tab — 只呈現，不操作
 *
 * 用 case_code 查詢 expense_invoices。
 *
 * 2026-08-04（owner：詳情頁應參照 /documents/:id 的整體設計）：
 * 移除原本的「操作」欄（每列 檢視/編輯/審核/駁回/刪除，一畫面 19 顆按鈕）。
 * 參照頁的 tab 內容只有資料，所有狀態變更都在 header —— 這裡改為
 * **點列進 /erp/expenses/:id**，操作在那一頁的 header 完成。
 * 搬移前已把該頁缺少的「刪除」補上，並把「編輯」條件由 pending 放寬為
 * pending/rejected，與原欄位一致，確保沒有任何入口消失。
 */
import React, { useState } from 'react';
import {
  Tag, Empty, Button, Typography, Row, Col,
} from 'antd';
import ClickableStatCard from '../../components/common/ClickableStatCard';
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

  // 2026-08-15：統計卡片改為可切換型別（owner 回報「動態統計卡片」缺漏）。
  //
  // 原本四張卡是核銷／請款／開票**三種型別**的數字，而表格只顯示核銷 ——
  // 卡片說「請款 5 筆」，列表卻一筆請款都沒有，看的人無從對應。
  // 讓卡片切換表格顯示的型別，數字與列表才是同一件事。
  const [typeFilter, setTypeFilter] = useState<'expense' | 'billing' | 'invoice'>('expense');
  const expenseRecords = (data?.records ?? []).filter(r => r.type === typeFilter);
  const summary = data?.summary;

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
  ];

  return (
    <>
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12} lg={6}>
          <ClickableStatCard title="核銷筆數" value={summary?.expense_count ?? 0}
            active={typeFilter === 'expense'} onClick={() => setTypeFilter('expense')} />
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <ClickableStatCard title="核銷總額" value={summary?.expense_total ?? 0}
            active={typeFilter === 'expense'} onClick={() => setTypeFilter('expense')} />
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <ClickableStatCard title="請款筆數" value={summary?.billing_count ?? 0} color="#1890ff"
            active={typeFilter === 'billing'} onClick={() => setTypeFilter('billing')} />
        </Col>
        <Col xs={12} sm={12} lg={6}>
          <ClickableStatCard title="開票筆數" value={summary?.invoice_count ?? 0} color="#52c41a"
            active={typeFilter === 'invoice'} onClick={() => setTypeFilter('invoice')} />
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
        <EnhancedTable<FinanceRecord>
          onRow={(row: FinanceRecord) => ({
            // 點整列即進核銷詳情。操作欄已移除，理論上列上不再有按鈕，
            // 但保留 target 判斷作為防護（日後若有人加回列內元件不會立刻壞掉）。
            onClick: (e: React.MouseEvent) => {
              const el = e.target as HTMLElement;
              if (el.closest('button') || el.closest('.ant-popover')) return;
              navigate(ROUTES.ERP_EXPENSE_DETAIL.replace(':id', String(row.id)));
            },
            style: { cursor: 'pointer' },
          })}
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
