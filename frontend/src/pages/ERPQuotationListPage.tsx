/**
 * ERP 報價/成本管理列表頁面
 */
import React, { useState } from 'react';
import { Card, Button, Space, Input, Typography, Row, Col, Popconfirm, Alert, App, Upload } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, DownloadOutlined, EditOutlined, UploadOutlined, FileExcelOutlined, DollarOutlined, FundOutlined, BankOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { erpQuotationsApi } from '../api/erp';
import { useNavigate } from 'react-router-dom';
import { useERPQuotations, useERPProfitSummary, useDeleteERPQuotation, useAuthGuard } from '../hooks';
import type { ERPQuotation, ERPQuotationListParams } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';

const { Title } = Typography;

export const ERPQuotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('projects:write');
  const [statFilter, setStatFilter] = useState<string | null>(null);
  const [params, setParams] = useState<ERPQuotationListParams>({ page: 1, limit: 20, sort_by: 'year', sort_order: 'desc' });
  const { data, isLoading, isError, refetch } = useERPQuotations(params);
  const { data: profitSummary } = useERPProfitSummary();
  const deleteMutation = useDeleteERPQuotation();

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('報價已刪除');
    } catch {
      message.error('刪除失敗');
    }
  };

  // 前端過濾：僅顯示已承攬

  const columns: ColumnsType<ERPQuotation> = [
    { title: '案號', key: 'project_code', width: 160, render: (_: unknown, r: ERPQuotation) => r.project_code || r.case_code },
    {
      title: '案名',
      dataIndex: 'case_name',
      key: 'case_name',
      ellipsis: true,
      render: (text: string | null) => <strong>{text ?? '-'}</strong>,
    },
    { title: '年度', dataIndex: 'year', key: 'year', width: 80, align: 'center', render: (v?: number) => v ? (v < 1911 ? v + 1911 : v) : '-' },
    {
      title: '總價',
      dataIndex: 'total_price',
      key: 'total_price',
      width: 120,
      align: 'right',
      render: (v: string | null) => v ? Number(v).toLocaleString() : '-',
    },
    {
      title: '毛利',
      dataIndex: 'gross_profit',
      key: 'gross_profit',
      width: 120,
      align: 'right',
      render: (v: string) => {
        const num = Number(v);
        return <span style={{ color: num >= 0 ? '#52c41a' : '#ff4d4f' }}>{num.toLocaleString()}</span>;
      },
    },
    {
      title: '毛利率',
      dataIndex: 'gross_margin',
      key: 'gross_margin',
      width: 90,
      align: 'right',
      render: (v: string | null) => v ? `${Number(v).toFixed(1)}%` : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: ERPQuotation) => (
        <Space>
          <Button type="link" size="small" onClick={(e) => { e.stopPropagation(); navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.id))); }}>
            詳情
          </Button>
          {canWrite && (
            <>
              <Button type="link" size="small" icon={<EditOutlined />} onClick={(e) => { e.stopPropagation(); navigate(ROUTES.ERP_QUOTATION_EDIT.replace(':id', String(record.id))); }} />
              <Popconfirm title="確定刪除此報價？" onConfirm={() => handleDelete(record.id)} okText="確定" cancelText="取消">
                <Button type="link" size="small" danger onClick={(e) => e.stopPropagation()}>刪除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  const grossProfit = profitSummary ? Number(profitSummary.total_gross_profit) : 0;

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>財務管理 (ERP)</Title></Col>
          <Col>
            {canWrite && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(ROUTES.ERP_QUOTATION_CREATE)}>
                新增報價
              </Button>
            )}
          </Col>
        </Row>
        {profitSummary && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="營收總額"
                value={Number(profitSummary.total_revenue).toLocaleString()}
                icon={<DollarOutlined />}
                color="#1890ff"
                active={statFilter === 'revenue'}
                onClick={() => setStatFilter(statFilter === 'revenue' ? null : 'revenue')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="成本總額"
                value={Number(profitSummary.total_cost).toLocaleString()}
                icon={<BankOutlined />}
                color="#faad14"
                active={statFilter === 'cost'}
                onClick={() => setStatFilter(statFilter === 'cost' ? null : 'cost')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="毛利"
                value={grossProfit.toLocaleString()}
                icon={<FundOutlined />}
                color={grossProfit >= 0 ? '#3f8600' : '#cf1322'}
                active={statFilter === 'profit'}
                onClick={() => setStatFilter(statFilter === 'profit' ? null : 'profit')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="應收未收"
                value={Number(profitSummary.total_outstanding).toLocaleString()}
                icon={<ExclamationCircleOutlined />}
                color="#ff4d4f"
                active={statFilter === 'outstanding'}
                onClick={() => setStatFilter(statFilter === 'outstanding' ? null : 'outstanding')}
              />
            </Col>
          </Row>
        )}
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜尋案號/案名"
            allowClear
            onSearch={(v) => setParams((p) => ({ ...p, search: v || undefined, page: 1 }))}
            style={{ width: 240 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={async () => {
              try {
                const blob = await erpQuotationsApi.exportExcel({ year: params.year });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'erp_quotations.xlsx';
                a.click();
                URL.revokeObjectURL(url);
                message.success('匯出成功');
              } catch { message.error('匯出失敗'); }
            }}
          >匯出 Excel</Button>
          {canWrite && (
            <>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    const result = await erpQuotationsApi.importExcel(file);
                    message.success(`匯入完成: 新增 ${result.created} 筆, 更新 ${result.updated} 筆`);
                    if (result.errors?.length) {
                      message.warning(`${result.errors.length} 筆匯入失敗`);
                    }
                    refetch();
                  } catch { message.error('匯入失敗'); }
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />}>匯入 Excel</Button>
              </Upload>
              <Button
                icon={<DownloadOutlined />}
                onClick={async () => {
                  try {
                    const blob = await erpQuotationsApi.downloadTemplate();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'erp_quotation_template.xlsx';
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch { message.error('下載範本失敗'); }
                }}
              >下載範本</Button>
            </>
          )}
        </Space>

        <EnhancedTable<ERPQuotation>
          columns={columns}
          dataSource={data?.items ?? []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: params.page,
            pageSize: params.limit,
            total: data?.pagination?.total ?? 0,
            onChange: (page, pageSize) => setParams((p) => ({ ...p, page, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.id))),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPQuotationListPage;
