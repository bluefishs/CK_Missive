/**
 * 資產行為紀錄填報頁
 *
 * 2026-08-16 owner：「erp財務 與其子項目 其表單仍操作非導覽模式」。
 * 原本是 `ERPAssetDetailPage` 裡的 `<Modal title="新增行為紀錄">`（6 個欄位），
 * 超過既有 Modal 豁免的「3-5 欄」門檻（`UI_DESIGN_STANDARDS` 2026-04-06 決策），
 * 且違反 CRUD=navigate 規約。
 */
import React from 'react';
import { Form, Input, Select, DatePicker, InputNumber, App } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { useCreateAssetLog, useAssetDetail } from '../hooks';
import { ASSET_ACTION_LABELS } from '../types/erp';
import type { AssetLogCreateRequest } from '../types/erp';

const ERPAssetLogFormPage: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const assetId = Number(id);
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const createLogMutation = useCreateAssetLog();
  const { data: asset } = useAssetDetail(assetId);

  const back = () => navigate(`/erp/assets/${assetId}`);

  const handleSubmit = async () => {
    const v = await form.validateFields();
    const payload: AssetLogCreateRequest = {
      asset_id: assetId,
      action: v.action,
      action_date: dayjs(v.action_date).format('YYYY-MM-DD'),
      description: v.description,
      cost: v.cost,
      operator: v.operator,
      notes: v.notes,
    };
    await createLogMutation.mutateAsync(payload);
    message.success('紀錄新增成功');
    back();
  };

  return (
    <ErpFormPageShell
      title={asset?.name ? `新增行為紀錄 — ${asset.name}` : '新增行為紀錄'}
      onBack={back}
      onSubmit={handleSubmit}
      submitting={createLogMutation.isPending}
      backText="返回資產"
    >
      <Form form={form} layout="vertical" initialValues={{ action_date: dayjs() }}>
        <Form.Item name="action" label="行為類型" rules={[{ required: true, message: '請選擇行為類型' }]}>
          <Select
            placeholder="請選擇"
            options={Object.entries(ASSET_ACTION_LABELS).map(([value, label]) => ({ value, label }))}
          />
        </Form.Item>
        <Form.Item name="action_date" label="日期" rules={[{ required: true, message: '請選擇日期' }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={2} maxLength={500} showCount />
        </Form.Item>
        <Form.Item name="cost" label="費用">
          <InputNumber<number>
            style={{ width: '100%' }}
            min={0}
            prefix="NT$"
            formatter={v => `${v ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={v => Number((v || '').replace(/,/g, ''))}
          />
        </Form.Item>
        <Form.Item name="operator" label="操作人">
          <Input />
        </Form.Item>
        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={2} maxLength={500} showCount />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ERPAssetLogFormPage;
