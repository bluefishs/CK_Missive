import React from 'react';
import { Card, Typography, Space, Row, Col, Statistic, Alert } from 'antd';
import { SettingOutlined, DatabaseOutlined, SafetyCertificateOutlined } from '@ant-design/icons';

const { Title } = Typography;

const SystemPage: React.FC = () => {
  return (
    <Space direction="vertical" style={{ width: '100%', padding: '24px' }}>
      <Title level={2}>系統管理</Title>
      
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title="系統運行時間"
              value="正常"
              prefix={<SettingOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="資料庫狀態"
              value="連線正常"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="安全狀態"
              value="安全"
              prefix={<SafetyCertificateOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="系統設定">
        <Alert
          message="系統設定功能"
          description="系統相關設定請至相應的管理頁面：使用者管理、資料庫管理、網站管理等。"
          type="info"
          showIcon
        />
      </Card>
    </Space>
  );
};

export default SystemPage;