/**
 * 報價紀錄 Tab — PM 案件的線上報價單 ＋ 上傳的報價單檔案
 *
 * 2026-08-26 owner：「線上報價單檢視及編輯維護 `/pm/cases` 尚未看到對應 UI 或功能」
 *
 * 查證屬實，而且比描述的更具體：**253 個 PM 案件裡有 229 個有線上報價單，
 * 而這一頁完全沒有列出它們**。案件詳情頁只有「新增報價」導出去的按鈕
 * （08-20 加的），**沒有回來的路** —— 使用者開了報價單之後，回到案件頁就找不到它。
 *
 * 而原本這一頁顯示的是 `AttachmentPanel`（**上傳的檔案**，PDF／掃描件），
 * 與「線上報價單記錄」是兩回事。兩者都要，但**線上的那份才是主體**：
 * 它有金額、狀態、承辦同仁，而檔案只是佐證。
 *
 * ⚠️ 依「詳情頁 tab 只呈現不操作」規範：這裡只列出與導向，
 * 編輯一律進 `ERPQuotationDetailPage`。
 *
 * @version 4.0.0 — 加線上報價單清單（原 3.0.0 只有附件面板）
 */
import { Card, Table, Tag, Typography, Empty, Space, Spin, Alert } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AttachmentPanel } from '../../components/common/AttachmentPanel';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { ROUTES } from '../../router/types';
import { defaultQueryOptions } from '../../config/queryConfig';
import type { ERPQuotation } from '../../types/erp';

const { Text } = Typography;

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  draft: { text: '草稿', color: 'default' },
  submitted: { text: '已送出', color: 'processing' },
  confirmed: { text: '已確認', color: 'success' },
  not_won: { text: '未得標', color: 'error' },
};

interface QuotationRecordsTabProps {
  caseCode: string;
  isEditing?: boolean;
}

export default function QuotationRecordsTab({ caseCode, isEditing = false }: QuotationRecordsTabProps) {
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['erp-quotations', 'by-case', caseCode],
    queryFn: async () => {
      const r = await apiClient.post<{ items?: ERPQuotation[]; total?: number }>(
        ERP_ENDPOINTS.QUOTATIONS_LIST, { case_code: caseCode, page: 1, limit: 50 },
      );
      return r;
    },
    enabled: !!caseCode,
    ...defaultQueryOptions.list,
  });

  const quotations = data?.items ?? [];

  const columns = [
    {
      title: '報價單號', dataIndex: 'quotation_no', width: 150,
      render: (v: string, r: ERPQuotation) => (
        <a onClick={() => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(r.id)))}>
          {v || `#${r.id}`}
        </a>
      ),
    },
    {
      title: '金額', dataIndex: 'total_price', width: 130, align: 'right' as const,
      render: (v?: number | string) =>
        v == null ? <Text type="secondary">—</Text> : `$${Number(v).toLocaleString()}`,
    },
    {
      title: '狀態', dataIndex: 'status', width: 100,
      render: (v: string) => {
        const s = STATUS_LABEL[v] ?? { text: v || '—', color: 'default' };
        return <Tag color={s.color}>{s.text}</Tag>;
      },
    },
    {
      // owner 2026-08-26：「填寫報價單就要對應同仁，不然後續如何管理與對應維護」
      // 來源是 `project_user_assignments`（以 case_code 關聯）—— 與本頁
      // 「承辦同仁」分頁看到的**同一份**，不另建一套。
      title: '承辦同仁', dataIndex: 'staff_name', width: 130,
      render: (v?: string) => v || <Text type="secondary">未指定</Text>,
    },
    {
      title: '填報者', dataIndex: 'created_by_name', width: 110,
      render: (v?: string) => v || <Text type="secondary">—</Text>,
    },
  ];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        size="small"
        title={<Space><FileTextOutlined />線上報價單</Space>}
        extra={<Text type="secondary">{quotations.length} 張</Text>}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
        ) : isError ? (
          // ⚠️「載不到」與「沒有報價單」必須看得出差別 —— 空表格會被讀成
          // 「這個案子還沒報價」，那與「查詢失敗」意思完全相反（08-20 的判準）。
          <Alert type="warning" showIcon message="報價單清單載入失敗，請重新整理" />
        ) : quotations.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="尚無線上報價單 —— 可用上方「新增報價」建立"
          />
        ) : (
          <Table
            rowKey="id"
            size="small"
            columns={columns}
            dataSource={quotations}
            pagination={false}
            scroll={{ x: 620 }}
          />
        )}
      </Card>

      {/* 上傳的報價單檔案（PDF／掃描件／客戶回簽）—— 與線上報價單是兩回事，
          兩者都保留：線上的有金額與狀態，檔案是佐證。 */}
      <AttachmentPanel
        caseCode={caseCode}
        isEditing={isEditing}
        title="報價單檔案"
        uploadTitle="上傳報價單檔案"
        emptyText={isEditing ? '尚無檔案，可上傳報價單 PDF 或客戶回簽' : '尚無檔案'}
        showDocType
      />
    </Space>
  );
}
