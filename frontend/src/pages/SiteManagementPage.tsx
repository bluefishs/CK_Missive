import React, { useState, useEffect } from 'react';
import { Tabs, Card, Typography, Space, Alert } from 'antd';
import { GlobalOutlined, MenuOutlined, SettingOutlined } from '@ant-design/icons';
import NavigationManagement from '../components/site-management/NavigationManagement';
import SiteConfigManagement from '../components/site-management/SiteConfigManagement';
import authService, { UserInfo } from '../services/authService';
import { usePermissions } from '../hooks/usePermissions';

const { Title, Paragraph } = Typography;

export const SiteManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('navigation');

  // 使用權限 hook 自動處理認證停用模式
  const { isAdmin, isSuperuser } = usePermissions();

  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };

  // 根據權限過濾標籤頁
  const getAvailableTabs = () => {
    const tabs = [];

    // 導覽列管理 - 管理員以上可以存取
    if (isAdmin) {
      tabs.push({
        key: 'navigation',
        label: (
          <span>
            <MenuOutlined />
            導覽列管理
          </span>
        ),
        children: <NavigationManagement />
      });
    }

    // 網站配置 - 只有超級管理員可以存取
    if (isSuperuser) {
      tabs.push({
        key: 'config',
        label: (
          <span>
            <SettingOutlined />
            網站配置
          </span>
        ),
        children: <SiteConfigManagement />
      });
    }

    return tabs;
  };

  const tabItems = getAvailableTabs();

  // 如果沒有任何權限，顯示權限不足訊息
  if (tabItems.length === 0) {
    return (
      <div style={{ padding: '24px' }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
              <GlobalOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
              網站管理
            </Title>
          </Card>
          <Alert
            message="權限不足"
            description="您沒有足夠的權限存取網站管理功能。請聯繫系統管理員獲取相關權限。"
            type="warning"
            showIcon
          />
        </Space>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <Card>
          <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
            <GlobalOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
            網站管理
          </Title>
          <Paragraph style={{ margin: '8px 0 0 0', color: '#666' }}>
            管理網站導覽列結構、排序和各項配置設定
            {!isSuperuser && (
              <span style={{ color: '#faad14' }}>
                {' '}(部分功能需要超級管理員權限)
              </span>
            )}
          </Paragraph>
        </Card>

        <Card>
          <Tabs 
            activeKey={activeTab} 
            onChange={handleTabChange} 
            size="large"
            items={tabItems}
          />
        </Card>
      </Space>
    </div>
  );
};

export default SiteManagementPage;