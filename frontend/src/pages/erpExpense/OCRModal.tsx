/**
 * OCR 發票辨識 Modal
 */
import React, { useState } from 'react';
import { Modal, Upload, Progress, Alert, Space, Button, message } from 'antd';
import { CameraOutlined } from '@ant-design/icons';
import type { FormInstance } from 'antd';
import type { ExpenseInvoiceOCRResult, ExpenseInvoiceCreate } from '../../types/erp';
import { useOCRParseExpense } from '../../hooks';
import dayjs from 'dayjs';

interface Props {
  open: boolean;
  onClose: () => void;
  createForm: FormInstance<ExpenseInvoiceCreate>;
  onOpenCreate: () => void;
}

const OCRModal: React.FC<Props> = ({ open, onClose, createForm, onOpenCreate }) => {
  const ocrMutation = useOCRParseExpense();
  const [ocrResult, setOcrResult] = useState<ExpenseInvoiceOCRResult | null>(null);

  const handleClose = () => {
    onClose();
    setOcrResult(null);
  };

  const handleUpload = (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      message.error('檔案過大，上限為 10MB');
      return;
    }
    ocrMutation.mutate(file, {
      onSuccess: (res) => {
        const result = res.data;
        if (!result) {
          message.error('OCR 回傳空結果');
          return;
        }
        setOcrResult(result);
        if (result.inv_num || result.amount) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const formValues: Record<string, any> = {
            inv_num: result.inv_num ?? '',
            amount: result.amount,
            source: 'ocr',
          };
          if (result.date) formValues.date = dayjs(result.date);
          if (result.buyer_ban) formValues.buyer_ban = result.buyer_ban;
          if (result.seller_ban) formValues.seller_ban = result.seller_ban;
          createForm.setFieldsValue(formValues);
          message.success(`OCR 辨識完成 (信心度: ${Math.round(result.confidence * 100)}%)，請確認後送出`);
          handleClose();
          onOpenCreate();
        } else {
          message.warning('OCR 未能辨識出發票資訊，請手動輸入');
        }
      },
      onError: () => message.error('OCR 辨識失敗'),
    });
  };

  return (
    <Modal
      title="OCR 發票辨識"
      open={open}
      onCancel={handleClose}
      footer={ocrResult ? (
        <Space>
          <Button onClick={handleClose}>關閉</Button>
        </Space>
      ) : null}
      width={480}
    >
      {!ocrResult && (
        <Upload.Dragger
          accept="image/jpeg,image/png,image/webp,image/heic"
          maxCount={1}
          showUploadList={false}
          beforeUpload={(file) => {
            handleUpload(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon"><CameraOutlined style={{ fontSize: 48, color: '#1890ff' }} /></p>
          <p className="ant-upload-text">點擊或拖曳發票影像至此</p>
          <p className="ant-upload-hint">支援 JPEG/PNG/WebP/HEIC，上限 10MB</p>
        </Upload.Dragger>
      )}
      {ocrMutation.isPending && <Progress percent={99} status="active" style={{ marginTop: 16 }} />}
      {ocrResult && (
        <div style={{ marginTop: 8 }}>
          <Alert
            type={ocrResult.confidence >= 0.6 ? 'success' : 'warning'}
            message={`辨識信心度: ${Math.round(ocrResult.confidence * 100)}%`}
            style={{ marginBottom: 12 }}
          />
          {ocrResult.warnings.length > 0 && (
            <Alert type="info" title={ocrResult.warnings.join('、')} style={{ marginBottom: 12 }} />
          )}
        </div>
      )}
    </Modal>
  );
};

export default OCRModal;
