/**
 * 核銷匯入 Modal — 參照公文匯入介面設計
 *
 * 流程：上傳 Excel → 預覽結果 → 確認匯入
 * 內建範本下載按鈕
 *
 * @version 1.0.0
 */
import React, { useState } from 'react';
import {
  Modal, Upload, Button, Alert, Space, Progress, Typography,
  Descriptions, Tag, App,
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, InfoCircleOutlined,
  CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons';
import { useImportExpenses, useDownloadExpenseTemplate } from '../../hooks';

const { Text } = Typography;
const { Dragger } = Upload;

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface ImportResult {
  created: number;
  skipped: number;
  total_rows?: number;
  total?: number;
  errors: Array<{ row: number; error: string }>;
}

const ExpenseImportModal: React.FC<Props> = ({ open, onClose, onSuccess }) => {
  const { message: messageApi } = App.useApp();
  const importMutation = useImportExpenses();
  const templateMutation = useDownloadExpenseTemplate();
  const [result, setResult] = useState<ImportResult | null>(null);

  const handleClose = () => {
    setResult(null);
    onClose();
  };

  const handleUpload = (file: File) => {
    setResult(null);
    importMutation.mutate(file, {
      onSuccess: (res) => {
        const d = (res as { data?: ImportResult })?.data;
        if (d) {
          setResult(d);
          if (d.created > 0) {
            messageApi.success(`核銷匯入完成: ${d.created} 筆新增`);
            onSuccess?.();
          }
        }
      },
      onError: () => messageApi.error('核銷匯入失敗'),
    });
  };

  return (
    <Modal
      title="核銷匯入"
      open={open}
      onCancel={handleClose}
      footer={result ? (
        <Space>
          <Button onClick={() => setResult(null)}>繼續匯入</Button>
          <Button type="primary" onClick={handleClose}>完成</Button>
        </Space>
      ) : null}
      width={600}
      destroyOnHidden
    >
      {/* 說明 + 範本下載 */}
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="核銷發票 Excel 匯入"
        description={
          <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
            <li>適用於批次匯入紙本發票或手動整理的核銷紀錄</li>
            <li>發票號碼為唯一識別，重複號碼自動跳過</li>
            <li>自動匹配賣方統編→廠商、案號→成案編號</li>
          </ul>
        }
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<DownloadOutlined />}
          onClick={() => templateMutation.mutate()}
          loading={templateMutation.isPending}
        >
          下載匯入範本
        </Button>
      </Space>

      {/* 上傳區 */}
      {!result && (
        <Dragger
          accept=".xlsx,.xls"
          showUploadList={false}
          beforeUpload={(file) => { handleUpload(file); return false; }}
          disabled={importMutation.isPending}
        >
          <div className="ant-upload-drag-icon">
            {importMutation.isPending ? (
              <Progress type="circle" percent={-1} size={48} />
            ) : (
              <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            )}
          </div>
          <p className="ant-upload-text">
            {importMutation.isPending ? '匯入中...' : '點擊或拖曳 Excel 檔案至此'}
          </p>
          <p className="ant-upload-hint">支援 .xlsx / .xls 格式</p>
        </Dragger>
      )}

      {/* 匯入結果 */}
      {result && (
        <div style={{ marginTop: 8 }}>
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            {result.created > 0 ? (
              <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
            ) : (
              <WarningOutlined style={{ fontSize: 48, color: '#faad14' }} />
            )}
          </div>

          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="總列數">{result.total_rows ?? result.total ?? 0}</Descriptions.Item>
            <Descriptions.Item label="新增">
              <Text strong style={{ color: '#52c41a' }}>{result.created}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="跳過 (重複)">
              <Text type="secondary">{result.skipped}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="錯誤">
              {result.errors.length > 0 ? (
                <Tag color="red">{result.errors.length}</Tag>
              ) : (
                <Tag color="green">0</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>

          {result.errors.length > 0 && (
            <Alert
              type="warning"
              style={{ marginTop: 12 }}
              message={`${result.errors.length} 筆錯誤`}
              description={
                <ul style={{ margin: '4px 0 0', paddingLeft: 20, maxHeight: 150, overflow: 'auto' }}>
                  {result.errors.map((e, i) => (
                    <li key={i}>第 {e.row} 行: {e.error}</li>
                  ))}
                </ul>
              }
            />
          )}
        </div>
      )}
    </Modal>
  );
};

export default ExpenseImportModal;
