import React from 'react';
import { Spin, Typography, Space } from 'antd';

const { Text } = Typography;

interface PageLoadingProps {
  message?: string;
}

export const PageLoading: React.FC<PageLoadingProps> = ({ 
  message = '載入中...' 
}) => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '50vh',
      padding: '32px'
    }}>
      <Space direction="vertical" size="large" align="center">
        <Spin size="large" />
        <Text type="secondary" style={{ fontSize: 16 }}>
          {message}
        </Text>
      </Space>
    </div>
  );
};