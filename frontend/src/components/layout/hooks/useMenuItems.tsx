/**
 * useMenuItems Hook
 * 選單項目轉換和圖標映射
 * 從 Layout.tsx 拆分出來
 */

import React from 'react';
import {
  DashboardOutlined,
  FileTextOutlined,
  UserOutlined,
  BankOutlined,
  TeamOutlined,
  SettingOutlined,
  NumberOutlined,
  ApiOutlined,
  ShopOutlined,
  ProjectOutlined,
  GlobalOutlined,
  CalendarOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  EyeOutlined,
  ImportOutlined,
  ExportOutlined,
  ApartmentOutlined,
  LineChartOutlined,
  FormOutlined,
  SecurityScanOutlined,
  MonitorOutlined,
  GoogleOutlined,
  ScheduleOutlined,
  FolderOutlined,
  RocketOutlined,
  CloudServerOutlined,
  ExperimentOutlined,
  EnvironmentOutlined,
  SendOutlined,
  CodeOutlined,
  AuditOutlined,
  AccountBookOutlined,
  NodeIndexOutlined,
} from '@ant-design/icons';
import type { NavigationItem } from './types';

// 圖標映射表
const iconMap: { [key: string]: React.ReactNode } = {
  // 簡化名稱映射 (向後兼容)
  'home': <DashboardOutlined />,
  'dashboard': <DashboardOutlined />,
  'file-text': <FileTextOutlined />,
  'file': <FileTextOutlined />,
  'plus': <FileTextOutlined />,
  'upload': <FileTextOutlined />,
  'download': <FileTextOutlined />,
  'workflow': <SettingOutlined />,
  'number': <NumberOutlined />,
  'project': <ProjectOutlined />,
  'contract': <ProjectOutlined />,
  'bank': <BankOutlined />,
  'shop': <ShopOutlined />,
  'calendar': <CalendarOutlined />,
  'bar-chart': <BarChartOutlined />,
  'api': <ApiOutlined />,
  'setting': <SettingOutlined />,
  'form': <FileTextOutlined />,
  'global': <GlobalOutlined />,
  'database': <BankOutlined />,
  'user': <UserOutlined />,
  'team': <TeamOutlined />,
  'key': <SettingOutlined />,

  // 完整 Ant Design 圖標名稱映射
  'FileTextOutlined': <FileTextOutlined />,
  'FolderOutlined': <FolderOutlined />,
  'CalendarOutlined': <CalendarOutlined />,
  'BarChartOutlined': <BarChartOutlined />,
  'SettingOutlined': <SettingOutlined />,
  'UserOutlined': <UserOutlined />,
  'DashboardOutlined': <DashboardOutlined />,
  'ProjectOutlined': <ProjectOutlined />,
  'BankOutlined': <BankOutlined />,
  'ShopOutlined': <ShopOutlined />,
  'TeamOutlined': <TeamOutlined />,
  'GlobalOutlined': <GlobalOutlined />,
  'DatabaseOutlined': <DatabaseOutlined />,
  'ApiOutlined': <ApiOutlined />,
  'EyeOutlined': <EyeOutlined />,
  'ImportOutlined': <ImportOutlined />,
  'ExportOutlined': <ExportOutlined />,
  'ApartmentOutlined': <ApartmentOutlined />,
  'LineChartOutlined': <LineChartOutlined />,
  'FormOutlined': <FormOutlined />,
  'SecurityScanOutlined': <SecurityScanOutlined />,
  'MonitorOutlined': <MonitorOutlined />,
  'GoogleOutlined': <GoogleOutlined />,
  'ScheduleOutlined': <ScheduleOutlined />,
  'RocketOutlined': <RocketOutlined />,
  'CloudServerOutlined': <CloudServerOutlined />,
  'ExperimentOutlined': <ExperimentOutlined />,
  'EnvironmentOutlined': <EnvironmentOutlined />,
  'SendOutlined': <SendOutlined />,
  'NumberOutlined': <NumberOutlined />,
  'CodeOutlined': <CodeOutlined />,
  'AuditOutlined': <AuditOutlined />,
  'AccountBookOutlined': <AccountBookOutlined />,
  'NodeIndexOutlined': <NodeIndexOutlined />,
};

/**
 * 取得圖標元件
 */
export const getIcon = (iconName?: string): React.ReactNode => {
  return iconMap[iconName || ''] || <FileTextOutlined />;
};

/**
 * 將導覽項目轉換為 Ant Design Menu 格式
 */
/** Ant Design Menu 項目格式 */
export interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
  children?: MenuItem[];
  permission_required?: string;
}

export const convertToMenuItems = (items: NavigationItem[]): MenuItem[] => {
  let fallbackIndex = 0;
  const convertItem = (item: NavigationItem): MenuItem => {
    const uniqueKey = item.children && item.children.length > 0
      ? `parent-${item.key || item.path || `nav-${fallbackIndex++}`}`
      : item.path || item.key || `leaf-${fallbackIndex++}`;

    const menuItem: MenuItem = {
      key: uniqueKey,
      icon: getIcon(item.icon),
      label: item.title,
      path: item.path,
    };

    if (item.children && item.children.length > 0) {
      menuItem.children = item.children.map(child => convertItem(child));
    }

    return menuItem;
  };

  return items.map(item => convertItem(item));
};

/**
 * 取得靜態選單項目 (備用)
 */
// getStaticMenuItems 已於 2026-09-08 刪除：它是選單的第二份宣告（DB 選單表才是唯一來源），
// 且其 ERP 項目沒有權限碼，導覽 API 失敗時對所有人露出。

/**
 * 根據路徑取得當前選中的選單 key
 */
export const getCurrentMenuKey = (pathname: string): string => {
  if (pathname === '/' || pathname === '/dashboard') return '/dashboard';
  return pathname;
};

/**
 * 根據路徑取得預設展開的選單 keys
 */
export const getDefaultOpenKeys = (pathname: string): string[] => {
  if (pathname.startsWith('/documents')) return ['/documents', 'documents'];
  if (pathname.startsWith('/contract-cases')) return ['project-management'];
  if (pathname.startsWith('/projects')) return ['project-management'];
  if (pathname.startsWith('/agencies')) return ['project-management'];
  if (pathname.startsWith('/vendors')) return ['project-management'];
  if (pathname.startsWith('/calendar')) return ['/calendar', 'calendar'];
  if (pathname.startsWith('/reports')) return ['/reports', 'reports'];
  if (pathname.startsWith('/api-docs')) return ['/reports', 'reports'];
  if (pathname.startsWith('/demo/unified-form')) return ['/reports', 'reports'];
  if (pathname.startsWith('/pm')) return ['case-data-menu', 'parent-project-management'];
  if (pathname.startsWith('/erp')) return ['case-data-menu', 'parent-project-management'];
  if (pathname.startsWith('/admin')) return ['/admin/system', 'system'];
  if (pathname.startsWith('/settings')) return ['/settings', 'settings'];
  return [];
};

export default { convertToMenuItems, getIcon, getCurrentMenuKey, getDefaultOpenKeys };
