/**
 * 邀標/報價管理列表頁面
 *
 * 建案階段：邀標登錄、報價上傳、決標追蹤。
 * 成案後自動帶入 Contract Cases 與 ERP Quotations。
 *
 * @version 3.0.0 — 重新定位為邀標/報價專區
 */
import React, { useState, useMemo } from 'react';
import { Typography, Input, Button, Flex, Row, Col, Tag, Select, Upload, App, Space } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, FileSearchOutlined, CheckCircleOutlined, DollarOutlined, SendOutlined, DownloadOutlined, UploadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCases, usePMCaseSummary, useAuthGuard, useResponsive } from '../hooks';
import { ClickableStatCard } from '../components/common';
import { PM_CATEGORY_LABELS } from '../types/api';
import type { PMCase } from '../types/api';
import { PM_CASE_STATUS_LABELS } from '../types/pm';
import type { PMCaseStatus } from '../types/pm';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { apiClient } from '../api/client';
import { PM_ENDPOINTS } from '../api/endpoints';

const { Title } = Typography;
const { Search } = Input;

export const PMCaseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { isMobile } = useResponsive();
  const { message } = App.useApp();

  const [searchText, setSearchText] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>(new Date().getFullYear());
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  // 匯出 XLSX
  const handleExportXlsx = async () => {
    try {
      message.loading({ content: '匯出中...', key: 'export' });
// ⚠️ 這裡原本用**裸 `fetch`** 打 `/api/...`：不經 apiClient 就不會帶上
      // 認證 cookie 與 X-CSRF-Token，於是這個功能一直是壞的
      // （owner 2026-08-19 回報「匯出 XLS 無法運作」）。
      // 同型掃全共 4 處：PM 案件匯出/匯入、里程碑匯出/匯入 —— 一併改用 apiClient。
      // 路徑也改用端點常數，不再硬編字串。
      const res = await apiClient.post(PM_ENDPOINTS.EXPORT_XLSX, {}, { responseType: 'blob' });
      const raw = res as unknown as { data?: Blob } | Blob;
      const blob = raw instanceof Blob ? raw : (raw.data as Blob);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pm_cases_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      message.success({ content: '匯出成功', key: 'export' });
    } catch {
      message.error({ content: '匯出失敗', key: 'export' });
    }
  };

  // 匯入 XLSX 修正 — 上傳到後端解析
  const handleImportXlsx = async (file: File) => {
    try {
      message.loading({ content: '匯入中...', key: 'import' });
      const formData = new FormData();
      formData.append('file', file);
      // 同上：裸 fetch 不帶認證，改走 apiClient
      // 匯入回應的形狀（後端 pm/cases/import-xlsx）
      type ImportResult = {
        success?: boolean; updated?: number; synced?: number; errors?: string[]; error?: string;
      };
      const res = await apiClient.post(PM_ENDPOINTS.IMPORT_XLSX, formData);
      const result = ((res as unknown as { data?: ImportResult })?.data
        ?? (res as unknown as ImportResult));

      if (result.success) {
        message.success({
          content: `匯入完成: 更新 ${result.updated} 筆, 同步 ${result.synced} 筆${result.errors?.length ? `, 錯誤 ${result.errors.length} 筆` : ''}`,
          key: 'import',
          duration: 5,
        });
        window.location.reload();
      } else {
        message.error({ content: result.error || '匯入失敗', key: 'import' });
      }
    } catch {
      message.error({ content: '匯入失敗，請確認 XLSX 格式正確', key: 'import' });
    }
    return false;
  };

  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    sort_by: 'year',
    sort_order: 'desc' as const,
    ...(searchText && { search: searchText }),
    ...(yearFilter !== undefined && { year: yearFilter }),
    ...(statusFilter && { status: statusFilter }),
    ...(categoryFilter && { category: categoryFilter }),
  }), [currentPage, searchText, yearFilter, statusFilter, categoryFilter]);

  const { data: casesData, isLoading, refetch } = usePMCases(queryParams);
  const { data: summary } = usePMCaseSummary({ year: yearFilter });

  // PaginatedResponse<PMCase> has .items and .pagination directly
  const cases = casesData?.items ?? [];
  const total = casesData?.pagination?.total ?? 0;

  const desktopColumns: ColumnsType<PMCase> = [
    {
      title: '案號',
      dataIndex: 'case_code',
      key: 'case_code',
      width: 140,
      render: (code: string) => <Typography.Text strong style={{ fontFamily: 'monospace', fontSize: 12 }}>{code}</Typography.Text>,
    },
    {
      title: '專案名稱',
      dataIndex: 'case_name',
      key: 'case_name',
      ellipsis: true,
    },
    {
      title: '委託單位',
      dataIndex: 'client_name',
      key: 'client_name',
      width: 150,
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '計畫類別',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (cat: string) => PM_CATEGORY_LABELS[cat] || cat || '-',
    },
    {
      title: '報價金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      width: 120,
      align: 'right' as const,
      render: (v: number) => v ? `NT$${v.toLocaleString()}` : '-',
    },
    {
      title: '承攬狀態',
      dataIndex: 'status',
      key: 'contract_status',
      width: 90,
      align: 'center' as const,
      filters: [
        { text: '評估中', value: 'planning' },
        { text: '已承攬', value: 'contracted' },
        { text: '已結案', value: 'closed' },
      ],
      onFilter: (value, record) => record.status === value,
      render: (status: string, record: PMCase) => {
        if (status === 'contracted') {
          // 2026-08-29（M3）：「已承攬未成案」與「已承攬已成案」在列表上
          // 原本無法區分 —— 而這個缺口存量 114 筆（91 待判讀＋23 可成案），
          // 使用者只能逐筆點進詳情頁看 project_code 有無。
          return record.project_code
            ? <Tag color="blue">已承攬</Tag>
            : <Tag color="gold">已承攬・未成案</Tag>;
        }
        if (status === 'closed') return <Tag color="success">已結案</Tag>;
        return <Tag color="default">評估中</Tag>;
      },
    },
    {
      title: '成案編號',
      dataIndex: 'project_code',
      key: 'project_code',
      width: 130,
      render: (code: string) => code
        ? <Typography.Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{code}</Typography.Text>
        : <Typography.Text type="secondary">-</Typography.Text>,
    },
  ];

  // Mobile: 案號、專案名稱、是否承攬
  const mobileColumns: ColumnsType<PMCase> = [
    desktopColumns[0]!, // 案號
    desktopColumns[1]!, // 專案名稱
    desktopColumns[5]!, // 是否承攬
  ];

  const columns = isMobile ? mobileColumns : desktopColumns;

  return (
    <ResponsiveContent>
      <Flex vertical gap={8} style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}><FileSearchOutlined style={{ marginRight: 8 }} />邀標/報價管理</Title>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportXlsx}
              >
                匯出 XLSX
              </Button>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={handleImportXlsx}
              >
                <Button icon={<UploadOutlined />}>匯入修正</Button>
              </Upload>
              {/* 2026-08-27：`projects:write` 不存在於任何地方（見 useAuthGuard 的 Permission 註解），
                  只有 superuser 看得到這個按鈕。後端 pm/cases 只有 require_auth ⇒
                  改成 projects:edit 不放寬任何 API 存取，只是停止隱藏入口。 */}
              {/* 2026-08-28 owner：「新增報價在右上角獨立按鈕，非在各案件內」＋
                  「create 仍是 mis 非 xls 樣板」——
                  範本式一頁建單（案首＋明細＋合計）：送出時自動建立邀標案件
                  （委託單位寫進 pm_cases.client_name，輸出文件才有客戶抬頭），
                  完成後直達該案件的報價單分頁（明細編輯＋輸出 PDF 都在那裡）。 */}
              {hasPermission('projects:edit') && (
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => navigate(ROUTES.ERP_QUOTATION_CREATE)}
                >
                  新增報價
                </Button>
              )}
              {hasPermission('projects:edit') && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => navigate(ROUTES.PM_CASE_CREATE)}
                >
                  新增邀標
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {summary && (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="邀標總數"
                value={summary.total_cases}
                icon={<FileSearchOutlined />}
                active={!statusFilter}
                onClick={() => { setStatusFilter(undefined); setCurrentPage(1); }}
              />
            </Col>
            {/* 2026-08-19：標籤與取值原本對不起來 ——
                「報價中」讀的是 `in_progress`，而 PM 案件根本沒有這個狀態
                （SSOT 只有 planning/contracted/closed）⇒ 這張卡恆為 0；
                「已成案」讀的是 `closed`（已結案），於是後端回的
                `contracted: 2` 完全沒有地方顯示，畫面說「已成案 1」
                而列表列著 2 筆「已承攬」。改為直接由 SSOT 推導，
                標籤、取值、列表用同一組詞彙。 */}
            {(['contracted', 'closed'] as PMCaseStatus[]).map((st) => (
              <Col xs={12} sm={6} key={st}>
                <ClickableStatCard
                  title={PM_CASE_STATUS_LABELS[st]}
                  value={summary.by_status?.[st] ?? 0}
                  icon={st === 'contracted' ? <SendOutlined /> : <CheckCircleOutlined />}
                  color={st === 'contracted' ? '#1890ff' : '#52c41a'}
                  active={statusFilter === st}
                  onClick={() => {
                    setStatusFilter(statusFilter === st ? undefined : st);
                    setCurrentPage(1);
                  }}
                />
              </Col>
            ))}
            <Col xs={12} sm={6}>
              {/* 金額不是狀態，點它沒有對應的篩選語意 —— 不給 onClick，
                  元件就不會 hoverable（原本點了只會變色，列表不動）。 */}
              <ClickableStatCard
                title="報價總額"
                value={`NT$${Number(summary.total_contract_amount ?? 0).toLocaleString()}`}
                icon={<DollarOutlined />}
              />
            </Col>
          </Row>
        )}

        <Row gutter={[8, 8]}>
          <Col xs={24} sm={8}>
            <Search
              placeholder="搜尋案號/案名..."
              allowClear
              onSearch={(v) => {
                setSearchText(v);
                setCurrentPage(1);
              }}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="年度"
              allowClear
              value={yearFilter}
              onChange={(v) => {
                setYearFilter(v);
                setCurrentPage(1);
              }}
              options={Array.from({ length: 5 }, (_, i) => {
                const y = new Date().getFullYear() - i;
                return { value: y, label: String(y) };
              })}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="承攬狀態"
              allowClear
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setCurrentPage(1);
              }}
              options={[
                { value: 'planning', label: '評估中' },
                { value: 'contracted', label: '已承攬' },
                { value: 'closed', label: '已結案' },
              ]}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="類別"
              allowClear
              value={categoryFilter}
              onChange={(v) => {
                setCategoryFilter(v);
                setCurrentPage(1);
              }}
              options={Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({
                value: k,
                label: v,
              }))}
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
          </Col>
        </Row>

        <EnhancedTable<PMCase>
          dataSource={cases}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: setCurrentPage,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/pm/cases/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: 800 }}
        />
      </Flex>
    </ResponsiveContent>
  );
};

export default PMCaseListPage;
