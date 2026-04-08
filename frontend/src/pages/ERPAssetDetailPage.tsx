/**
 * ERP 資產詳情頁面 — 統一 DetailPageLayout 模板
 *
 * Tab: 資產資訊 / 行為紀錄 / 關聯發票
 *
 * @version 1.0.0
 */
import React, { useState } from 'react';
import {
  Descriptions, Tag, Button, Modal, Form, Input, InputNumber,
  Select, DatePicker, Card, Empty, App, Image,
} from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import {
  InfoCircleOutlined, HistoryOutlined, FileTextOutlined,
  PlusOutlined, EditOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { useAssetDetail, useAssetLogs, useCreateAssetLog, useAssetDetailFull, useCaseCodeMap } from '../hooks';
import type { AssetLog, AssetLogCreateRequest } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  in_use: { label: '使用中', color: 'green' },
  idle: { label: '閒置', color: 'default' },
  maintenance: { label: '維修中', color: 'orange' },
  disposed: { label: '已報廢', color: 'red' },
};

const CATEGORY_COLORS: Record<string, string> = {
  '電腦設備': 'blue', '辦公家具': 'gold', '量測儀器': 'purple',
  '交通工具': 'cyan', '軟體授權': 'geekblue', '其他': 'default',
};

const ACTION_LABELS: Record<string, string> = {
  purchase: '採購', repair: '維修', maintain: '保養',
  transfer: '調撥', dispose: '報廢', inspect: '盤點', other: '其他',
};

