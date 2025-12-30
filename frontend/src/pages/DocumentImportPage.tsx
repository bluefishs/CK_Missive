import React from 'react';
import { Card, Typography, Space, Alert, Button } from 'antd';
import { ImportOutlined } from '@ant-design/icons';

const { Title } = Typography;

const DocumentImportPage: React.FC = () => {
  return (
    <Space direction="vertical" style={{ width: '100%', padding: '24px' }}>
      <Title level={2}>
        <ImportOutlined /> 公文匯入
      </Title>
      
      <Card title="CSV 文件匯入">
        <Alert
          message="功能已整合"
          description="公文匯入功能已整合在公文管理頁面中，請至公文管理使用 CSV 匯入功能。"
          type="info"
          showIcon
          action={
            <Button size="small" href="/documents">
              前往公文管理
            </Button>
          }
        />
      </Card>
      
      <Card title="支援的匯入格式">
        <ul>
          <li>CSV 文件 (.csv)</li>
          <li>支援中文編碼 (UTF-8, Big5)</li>
          <li>批量匯入公文資料</li>
          <li>自動檢測文件格式</li>
          <li>容錯處理機制</li>
        </ul>
      </Card>
    </Space>
  );
};

export default DocumentImportPage;