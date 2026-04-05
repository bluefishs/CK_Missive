import React from 'react';
import { Result, Button } from 'antd';
import { HomeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';

export const NotFoundPage: React.FC = () => {
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
        status="404"
        title="404"
        subTitle="抱歉，您要尋找的頁面不存在或已被移除。"
        extra={
          <Button 
            type="primary" 
            icon={<HomeOutlined />}
            size="large"
            onClick={() => navigate(ROUTES.DASHBOARD)}
          >
            回到首頁
          </Button>
        }
      />
    </div>
  );
};
