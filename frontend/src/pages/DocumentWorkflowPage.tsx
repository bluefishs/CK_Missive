import React from 'react';
import { Card, Typography, Space, Steps, Alert, Button } from 'antd';
import { FileTextOutlined, EditOutlined, CheckCircleOutlined, SendOutlined } from '@ant-design/icons';

const { Title } = Typography;
const { Step } = Steps;

const DocumentWorkflowPage: React.FC = () => {
  return (
    <Space direction="vertical" style={{ width: '100%', padding: '24px' }}>
      <Title level={2}>公文流程管理</Title>
      
      <Card title="標準公文處理流程">
        <Steps
          current={1}
          direction="vertical"
          items={[
            {
              title: '收文登記',
              description: '接收外部公文，進行編號登記',
              icon: <FileTextOutlined />
            },
            {
              title: '分文處理',
              description: '依據公文性質分派至相關單位',
              icon: <EditOutlined />
            },
            {
              title: '承辦作業',
              description: '各單位進行公文處理作業',
              icon: <EditOutlined />
            },
            {
              title: '核定簽核',
              description: '主管進行公文內容核定',
              icon: <CheckCircleOutlined />
            },
            {
              title: '發文歸檔',
              description: '完成處理後發文並歸檔保存',
              icon: <SendOutlined />
            }
          ]}
        />
      </Card>

      <Card title="工作流程設定">
        <Alert
          message="功能建置中"
          description="公文工作流程設定功能正在開發中，目前公文處理請至公文管理頁面進行。"
          type="info"
          showIcon
          action={
            <Button size="small" href="/documents">
              前往公文管理
            </Button>
          }
        />
      </Card>
    </Space>
  );
};

export default DocumentWorkflowPage;