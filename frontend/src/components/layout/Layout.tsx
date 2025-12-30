import React, { useState } from 'react';
import { useEffect } from "react";
import {
  Layout as AntLayout,
  Menu,
  Button,
  Typography,
  Breadcrumb,
  Dropdown,
  Avatar,
  Space,
  Drawer,
} from 'antd';
import {
  MenuOutlined,
  FileTextOutlined,
  DashboardOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  HomeOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = AntLayout;
const { Title } = Typography;

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  const menuItems = [
    {
      key: 'documents',
      icon: <FileTextOutlined />,
      label: '公文管理',
    },
    {
      key: 'dashboard',
      icon: <DashboardOutlined />,
      label: '儀表板',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系統設定',
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '個人資料',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
    },
  ];

  const breadcrumbItems = [
    {
      title: <HomeOutlined />,
    },
    {
      title: '公文管理',
    },
  ];

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {/* 桌面版側邊欄 */}
      <Sider 
        breakpoint="lg"
        collapsedWidth="0"
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{ 
          height: 64, 
          margin: 16, 
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Title level={4} style={{ color: 'white', margin: 0 }}>
            {collapsed ? 'CK' : '乾坤測繪'}
          </Title>
        </div>
        
        <Menu
          theme="dark"
          mode="inline"
          defaultSelectedKeys={['documents']}
          items={menuItems}
        />
      </Sider>

      <AntLayout style={{ marginLeft: collapsed ? 0 : 200 }}>
        {/* 頂部導航 */}
        <Header style={{ 
          padding: '0 24px', 
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
        }}>
          <Space>
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ display: isMobile ? 'block' : 'none' }}
            />
            
            <Title level={3} style={{ margin: 0, color: '#1976d2' }}>
              乾坤測繪公文管理系統
            </Title>
          </Space>

          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button type="text" style={{ height: 'auto', padding: '4px 8px' }}>
              <Space>
                <Avatar icon={<UserOutlined />} />
                管理員
              </Space>
            </Button>
          </Dropdown>
        </Header>

        {/* 內容區域 */}
        <Content style={{ 
          margin: '24px',
          minHeight: 280,
        }}>
          {/* 麵包屑導航 */}
          <Breadcrumb 
            items={breadcrumbItems}
            style={{ marginBottom: 16 }}
          />
          
          <div style={{
            padding: 24,
            minHeight: 360,
            background: '#fff',
            borderRadius: 6,
          }}>
            {children}
          </div>
        </Content>
      </AntLayout>

      {/* 移動版抽屜 */}
      <Drawer
        title="乾坤測繪公文系統"
        placement="left"
        onClose={() => setMobileDrawerOpen(false)}
        open={mobileDrawerOpen}
        width={240}
      >
        <Menu
          mode="inline"
          defaultSelectedKeys={['documents']}
          items={menuItems}
          onClick={() => setMobileDrawerOpen(false)}
        />
      </Drawer>
    </AntLayout>
  );
};