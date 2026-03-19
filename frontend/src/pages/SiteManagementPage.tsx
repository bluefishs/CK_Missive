import { useState } from 'react';
import type { FC } from 'react';
import { Card, Space, Alert, Tabs } from 'antd';
import { GlobalOutlined, MenuOutlined, SettingOutlined } from '@ant-design/icons';
import { usePermissions } from '../hooks';
import SiteConfigManagement from '../components/site-management/SiteConfigManagement';
import { NavigationTreePanel } from './siteManagement';
import './SiteManagementPage.css';

export const SiteManagementPage: FC = () => {
  const [activeTab, setActiveTab] = useState('navigation');
  const { isAdmin, isSuperuser } = usePermissions();

  const getAvailableTabs = () => {
    const tabs = [];

    if (isAdmin()) {
      tabs.push({
        key: 'navigation',
        label: (
          <span>
            <MenuOutlined />
            導覽列管理
          </span>
        ),
        children: <NavigationTreePanel />
      });
    }

    if (isSuperuser()) {
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

  if (tabItems.length === 0) {
    return (
      <div className="site-management-page">
        <Card>
          <Alert
            title="權限不足"
            description="您沒有足夠的權限存取網站管理功能。"
            type="warning"
            showIcon
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="site-management-page">
      <Card>
        <Space vertical style={{ width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
            <GlobalOutlined style={{ fontSize: 24, marginRight: 12, color: '#1890ff' }} />
            <div>
              <h2 style={{ margin: 0 }}>網站管理</h2>
              <span style={{ color: '#666' }}>管理網站導覽列結構、排序和各項配置設定</span>
            </div>
          </div>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            size="large"
            items={tabItems}
          />
        </Space>
      </Card>
    </div>
  );
};

export default SiteManagementPage;
