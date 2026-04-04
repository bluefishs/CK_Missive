/**
 * 智慧發票掃描 Modal — 支援批次連續掃描
 *
 * 參照雲端發票 App 體驗：
 * - 拍一張 → 自動辨識 (QR + OCR) → 建檔 → 繼續下一張
 * - 批次結果即時顯示累計筆數
 * - 支援電子發票 QR Code (Head + Detail 品項) + 傳統紙本 OCR
 *
 * @version 2.0.0 — 批次模式
 */
import React, { useState, useRef, useCallback } from 'react';
import {
  Modal, Upload, Button, Space, Tag, Alert,
  Spin, Typography, Divider, App, Badge, List,
} from 'antd';
import {
  CameraOutlined, ScanOutlined, PictureOutlined,
  CheckCircleOutlined, WarningOutlined, PlusOutlined,
} from '@ant-design/icons';
import type { SmartScanResult } from '../../api/erp/expensesApi';
import { expensesApi } from '../../api/erp';

const { Text } = Typography;

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface ScanRecord {
  file_name: string;
  result: SmartScanResult;
  preview_url: string;
}

const SmartScanModal: React.FC<Props> = ({ open, onClose, onSuccess }) => {
  const { message: messageApi } = App.useApp();
  const [scanning, setScanning] = useState(false);
  const [records, setRecords] = useState<ScanRecord[]>([]);
  const [currentPreview, setCurrentPreview] = useState<string | null>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    onClose();
    setRecords([]);
    setCurrentPreview(null);
    if (records.some(r => r.result.created)) {
      onSuccess?.();
    }
  };

  const doScan = useCallback(async (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      messageApi.error('檔案過大，上限 10MB');
      return;
    }

    setScanning(true);
    const previewUrl = URL.createObjectURL(file);
    setCurrentPreview(previewUrl);

    try {
      const res = await expensesApi.smartScan(file, { auto_create: true });
      const data = res.data;

      if (data) {
        setRecords(prev => [...prev, { file_name: file.name, result: data, preview_url: previewUrl }]);

        if (data.created) {
          messageApi.success(`✅ ${data.inv_num} 已建檔 (${data.method === 'qr' ? 'QR' : 'OCR'})`);
        } else if (data.success) {
          messageApi.warning(data.message || '辨識成功但未建檔');
        } else {
          messageApi.info('未辨識出發票');
        }
      }
    } catch {
      messageApi.error('辨識失敗');
    } finally {
      setScanning(false);
      setCurrentPreview(null);
    }
  }, [messageApi]);

  const handleCameraCapture = () => cameraRef.current?.click();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) doScan(file);
    if (cameraRef.current) cameraRef.current.value = '';
  };

  const createdCount = records.filter(r => r.result.created).length;
  const totalCount = records.length;

  const methodTag = (method: string) => {
    switch (method) {
      case 'qr': return <Tag color="green">QR</Tag>;
      case 'qr+ocr': return <Tag color="blue">QR+OCR</Tag>;
      case 'ocr': return <Tag color="orange">OCR</Tag>;
      default: return <Tag>—</Tag>;
    }
  };

  return (
    <Modal
      title={
        <Space>
          <ScanOutlined />
          智慧發票掃描
          {totalCount > 0 && (
            <Badge count={`${createdCount}/${totalCount}`} style={{ backgroundColor: '#52c41a' }} />
          )}
        </Space>
      }
      open={open}
      onCancel={handleClose}
      footer={
        <Space>
          <Text type="secondary">
            {totalCount > 0 ? `已掃 ${totalCount} 張，建檔 ${createdCount} 筆` : ''}
          </Text>
          <Button onClick={handleClose}>
            {totalCount > 0 ? '完成' : '關閉'}
          </Button>
        </Space>
      }
      width={600}
    >
      {/* 拍照/上傳區 — 始終顯示（支援連續掃描） */}
      {!scanning && (
        <>
          {records.length === 0 && (
            <Alert
              type="info"
              showIcon
              message="拍一張照片，自動辨識電子發票 QR Code 或傳統發票，支援連續掃描多張"
              style={{ marginBottom: 16 }}
            />
          )}

          <Space style={{ width: '100%', marginBottom: 16 }} size="middle">
            <Button
              type="primary"
              icon={<CameraOutlined />}
              size="large"
              onClick={handleCameraCapture}
              style={{ height: 48, fontSize: 16 }}
            >
              {records.length > 0 ? '繼續拍照' : '拍照掃描'}
            </Button>

            <Upload
              accept="image/jpeg,image/png,image/webp,image/heic"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(file) => { doScan(file); return false; }}
            >
              <Button icon={<PictureOutlined />} size="large" style={{ height: 48 }}>
                選擇照片
              </Button>
            </Upload>

            {records.length > 0 && (
              <Button icon={<PlusOutlined />} size="large" style={{ height: 48 }}
                onClick={handleCameraCapture}>
                下一張
              </Button>
            )}
          </Space>

          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </>
      )}

      {/* 掃描中 */}
      {scanning && (
        <div style={{ textAlign: 'center', padding: '30px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 12 }}>
            <Text type="secondary">辨識中... QR → OCR</Text>
          </div>
          {currentPreview && (
            <img src={currentPreview} alt="掃描中" style={{ maxWidth: 180, marginTop: 12, borderRadius: 8, opacity: 0.6 }} />
          )}
        </div>
      )}

      {/* 累計結果列表 */}
      {records.length > 0 && !scanning && (
        <>
          <Divider style={{ margin: '8px 0' }}>掃描紀錄</Divider>
          <List
            size="small"
            dataSource={[...records].reverse()}
            style={{ maxHeight: 400, overflow: 'auto' }}
            renderItem={(rec, idx) => (
              <List.Item
                key={idx}
                style={{
                  padding: '8px 12px',
                  backgroundColor: rec.result.created ? '#f6ffed' : rec.result.success ? '#fffbe6' : '#fff2f0',
                  borderRadius: 6,
                  marginBottom: 4,
                }}
              >
                <List.Item.Meta
                  avatar={
                    <img src={rec.preview_url} alt="" style={{ width: 48, height: 48, objectFit: 'cover', borderRadius: 4 }} />
                  }
                  title={
                    <Space size="small">
                      {rec.result.created
                        ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                        : <WarningOutlined style={{ color: rec.result.success ? '#faad14' : '#ff4d4f' }} />
                      }
                      <Text strong>{rec.result.inv_num || '未辨識'}</Text>
                      {methodTag(rec.result.method)}
                    </Space>
                  }
                  description={
                    <Space split="｜" size={0}>
                      {rec.result.amount != null && <Text>NT$ {rec.result.amount.toLocaleString()}</Text>}
                      {rec.result.date && <Text type="secondary">{rec.result.date}</Text>}
                      {rec.result.items && rec.result.items.length > 0 && (
                        <Text type="secondary">{rec.result.items.length} 品項</Text>
                      )}
                      {rec.result.message && !rec.result.created && (
                        <Text type="warning">{rec.result.message}</Text>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </>
      )}
    </Modal>
  );
};

export default SmartScanModal;
