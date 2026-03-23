/**
 * QR Code 掃描建立 Modal
 */
import React from 'react';
import { Modal, Form, Input, Select, Alert, App } from 'antd';
import { ScanOutlined } from '@ant-design/icons';
import { EXPENSE_CATEGORY_OPTIONS } from '../../types/erp';
import { useQRScanExpense, useProjectsDropdown } from '../../hooks';
import QRCodeScanner from '../../components/common/QRCodeScanner';

interface Props {
  open: boolean;
  onClose: () => void;
}

const QRScanModal: React.FC<Props> = ({ open, onClose }) => {
  const { message: messageApi } = App.useApp();
  const [form] = Form.useForm();
  const qrScanMutation = useQRScanExpense();
  const { projects: projectOptions } = useProjectsDropdown();

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await qrScanMutation.mutateAsync(values);
      messageApi.success('QR 掃描建立成功');
      onClose();
      form.resetFields();
    } catch {
      messageApi.error('QR 掃描失敗');
    }
  };

  return (
    <Modal
      title={<><ScanOutlined /> QR Code 掃描建立</>}
      open={open}
      onOk={handleSubmit}
      onCancel={() => { onClose(); form.resetFields(); }}
      confirmLoading={qrScanMutation.isPending}
      width={480}
    >
      <Alert
        type="info"
        title="手機用戶可直接使用相機掃描電子發票 QR Code；桌機用戶請手動貼上。"
        style={{ marginBottom: 16 }}
        showIcon
      />
      <QRCodeScanner
        onScan={(text) => {
          form.setFieldsValue({ raw_qr: text });
          messageApi.success('QR Code 掃描成功，請確認後送出');
        }}
        width={280}
        height={280}
      />
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item name="raw_qr" label="QR Code 內容" rules={[{ required: true, message: '請掃描或貼上 QR Code' }]}>
          <Input.TextArea rows={3} placeholder="掃描後自動填入，或手動貼上電子發票 QR Code 內容" />
        </Form.Item>
        <Form.Item name="case_code" label="案號 (選填)">
          <Select
            placeholder="留空 = 一般營運支出"
            allowClear
            showSearch
            optionFilterProp="label"
            options={projectOptions?.filter(p => p.project_code).map(p => ({
              value: p.project_code,
              label: `${p.project_code} ${p.project_name}`,
            })) ?? []}
          />
        </Form.Item>
        <Form.Item name="category" label="費用分類">
          <Select placeholder="選擇分類" options={EXPENSE_CATEGORY_OPTIONS} allowClear />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default QRScanModal;
