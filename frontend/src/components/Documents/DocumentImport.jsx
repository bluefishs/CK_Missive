import React, { useState } from 'react';
import { Upload, Button, Card, Alert, Progress, Typography, Space, Divider } from 'antd';
import { InboxOutlined, FileExcelOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { documentAPI } from '../services/documentAPI';

const { Dragger } = Upload;
const { Title, Text } = Typography;

const DocumentImport = ({ onImportSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileUpload = async (file) => {
    // 檢查檔案類型
    if (!file.name.endsWith('.csv')) {
      setImportResult({
        success: false,
        message: '請選擇CSV格式檔案'
      });
      return false;
    }

    setUploading(true);
    setUploadProgress(0);
    setImportResult(null);

    try {
      // 模擬上傳進度
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // 執行匯入
      const result = await documentAPI.importCSV(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      // 處理結果
      if (result.success_count > 0) {
        setImportResult({
          success: true,
          message: `匯入成功！共處理 ${result.total_rows} 筆，成功 ${result.success_count} 筆`,
          details: result
        });
        
        // 通知父元件刷新
        if (onImportSuccess) {
          onImportSuccess(result);
        }
      } else {
        setImportResult({
          success: false,
          message: `匯入失敗！共 ${result.error_count} 筆錯誤`,
          details: result
        });
      }

    } catch (error) {
      console.error('匯入失敗:', error);
      setImportResult({
        success: false,
        message: `匯入失敗: ${error.response?.data?.detail || error.message}`
      });
    } finally {
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 2000);
    }

    return false; // 阻止預設上傳行為
  };

  const downloadTemplate = () => {
    // 建立CSV範本
    const csvContent = [
      '公文文號,公文類型,主旨,發文機關,收文機關,公文日期,分類,類別,字,承攬案件,收文日期,發文日期',
      '桃工建字第1140001號,函,關於工程案件申請,桃園市政府工務局,乾坤測繪有限公司,114年1月5日,receive,函,建,測量工程案,114年1月5日 10:30,',
      '乾測字第1140001號,函,測量成果報告,乾坤測繪有限公司,桃園市政府工務局,114年1月10日,send,函,測,測量工程案,,114年1月10日 14:00'
    ].join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'documents_template.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card title="批次匯入公文資料" className="import-card">
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        
        {/* 使用說明 */}
        <Alert
          message="匯入說明"
          description={
            <div>
              <p>1. 請使用CSV格式檔案（UTF-8編碼）</p>
              <p>2. 必須包含：公文文號、公文類型、主旨、分類等欄位</p>
              <p>3. 日期格式支援：114年1月5日、2025-01-05等</p>
              <p>4. 分類欄位請使用：receive（收文）或 send（發文）</p>
            </div>
          }
          type="info"
          showIcon
        />

        {/* 下載範本 */}
        <div style={{ textAlign: 'center' }}>
          <Button 
            icon={<FileExcelOutlined />} 
            onClick={downloadTemplate}
            type="dashed"
          >
            下載CSV範本
          </Button>
        </div>

        <Divider />

        {/* 檔案上傳區域 */}
        <Dragger
          beforeUpload={handleFileUpload}
          disabled={uploading}
          showUploadList={false}
          style={{ padding: '20px' }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">
            <Title level={4}>點擊或拖拽CSV檔案到這裡</Title>
          </p>
          <p className="ant-upload-hint">
            支援單個CSV檔案上傳，檔案大小限制10MB
          </p>
        </Dragger>

        {/* 上傳進度 */}
        {uploading && (
          <div>
            <Text>處理中...</Text>
            <Progress percent={uploadProgress} status="active" />
          </div>
        )}

        {/* 匯入結果 */}
        {importResult && (
          <Alert
            message={importResult.success ? '匯入成功' : '匯入失敗'}
            description={
              <div>
                <p>{importResult.message}</p>
                {importResult.details && (
                  <div>
                    <p>處理時間: {importResult.details.processing_time?.toFixed(2)} 秒</p>
                    {importResult.details.errors && importResult.details.errors.length > 0 && (
                      <div>
                        <Text strong>錯誤詳情:</Text>
                        <ul style={{ maxHeight: '150px', overflow: 'auto', marginTop: '8px' }}>
                          {importResult.details.errors.slice(0, 10).map((error, index) => (
                            <li key={index}>{error}</li>
                          ))}
                          {importResult.details.errors.length > 10 && (
                            <li>... 還有 {importResult.details.errors.length - 10} 筆錯誤</li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            }
            type={importResult.success ? 'success' : 'error'}
            showIcon
            icon={importResult.success ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
          />
        )}
      </Space>
    </Card>
  );
};

export default DocumentImport;
