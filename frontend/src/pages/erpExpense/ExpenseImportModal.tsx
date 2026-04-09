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
  Descriptions, Tag, App, Segmented, Input,
} from 'antd';
import {
  UploadOutlined, DownloadOutlined, InfoCircleOutlined,
  CheckCircleOutlined, WarningOutlined, CopyOutlined,
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
  batch_id?: string;
  errors: Array<{ row: number; error: string }>;
  warnings?: Array<{ row: number; warning: string }>;
}

const ExpenseImportModal: React.FC<Props> = ({ open, onClose, onSuccess }) => {
  const { message: messageApi } = App.useApp();
  const importMutation = useImportExpenses();
  const templateMutation = useDownloadExpenseTemplate();
  const [result, setResult] = useState<ImportResult | null>(null);
  const [mode, setMode] = useState<'excel' | 'paste'>('excel');
  const [pasteText, setPasteText] = useState('');

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
      {/* 模式切換 */}
      <Segmented block value={mode} onChange={(v) => { setMode(v as 'excel' | 'paste'); setResult(null); }}
        options={[
          { value: 'excel', icon: <UploadOutlined />, label: 'Excel 上傳' },
          { value: 'paste', icon: <CopyOutlined />, label: '快速貼上' },
        ]}
        style={{ marginBottom: 12 }}
      />

      {mode === 'excel' && (
        <>
          <Space style={{ marginBottom: 12 }}>
            <Button icon={<DownloadOutlined />} onClick={() => templateMutation.mutate()} loading={templateMutation.isPending} size="small">
              下載範本
            </Button>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>只填前 3 欄 (發票號/日期/金額) 即可匯入</Typography.Text>
          </Space>
          {!result && (
            <Dragger accept=".xlsx,.xls" showUploadList={false}
              beforeUpload={(file) => { handleUpload(file); return false; }}
              disabled={importMutation.isPending}>
              <div className="ant-upload-drag-icon">
                {importMutation.isPending ? <Progress type="circle" percent={-1} size={48} /> : <UploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />}
              </div>
              <p className="ant-upload-text">{importMutation.isPending ? '匯入中...' : '點擊或拖曳 Excel'}</p>
            </Dragger>
          )}
        </>
      )}

      {mode === 'paste' && !result && (
        <>
          <Alert type="info" showIcon icon={<InfoCircleOutlined />} style={{ marginBottom: 8 }}
            message="每行一筆，Tab 或逗號分隔：發票號碼、日期、金額、案件代碼(選填)"
          />
          <Input.TextArea
            rows={6} value={pasteText} onChange={(e) => setPasteText(e.target.value)}
            placeholder={'AB12345678\t2025-06-15\t5000\tB114-B001\nCD87654321\t2025-06-16\t3200'}
            style={{ fontFamily: 'monospace', fontSize: 13 }}
          />
          <Button type="primary" block style={{ marginTop: 8 }}
            disabled={!pasteText.trim()} loading={importMutation.isPending}
            onClick={() => {
              // 將貼上文字轉為 CSV → blob → 讓後端 Excel 解析
              const lines = pasteText.trim().split('\n').filter(Boolean);
              // 將貼上的文字轉為 XLSX 給後端解析
              import('xlsx').then(XLSX => {
                const ws = XLSX.utils.aoa_to_sheet(
                  [['發票號碼', '日期', '金額', '案件代碼'],
                   ...lines.map(l => l.split(/[\t,]/).map(c => c.trim()))]
                );
                const wb = XLSX.utils.book_new();
                XLSX.utils.book_append_sheet(wb, ws, '費用報銷匯入');
                const buf = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
                const file = new File([buf], 'paste_import.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
                handleUpload(file);
              }).catch(() => {
                messageApi.error('需要 xlsx 套件支援貼上匯入');
              });
            }}>
            匯入 {pasteText.trim().split('\n').filter(Boolean).length} 筆
          </Button>
        </>
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

          {result.batch_id && (
            <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 11 }}>
              批次編號: {result.batch_id}
            </Text>
          )}

          {(result.warnings?.length ?? 0) > 0 && (
            <Alert type="info" style={{ marginTop: 12 }}
              message={`${result.warnings!.length} 筆案號警告`}
              description={
                <ul style={{ margin: '4px 0 0', paddingLeft: 20, maxHeight: 100, overflow: 'auto' }}>
                  {result.warnings!.map((w, i) => <li key={i}>第 {w.row} 行: {w.warning}</li>)}
                </ul>
              }
            />
          )}

          {result.errors.length > 0 && (
            <Alert type="warning" style={{ marginTop: 12 }}
              message={`${result.errors.length} 筆錯誤`}
              description={
                <ul style={{ margin: '4px 0 0', paddingLeft: 20, maxHeight: 150, overflow: 'auto' }}>
                  {result.errors.map((e, i) => <li key={i}>第 {e.row} 行: {e.error}</li>)}
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
