/**
 * 核銷掃描/輸入面板 — 拆分自 ERPExpenseCreatePage
 *
 * 負責三種輸入方式的 UI 呈現：智慧掃描、手動填寫、財政部發票
 */
import React, { useRef } from 'react';
import {
  Button, Card, Upload, Spin, Alert,
  Descriptions, Tag, Divider, Space, Image, Steps, Typography,
} from 'antd';
import {
  CameraOutlined, PictureOutlined, CheckCircleOutlined, EditOutlined,
} from '@ant-design/icons';
import type { SmartScanResult } from '../../api/erp/expensesApi';

const { Text } = Typography;

interface ScanPanelProps {
  method: string;
  scanning: boolean;
  scanResult: SmartScanResult | null;
  previewUrl: string | null;
  isMobile: boolean;
  mofInvoices: Array<{ id: number; inv_num: string; date: string; amount: number; seller_ban?: string; status: string }>;
  onScan: (file: File) => void;
  onReset: () => void;
  onMofSelect: (inv: { inv_num: string; date: string; amount: number; seller_ban?: string }) => void;
  onGoToForm?: () => void;
}

const ExpenseScanPanel: React.FC<ScanPanelProps> = ({
  method, scanning, scanResult, previewUrl, isMobile,
  mofInvoices, onScan, onReset, onMofSelect, onGoToForm,
}) => {
  const cameraRef = useRef<HTMLInputElement>(null);

  return (
    <>
      {method === '智慧掃描' && (
        <>
          {!scanning && !scanResult && (
            <>
              <Button
                type="primary" icon={<CameraOutlined />} block size="large"
                onClick={() => cameraRef.current?.click()}
                style={{ height: 56, fontSize: 18, marginBottom: 12 }}
              >
                拍照掃描
              </Button>
              <input
                ref={cameraRef} type="file" accept="image/*" capture="environment"
                style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) onScan(f); if (cameraRef.current) cameraRef.current.value = ''; }}
              />
              <Upload.Dragger
                accept="image/jpeg,image/png,image/webp,image/heic"
                maxCount={1} showUploadList={false}
                beforeUpload={(file) => { onScan(file); return false; }}
              >
                <PictureOutlined style={{ fontSize: 32, color: '#8c8c8c' }} />
                <p style={{ color: '#8c8c8c', margin: '8px 0 0' }}>或選擇已有照片</p>
              </Upload.Dragger>
            </>
          )}

          {scanning && (
            <div style={{ textAlign: 'center', padding: '30px 0' }}>
              <Steps
                size="small" current={1}
                items={[
                  { title: '上傳', status: 'finish' },
                  { title: '辨識中', status: 'process' },
                  { title: '完成', status: 'wait' },
                ]}
                style={{ maxWidth: 300, margin: '0 auto 16px' }}
              />
              <Spin size="large" />
              {previewUrl && (
                <img src={previewUrl} alt="掃描中" style={{ maxWidth: 160, marginTop: 12, borderRadius: 8, opacity: 0.6 }} />
              )}
            </div>
          )}

          {scanResult && (
            <div>
              {previewUrl && (
                <div style={{ textAlign: 'center', marginBottom: 12 }}>
                  <Image src={previewUrl} alt="發票" width={isMobile ? 150 : 200} style={{ borderRadius: 8 }} />
                </div>
              )}
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="辨識方式">
                  <Tag color={scanResult.method === 'qr' ? 'green' : 'orange'}>
                    {scanResult.method === 'qr' ? 'QR Code' : scanResult.method === 'ocr' ? 'OCR' : scanResult.method}
                  </Tag>
                  <Tag>{Math.round(scanResult.confidence * 100)}%</Tag>
                </Descriptions.Item>
                {scanResult.inv_num && <Descriptions.Item label="發票號碼">{scanResult.inv_num}</Descriptions.Item>}
                {scanResult.amount != null && <Descriptions.Item label="金額">NT$ {scanResult.amount.toLocaleString()}</Descriptions.Item>}
              </Descriptions>
              {scanResult.items && scanResult.items.length > 0 && (
                <>
                  <Divider style={{ margin: '8px 0' }}>品項 ({scanResult.items.length})</Divider>
                  {scanResult.items.map((item, i) => (
                    <div key={i} style={{ fontSize: 12, color: '#666' }}>
                      {item.name} ×{item.qty} = ${item.amount}
                    </div>
                  ))}
                </>
              )}
              <Space style={{ width: '100%', marginTop: 12 }} direction={isMobile ? 'vertical' : 'horizontal'}>
                <Button block={isMobile} onClick={onReset}>重新掃描</Button>
                {isMobile && onGoToForm && (
                  <Button type="primary" block icon={<CheckCircleOutlined />} onClick={onGoToForm}>
                    確認，填寫表單
                  </Button>
                )}
              </Space>
            </div>
          )}
        </>
      )}

      {method === '手動填寫' && (
        isMobile && onGoToForm
          ? <Button type="primary" block size="large" icon={<EditOutlined />} onClick={onGoToForm} style={{ height: 56 }}>開始填寫</Button>
          : <Alert type="info" showIcon message="直接在右側表單填寫發票資訊" />
      )}

      {method === '財政部發票' && (
        <>
          {mofInvoices.length === 0 ? (
            <Alert type="warning" showIcon message="尚無待核銷的財政部發票" description="請先至 ERP Hub → 電子發票 同步後再選取。" />
          ) : (
            <div style={{ maxHeight: isMobile ? 300 : 350, overflow: 'auto' }}>
              {mofInvoices.map((inv) => (
                <Card
                  key={inv.id} size="small" hoverable
                  style={{ marginBottom: 8, cursor: 'pointer' }}
                  onClick={() => onMofSelect(inv)}
                >
                  <Space direction={isMobile ? 'vertical' : 'horizontal'} size={4}>
                    <Tag color="blue">{inv.inv_num}</Tag>
                    <Text type="secondary">{inv.date}</Text>
                    <Text strong>NT$ {Number(inv.amount).toLocaleString()}</Text>
                  </Space>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
};

export default ExpenseScanPanel;
