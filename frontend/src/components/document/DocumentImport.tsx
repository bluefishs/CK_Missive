/**
 * 公文匯入對話框
 *
 * @version 2.0.0 - 模組化重構：Hook + 子元件提取
 * @date 2026-01-28
 */

import React from 'react';
import {
  Modal,
  Upload,
  Button,
  Tabs,
  Alert,
  Space,
  Progress,
} from 'antd';
import {
  FileExcelOutlined,
  FileTextOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';

import { useDocumentImport } from './import/useDocumentImport';
import { ImportPreviewCard } from './import/ImportPreviewCard';
import { ImportResultCard } from './import/ImportResultCard';

const { Dragger } = Upload;

interface DocumentImportProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const DocumentImport: React.FC<DocumentImportProps> = ({
  visible,
  onClose,
  onSuccess,
}) => {
  const {
    activeTab,
    setActiveTab,
    uploading,
    importing,
    step,
    previewResult,
    importResult,
    handleReset,
    handleClose,
    handleExcelPreview,
    handleExcelImport,
    handleCsvUpload,
    handleDownloadTemplate,
  } = useDocumentImport(onClose, onSuccess);

  const ExcelImportPanel = () => (
    <div>
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="手動公文匯入"
        description={
          <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
            <li>適用於紙本郵寄紀錄、手動輸入的公文資料</li>
            <li>使用本系統匯出的 Excel 格式</li>
            <li>公文ID 有值 = 更新現有資料</li>
            <li>公文ID 空白 = 新增（自動產生流水號）</li>
            <li>支援匯入前預覽確認</li>
          </ul>
        }
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16 }}>
        <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
          下載匯入範本
        </Button>
      </Space>

      {step === 'upload' && (
        <Dragger
          accept=".xlsx,.xls"
          showUploadList={false}
          beforeUpload={handleExcelPreview}
          disabled={uploading}
        >
          <div className="ant-upload-drag-icon">
            {uploading ? (
              <Progress type="circle" percent={-1} size={48} />
            ) : (
              <EyeOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            )}
          </div>
          <p className="ant-upload-text">
            {uploading ? '載入中...' : '點擊或拖曳 Excel 檔案預覽'}
          </p>
          <p className="ant-upload-hint">
            支援 .xlsx, .xls 格式，上傳後可預覽確認再匯入
          </p>
        </Dragger>
      )}

      {step === 'preview' && previewResult && (
        <ImportPreviewCard
          previewResult={previewResult}
          importing={importing}
          onReset={handleReset}
          onImport={handleExcelImport}
        />
      )}

      {step === 'result' && importResult && (
        <ImportResultCard
          importResult={importResult}
          onClose={handleClose}
          onReset={handleReset}
        />
      )}
    </div>
  );

  const CsvImportPanel = () => (
    <div>
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="電子公文檔匯入"
        description={
          <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
            <li>適用於電子公文系統匯出的 CSV 檔案</li>
            <li>receiveList.csv (收文清單)</li>
            <li>sendList.csv (發文清單)</li>
            <li>自動偵測標頭、組合公文字號</li>
          </ul>
        }
        style={{ marginBottom: 16 }}
      />

      {step === 'upload' && (
        <Dragger
          accept=".csv"
          showUploadList={false}
          beforeUpload={handleCsvUpload}
          disabled={uploading}
        >
          <div className="ant-upload-drag-icon">
            {uploading ? (
              <Progress type="circle" percent={-1} size={48} />
            ) : (
              <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            )}
          </div>
          <p className="ant-upload-text">
            {uploading ? '匯入中...' : '點擊或拖曳 CSV 檔案到此處'}
          </p>
          <p className="ant-upload-hint">
            支援 receiveList.csv, sendList.csv 格式
          </p>
        </Dragger>
      )}

      {step === 'result' && importResult && (
        <ImportResultCard
          importResult={importResult}
          onClose={handleClose}
          onReset={handleReset}
        />
      )}
    </div>
  );

  const tabItems = [
    {
      key: 'excel',
      label: (
        <span>
          <FileExcelOutlined />
          手動公文匯入
        </span>
      ),
      children: <ExcelImportPanel />,
    },
    {
      key: 'csv',
      label: (
        <span>
          <FileTextOutlined />
          電子公文檔匯入
        </span>
      ),
      children: <CsvImportPanel />,
    },
  ];

  return (
    <Modal
      title="公文匯入"
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={800}
      destroyOnHidden
    >
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key);
          handleReset();
        }}
        items={tabItems}
      />
    </Modal>
  );
};

export default DocumentImport;
