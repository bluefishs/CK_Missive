/**
 * 桃園查估派工 - 派工紀錄 Tab 的 Modal 元件
 *
 * 從 DispatchOrdersTab.tsx 提取的批次設定與匯入 Modal
 *
 * @version 1.0.0
 * @date 2026-03-25
 */

import React from 'react';
import {
  Typography,
  Button,
  Modal,
  Select,
  Row,
  Col,
  Upload,
  Form,
} from 'antd';
import {
  DownloadOutlined,
  FileExcelOutlined,
} from '@ant-design/icons';
import type { FormInstance } from 'antd';

const { Text } = Typography;

export interface BatchSetModalProps {
  visible: boolean;
  selectedCount: number;
  form: FormInstance;
  isPending: boolean;
  onOk: () => void;
  onCancel: () => void;
}

export const BatchSetModal: React.FC<BatchSetModalProps> = ({
  visible,
  selectedCount,
  form,
  isPending,
  onOk,
  onCancel,
}) => (
  <Modal
    title={`批量設定結案批次 (${selectedCount} 筆)`}
    open={visible}
    onOk={onOk}
    onCancel={onCancel}
    confirmLoading={isPending}
    okText="確定設定"
    cancelText="取消"
    width={400}
  >
    <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
      <Form.Item name="batch_no" label="結案批次">
        <Select
          placeholder="選擇結案批次（留空=清除）"
          allowClear
          options={[
            { value: 1, label: '第1批結案' },
            { value: 2, label: '第2批結案' },
            { value: 3, label: '第3批結案' },
            { value: 4, label: '第4批結案' },
            { value: 5, label: '第5批結案' },
          ]}
        />
      </Form.Item>
      <div style={{ color: '#666', fontSize: 12 }}>
        將為選中的 {selectedCount} 筆派工單統一設定結案批次。留空可清除已有設定。
      </div>
    </Form>
  </Modal>
);

export interface ImportDispatchModalProps {
  visible: boolean;
  isMobile: boolean;
  onCancel: () => void;
  onImport: (file: File) => void;
  onDownloadTemplate: () => void;
}

export const ImportDispatchModal: React.FC<ImportDispatchModalProps> = ({
  visible,
  isMobile,
  onCancel,
  onImport,
  onDownloadTemplate,
}) => (
  <Modal
    title="Excel 匯入派工紀錄"
    open={visible}
    onCancel={onCancel}
    footer={null}
    width={isMobile ? '95%' : 600}
  >
    <div style={{ marginBottom: 16 }}>
      <Button icon={<DownloadOutlined />} onClick={onDownloadTemplate}>
        下載匯入範本
      </Button>
      <span style={{ marginLeft: 8, color: '#666', fontSize: 12 }}>
        範本包含 13 個欄位：派工單號、機關函文號、工程名稱...等
      </span>
    </div>
    <Upload.Dragger
      accept=".xlsx,.xls"
      maxCount={1}
      beforeUpload={(file) => {
        onImport(file);
        return false;
      }}
    >
      <p className="ant-upload-drag-icon">
        <FileExcelOutlined style={{ fontSize: 48, color: '#52c41a' }} />
      </p>
      <p className="ant-upload-text">點擊或拖曳 Excel 檔案至此區域</p>
      <p className="ant-upload-hint">
        支援 .xlsx, .xls 格式，對應原始需求 17 欄位設計
      </p>
    </Upload.Dragger>
    <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
      <Text strong>匯入欄位說明：</Text>
      <div style={{ marginTop: 8, fontSize: 12 }}>
        <Row gutter={[8, 4]}>
          <Col span={8}>1. 派工單號 *</Col>
          <Col span={8}>2. 機關函文號</Col>
          <Col span={8}>3. 工程名稱/派工事項</Col>
          <Col span={8}>4. 作業類別</Col>
          <Col span={8}>5. 分案名稱/派工備註</Col>
          <Col span={8}>6. 履約期限</Col>
          <Col span={8}>7. 案件承辦</Col>
          <Col span={8}>8. 查估單位</Col>
          <Col span={8}>9. 乾坤函文號</Col>
          <Col span={8}>10. 雲端資料夾</Col>
          <Col span={8}>11. 專案資料夾</Col>
          <Col span={8}>12. 聯絡備註</Col>
        </Row>
      </div>
    </div>
  </Modal>
);
