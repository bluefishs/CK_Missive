/**
 * ERP 資產管理列表頁面
 *
 * 功能：資產列表 + 統計卡片 + 篩選 + 導航至詳情
 */
import React, { useState, useMemo } from 'react';
import {
  Alert, App, Card, Table, Button, Space, Tag, Input, Select, Typography,
  Statistic, Row, Col, Modal, Upload,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, SearchOutlined, DownloadOutlined,
  UploadOutlined, AuditOutlined, FileExcelOutlined,
} from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { useAssetList, useAssetStats, useExportAssets, useImportAssets, useBatchInventory, useExportInventory, useDownloadAssetTemplate } from '../hooks';
import type { Asset } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

// --- 常數定義 ---

const CATEGORY_LABELS: Record<string, string> = {
  equipment: '設備',
  vehicle: '車輛',
  instrument: '儀器',
  furniture: '家具',
  other: '其他',
};

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({ value, label }));

const STATUS_LABELS: Record<string, string> = {
  in_use: '使用中',
  maintenance: '維修中',
  idle: '閒置',
  disposed: '已報廢',
  lost: '遺失',
};

const STATUS_COLORS: Record<string, string> = {
  in_use: 'green',
  maintenance: 'orange',
  idle: 'blue',
  disposed: 'red',
  lost: 'volcano',
};

const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }));

interface AssetListParams {
  skip: number;
  limit: number;
  category?: string;
  status?: string;
  keyword?: string;
}

// --- 元件 ---

const ERPAssetListPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [params, setParams] = useState<AssetListParams>({ skip: 0, limit: 20 });
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const { data, isLoading, isError, refetch } = useAssetList(params);
  const { data: stats } = useAssetStats();
  const exportMutation = useExportAssets();
  const importMutation = useImportAssets();
  const batchInventoryMutation = useBatchInventory();
  const exportInventoryMutation = useExportInventory();
  const templateMutation = useDownloadAssetTemplate();

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;

  const handleBatchInventory = () => {
    let operatorValue = '';
    Modal.confirm({
      title: `批次盤點 (${selectedRowKeys.length} 項)`,
      content: (
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 8 }}>盤點人員：</div>
          <Input
            placeholder="請輸入盤點人員姓名"
            onChange={(e) => { operatorValue = e.target.value; }}
          />
        </div>
      ),
      okText: '確認盤點',
      cancelText: '取消',
      onOk: async () => {
        if (!operatorValue.trim()) {
          message.warning('請輸入盤點人員姓名');
          return Promise.reject();
        }
        await batchInventoryMutation.mutateAsync({
          asset_ids: selectedRowKeys.map(Number),
          operator: operatorValue.trim(),
        });
        message.success(`已完成 ${selectedRowKeys.length} 項資產盤點`);
        setSelectedRowKeys([]);
      },
    });
  };

  const columns: ColumnsType<Asset> = [
    {
      title: '資產編號',
      dataIndex: 'asset_code',
      key: 'asset_code',
      width: 130,
    },
    {
      title: '名稱',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 90,
      render: (val: string) => (
        <Tag>{CATEGORY_LABELS[val] ?? val}</Tag>
      ),
    },
    {
      title: '品牌/型號',
      key: 'brand_model',
      width: 160,
      render: (_: unknown, record: Asset) => {
        const parts = [record.brand, record.asset_model].filter(Boolean);
        return parts.length > 0 ? parts.join(' / ') : '-';
      },
    },
    {
      title: '購入金額',
      dataIndex: 'purchase_amount',
      key: 'purchase_amount',
      width: 120,
      align: 'right',
      render: (val?: number) => val != null ? val.toLocaleString() : '-',
    },
    {
      title: '目前價值',
      key: 'current_value',
      width: 120,
      align: 'right',
      render: (_: unknown, record: Asset) => {
        const val = record.current_value ?? record.purchase_amount;
        return val != null ? val.toLocaleString() : '-';
      },
    },
    {
      title: '存放位置',
      dataIndex: 'location',
      key: 'location',
      width: 140,
      ellipsis: true,
      render: (val?: string) => val ?? '-',
    },
    {
      title: '保管人',
      dataIndex: 'custodian',
      key: 'custodian',
      width: 100,
      render: (val?: string) => val ?? '-',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] ?? 'default'}>
          {STATUS_LABELS[status] ?? status}
        </Tag>
      ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* 統計卡片 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={3} style={{ margin: 0 }}>資產管理</Title>
          </Col>
          <Col>
            <Space>
              {selectedRowKeys.length > 0 && (
                <Button
                  icon={<AuditOutlined />}
                  onClick={handleBatchInventory}
                  loading={batchInventoryMutation.isPending}
                >
                  批次盤點 ({selectedRowKeys.length})
                </Button>
              )}
              <Button
                icon={<FileExcelOutlined />}
                onClick={() => exportInventoryMutation.mutate()}
                loading={exportInventoryMutation.isPending}
              >
                盤點報表
              </Button>
              <Button
                icon={<FileExcelOutlined />}
                onClick={() => templateMutation.mutate()}
                loading={templateMutation.isPending}
              >
                範本
              </Button>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={(file) => {
                  importMutation.mutateAsync(file).then((res) => {
                    const d = res?.data;
                    const parts = [`共 ${d?.total_rows ?? 0} 列`, `${d?.created ?? 0} 新增`, `${d?.updated ?? 0} 更新`];
                    if (d?.skipped) parts.push(`${d.skipped} 跳過`);
                    if (d?.errors?.length) parts.push(`${d.errors.length} 錯誤`);
                    message.success(`匯入完成: ${parts.join(', ')}`);
                    refetch();
                  }).catch(() => message.error('匯入失敗'));
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />} loading={importMutation.isPending}>
                  匯入
                </Button>
              </Upload>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => exportMutation.mutate()}
                loading={exportMutation.isPending}
              >
                匯出
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => navigate(ROUTES.ERP_ASSET_CREATE)}
              >
                新增資產
              </Button>
            </Space>
          </Col>
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={12} sm={4}>
            <Statistic title="總資產數" value={stats?.total_count ?? 0} />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic
              title="使用中"
              value={stats?.in_use ?? 0}
              styles={{ content: { color: '#52c41a' } }}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic
              title="維修中"
              value={stats?.maintenance ?? 0}
              styles={{ content: { color: '#fa8c16' } }}
            />
          </Col>
          <Col xs={12} sm={4}>
            <Statistic
              title="閒置"
              value={stats?.idle ?? 0}
              styles={{ content: { color: '#1890ff' } }}
            />
          </Col>
          <Col xs={12} sm={8}>
            <Statistic
              title="總價值"
              value={stats?.total_value ?? 0}
              precision={0}
              prefix="NT$"
            />
          </Col>
        </Row>
      </Card>

      {/* 列表 */}
      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜尋資產編號或名稱..."
            allowClear
            style={{ width: 220 }}
            onChange={(e) => {
              const val = e.target.value.trim() || undefined;
              setParams((p) => ({ ...p, keyword: val, skip: 0 }));
            }}
          />
          <Select
            placeholder="類別"
            allowClear
            style={{ width: 120 }}
            options={CATEGORY_OPTIONS}
            onChange={(v) => setParams((p) => ({ ...p, category: v, skip: 0 }))}
          />
          <Select
            placeholder="狀態"
            allowClear
            style={{ width: 120 }}
            options={STATUS_OPTIONS}
            onChange={(v) => setParams((p) => ({ ...p, status: v, skip: 0 }))}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            重新整理
          </Button>
        </Space>

        {isError && <Alert type="error" message="資產資料載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

        <Table<Asset>
          columns={columns}
          dataSource={items}
          rowKey="id"
          loading={isLoading}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
          }}
          pagination={{
            current: Math.floor((params.skip ?? 0) / (params.limit ?? 20)) + 1,
            pageSize: params.limit ?? 20,
            total,
            onChange: (page, pageSize) =>
              setParams((p) => ({ ...p, skip: (page - 1) * pageSize, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (t, range) => `第 ${range[0]}-${range[1]} 項，共 ${t} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(`${ROUTES.ERP_ASSETS}/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1200 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPAssetListPage;
