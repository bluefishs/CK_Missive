import React from 'react';
import { Card, Typography, Space, Alert, Button } from 'antd';
import { ExportOutlined } from '@ant-design/icons';

const { Title } = Typography;

const DocumentExportPage: React.FC = () => {
  return (
    <Space direction="vertical" style={{ width: '100%', padding: '24px' }}>
      <Title level={2}>
        <ExportOutlined /> 公文匯出
      </Title>
      
      <Card title="資料匯出">
        <Alert
          message="功能已整合"
          description="公文匯出功能已整合在公文管理頁面中，請至公文管理使用批量匯出功能。"
          type="info"
          showIcon
          action={
            <Button size="small" href="/documents">
              前往公文管理
            </Button>
          }
        />
      </Card>
      
      <Card title="支援的匯出格式">
        <ul>
          <li>Excel 文件 (.xlsx)</li>
          <li>CSV 文件 (.csv)</li>
          <li>PDF 報表</li>
          <li>自定範圍匯出</li>
          <li>按條件篩選匯出</li>
          <li>批量檔案打包</li>
        </ul>
      </Card>
    </Space>
  );
};

export default DocumentExportPage;