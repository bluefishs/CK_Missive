import React from 'react';
import { Result, Button } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

export const DocumentDetailPage = () => {
  const navigate = useNavigate();

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      background: '#f5f5f5'
    }}>
      <Result
        status="info"
        title="DocumentDetail 頁面"
        subTitle="此頁面正在開發中，即將完成。"
        extra={
          <Button 
            type="primary" 
            icon={<HomeOutlined />}
            onClick={() => navigate('/dashboard')}
          >
            返回首頁
          </Button>
        }
      />
    </div>
  );
};