const ACTION_COLORS: Record<string, string> = {
  purchase: 'blue', repair: 'orange', maintain: 'green',
  transfer: 'purple', dispose: 'red', inspect: 'cyan', other: 'default',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ERPAssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const assetId = id ? Number(id) : null;
  const { message } = App.useApp();

  const { data: detailData, isLoading } = useAssetDetail(assetId);
  const { data: fullData } = useAssetDetailFull(assetId);
  const { data: logsData } = useAssetLogs(assetId);
  const { data: caseCodeMap } = useCaseCodeMap();
  const createLogMutation = useCreateAssetLog();

  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const asset = detailData ?? null;
  const logs = logsData?.items ?? [];

  // --- Create log handler ---
  const handleCreateLog = async () => {
    try {
      const values = await form.validateFields();
      const payload: AssetLogCreateRequest = {
        asset_id: assetId!,
        action: values.action,
        action_date: values.action_date.format('YYYY-MM-DD'),
        description: values.description,
        cost: values.cost,
        operator: values.operator,
        notes: values.notes,
      };
      await createLogMutation.mutateAsync(payload);
      message.success('紀錄新增成功');
      setModalOpen(false);
      form.resetFields();
    } catch {
      // validation or mutation error
    }
  };

  // --- Not found ---
  if (!asset && !isLoading) {
    return (
      <DetailPageLayout
        header={{ title: '找不到此資產', backPath: ROUTES.ERP_ASSETS }}
        tabs={[]} hasData={false}
      />
    );
  }

  const statusInfo = STATUS_MAP[asset?.status ?? ''] ?? { label: asset?.status ?? '-', color: 'default' };

  // === Tab 1: 資產資訊 ===
  const photoUrl = asset?.photo_path ? `/${asset.photo_path}` : null;

  const infoTab = (
    <>
      {photoUrl && (
        <div style={{ marginBottom: 16, textAlign: 'center' }}>
          <Image
            src={photoUrl}
            alt={asset?.name ?? '資產照片'}
            width={240}
            style={{ borderRadius: 8, objectFit: 'cover' }}
          />
        </div>
      )}
      <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
      <Descriptions.Item label="資產編號">{asset?.asset_code}</Descriptions.Item>
      <Descriptions.Item label="名稱">{asset?.name}</Descriptions.Item>
      <Descriptions.Item label="類別">
        <Tag color={CATEGORY_COLORS[asset?.category ?? ''] ?? 'default'}>{asset?.category}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="品牌">{asset?.brand ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="型號">{asset?.asset_model ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="序號">{asset?.serial_number ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="購入日期">{asset?.purchase_date ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="購入金額">
        {asset?.purchase_amount != null ? `NT$ ${asset.purchase_amount.toLocaleString()}` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="目前價值">
        {(asset?.current_value ?? asset?.purchase_amount) != null
          ? `NT$ ${(asset?.current_value ?? asset?.purchase_amount)!.toLocaleString()}`
          : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="折舊率">
        {asset?.depreciation_rate != null ? `${asset.depreciation_rate}%` : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="狀態">
        <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
      </Descriptions.Item>
      <Descriptions.Item label="存放位置">{asset?.location ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="保管人">{asset?.custodian ?? '-'}</Descriptions.Item>
      <Descriptions.Item label="成案編號">
        {asset?.case_code
          ? (caseCodeMap?.[asset.case_code] || asset.case_code)
          : '-'}
      </Descriptions.Item>
      <Descriptions.Item label="備註" span={2}>{asset?.notes ?? '-'}</Descriptions.Item>
    </Descriptions>
    </>
  );

  // === Tab 2: 行為紀錄 ===
  const logColumns: ColumnsType<AssetLog> = [
    {
      title: '日期', dataIndex: 'action_date', key: 'action_date', width: 110,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-',
    },
    {
      title: '行為類型', dataIndex: 'action', key: 'action', width: 90,
      render: (v: string) => (
        <Tag color={ACTION_COLORS[v] ?? 'default'}>{ACTION_LABELS[v] ?? v}</Tag>
      ),
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '費用', dataIndex: 'cost', key: 'cost', width: 110, align: 'right' as const,
      render: (v: number) => v ? `NT$ ${v.toLocaleString()}` : '-',
    },
    { title: '操作人', dataIndex: 'operator', key: 'operator', width: 100 },
    {
      title: '位置變更', key: 'location_change', width: 160,
      render: (_: unknown, r: AssetLog) =>
        r.from_location || r.to_location
          ? `${r.from_location ?? '?'} → ${r.to_location ?? '?'}`
          : '-',
    },
    { title: '備註', dataIndex: 'notes', key: 'notes', width: 140, ellipsis: true },
  ];

  const logsTab = (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新增紀錄
        </Button>
      </div>
      <EnhancedTable<AssetLog>
        rowKey="id"
        columns={logColumns}
        dataSource={logs}
        size="small"
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
      />
    </>
  );

  // === Tab 3: 關聯發票 + 案件報價 ===
  const invoice = fullData?.invoice ?? null;
  const caseQuotation = fullData?.case_quotation ?? null;

  const invoiceTab = (
    <>
      {invoice ? (
        <Card size="small" title="關聯發票" style={{ marginBottom: 16 }}>
          <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="發票號碼">{invoice.inv_num}</Descriptions.Item>
            <Descriptions.Item label="日期">{invoice.date ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="金額">NT$ {Number(invoice.amount).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag>{invoice.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="賣方統編">{invoice.seller_ban ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="類別">{invoice.category ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="來源">{invoice.source}</Descriptions.Item>
          </Descriptions>
        </Card>
      ) : (
        <Card size="small" title="關聯發票" style={{ marginBottom: 16 }}>
          <Empty description="尚未關聯發票" />
        </Card>
      )}
      {caseQuotation ? (
        <Card size="small" title="所屬案件報價">
          <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
            <Descriptions.Item label="成案編號">{caseCodeMap?.[caseQuotation.case_code] || caseQuotation.case_code}</Descriptions.Item>
            <Descriptions.Item label="案件名稱">{caseQuotation.case_name ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="合約總價">NT$ {Number(caseQuotation.total_price).toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag>{caseQuotation.status}</Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      ) : asset?.case_code ? (
        <Card size="small" title="所屬案件報價">
          <Empty description={`案件 ${asset.case_code} 尚無報價記錄`} />
        </Card>
      ) : null}
    </>
  );

  // === Tabs ===
  const tabs = [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '資產資訊' }, infoTab),
    createTabItem('logs', { icon: <HistoryOutlined />, text: '行為紀錄', count: logs.length }, logsTab),
    createTabItem('invoice', { icon: <FileTextOutlined />, text: '關聯發票' }, invoiceTab),
  ];

  return (
    <DetailPageLayout
      header={{
        title: asset?.name ?? '資產詳情',
        subtitle: asset?.asset_code,
        tags: [{ text: statusInfo.label, color: statusInfo.color }],
        backPath: ROUTES.ERP_ASSETS,
        extra: (
          <Button
            type="primary"
            icon={<EditOutlined />}
            onClick={() => navigate(ROUTES.ERP_ASSET_EDIT.replace(':id', String(assetId)))}
          >
            編輯
          </Button>
        ),
      }}
      tabs={tabs}
      loading={isLoading}
      hasData={!!asset}
    >
      {/* 新增紀錄 Modal */}
      <Modal
        title="新增行為紀錄"
        open={modalOpen}
        onOk={handleCreateLog}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        confirmLoading={createLogMutation.isPending}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" preserve={false}>
          <Form.Item name="action" label="行為類型" rules={[{ required: true, message: '請選擇行為類型' }]}>
            <Select placeholder="請選擇">
              {Object.entries(ACTION_LABELS).map(([k, v]) => (
                <Select.Option key={k} value={k}>{v}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="action_date" label="日期" rules={[{ required: true, message: '請選擇日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="cost" label="費用">
            <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" />
          </Form.Item>
          <Form.Item name="operator" label="操作人">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </DetailPageLayout>
  );
};

export default ERPAssetDetailPage;
