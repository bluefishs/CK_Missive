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
  ProfileOutlined,
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
  LinkOutlined
} from '@ant-design/icons';
import { ROUTES } from '../../../router/types';
import type { NavigationItem } from './useNavigationData';

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
  'ScheduleOutlined': <ScheduleOutlined />
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
  const convertItem = (item: NavigationItem): MenuItem => {
    const uniqueKey = item.children && item.children.length > 0
      ? `parent-${item.key || item.path || `nav-${Date.now()}`}`
      : item.path || item.key || `leaf-${Date.now()}`;

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
export const getStaticMenuItems = (): MenuItem[] => [
  {
    key: ROUTES.DASHBOARD,
    icon: <DashboardOutlined />,
    label: '儀表板',
    path: ROUTES.DASHBOARD,
  },
  // 1. 公文管理
  {
    key: 'documents-menu',
    icon: <FileTextOutlined />,
    label: '公文管理',
    children: [
      {
        key: ROUTES.DOCUMENTS,
        icon: <EyeOutlined />,
        label: '文件瀏覽',
        path: ROUTES.DOCUMENTS,
      },
      {
        key: ROUTES.DOCUMENT_NUMBERS,
        icon: <NumberOutlined />,
        label: '文號管理',
        path: ROUTES.DOCUMENT_NUMBERS,
      },
    ],
  },
  // 2. 案件資料
  {
    key: 'case-data-menu',
    icon: <ProjectOutlined />,
    label: '案件資料',
    children: [
      {
        key: ROUTES.CONTRACT_CASES,
        icon: <ProjectOutlined />,
        label: '專案管理',
        path: ROUTES.CONTRACT_CASES,
      },
      {
        key: ROUTES.AGENCIES,
        icon: <BankOutlined />,
        label: '機關管理',
        path: ROUTES.AGENCIES,
      },
      {
        key: ROUTES.VENDORS,
        icon: <ShopOutlined />,
        label: '廠商管理',
        path: ROUTES.VENDORS,
      },
      {
        key: ROUTES.STAFF,
        icon: <TeamOutlined />,
        label: '承辦同仁',
        path: ROUTES.STAFF,
      },
    ],
  },
  // 3. 行事曆
  {
    key: ROUTES.CALENDAR,
    icon: <CalendarOutlined />,
    label: '行事曆',
    path: ROUTES.CALENDAR,
  },
  // 4. 報表分析
  {
    key: 'reports-menu',
    icon: <BarChartOutlined />,
    label: '報表分析',
    children: [
      {
        key: ROUTES.REPORTS,
        icon: <LineChartOutlined />,
        label: '統計報表',
        path: ROUTES.REPORTS,
      },
      {
        key: ROUTES.API_DOCS,
        icon: <ApiOutlined />,
        label: 'API文件',
        path: ROUTES.API_DOCS,
      },
      {
        key: ROUTES.UNIFIED_FORM_DEMO,
        icon: <FormOutlined />,
        label: '統一表單示例',
        path: ROUTES.UNIFIED_FORM_DEMO,
      },
      {
        key: ROUTES.API_MAPPING,
        icon: <LinkOutlined />,
        label: 'API對應表',
        path: ROUTES.API_MAPPING,
      },
    ],
  },
  // 5. 系統管理
  {
    key: 'admin-menu',
    icon: <SettingOutlined />,
    label: '系統管理',
    children: [
      {
        key: ROUTES.USER_MANAGEMENT,
        icon: <UserOutlined />,
        label: '使用者管理',
        path: ROUTES.USER_MANAGEMENT,
      },
      {
        key: ROUTES.PERMISSION_MANAGEMENT,
        icon: <SecurityScanOutlined />,
        label: '權限管理',
        path: ROUTES.PERMISSION_MANAGEMENT,
      },
      {
        key: ROUTES.DATABASE,
        icon: <DatabaseOutlined />,
        label: '資料庫管理',
        path: ROUTES.DATABASE,
      },
      {
        key: ROUTES.SITE_MANAGEMENT,
        icon: <GlobalOutlined />,
        label: '網站管理',
        path: ROUTES.SITE_MANAGEMENT,
      },
      {
        key: ROUTES.ADMIN_DASHBOARD,
        icon: <DashboardOutlined />,
        label: '管理員面板',
        path: ROUTES.ADMIN_DASHBOARD,
      },
      {
        key: ROUTES.GOOGLE_AUTH_DIAGNOSTIC,
        icon: <GoogleOutlined />,
        label: 'Google認證診斷',
        path: ROUTES.GOOGLE_AUTH_DIAGNOSTIC,
      },
    ],
  },
  // 6. 個人設定
  {
    key: 'personal-menu',
    icon: <UserOutlined />,
    label: '個人設定',
    children: [
      {
        key: ROUTES.PROFILE,
        icon: <ProfileOutlined />,
        label: '個人設定',
        path: ROUTES.PROFILE,
      },
    ],
  },
];

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
  if (pathname.startsWith('/cases')) return ['/cases', 'cases'];
  if (pathname.startsWith('/projects')) return ['/cases', 'cases'];
  if (pathname.startsWith('/agencies')) return ['/cases', 'cases'];
  if (pathname.startsWith('/vendors')) return ['/cases', 'cases'];
  if (pathname.startsWith('/calendar')) return ['/calendar', 'calendar'];
  if (pathname.startsWith('/reports')) return ['/reports', 'reports'];
  if (pathname.startsWith('/api-docs')) return ['/reports', 'reports'];
  if (pathname.startsWith('/demo/unified-form')) return ['/reports', 'reports'];
  if (pathname.startsWith('/admin')) return ['/admin/system', 'system'];
  if (pathname.startsWith('/settings')) return ['/settings', 'settings'];
  return [];
};

export default { convertToMenuItems, getStaticMenuItems, getIcon, getCurrentMenuKey, getDefaultOpenKeys };
