import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useMemo } from 'react';
import { ROUTES, ROUTE_META } from './types';

// 導航 hook
export const useAppNavigation = () => {
  const navigate = useNavigate();
  
  const navigateToDocument = (id?: number) => {
    if (id) {
      navigate(ROUTES.DOCUMENT_DETAIL.replace(':id', String(id)));
    } else {
      navigate(ROUTES.DOCUMENTS);
    }
  };
  
  const navigateToCreateDocument = () => {
    navigate(ROUTES.DOCUMENT_CREATE);
  };
  
  const navigateToEditDocument = (id: number) => {
    navigate(ROUTES.DOCUMENT_EDIT.replace(':id', String(id)));
  };
  
  const navigateToDashboard = () => {
    navigate(ROUTES.DASHBOARD);
  };
  
  const navigateToSettings = () => {
    navigate(ROUTES.SETTINGS);
  };
  
  const navigateToProfile = () => {
    navigate(ROUTES.PROFILE);
  };
  
  const goBack = () => {
    navigate(-1);
  };
  
  return {
    navigate,
    navigateToDocument,
    navigateToCreateDocument,
    navigateToEditDocument,
    navigateToDashboard,
    navigateToSettings,
    navigateToProfile,
    goBack,
  };
};

// 當前路由資訊 hook
export const useCurrentRoute = () => {
  const location = useLocation();
  const params = useParams();
  
  const currentRoute = useMemo(() => {
    const pathname = location.pathname;
    
    // 找到匹配的路由
    const matchedRoute = Object.entries(ROUTES).find(([, path]) => {
      if (path.includes(':')) {
        // 處理動態路由
        const regex = new RegExp('^' + path.replace(/:[^/]+/g, '[^/]+') + '$');
        return regex.test(pathname);
      }
      return path === pathname;
    });
    
    if (matchedRoute) {
      const [routeName, routePath] = matchedRoute;
      const meta = ROUTE_META[routePath as keyof typeof ROUTE_META];
      
      return {
        name: routeName,
        path: routePath,
        currentPath: pathname,
        meta,
        params,
      };
    }
    
    return null;
  }, [location.pathname, params]);
  
  return currentRoute;
};

// 麵包屑 hook
export const useBreadcrumbs = () => {
  const location = useLocation();
  const params = useParams();
  
  const breadcrumbs = useMemo(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbItems = [];
    
    // 總是包含首頁
    breadcrumbItems.push({
      name: '首頁',
      path: ROUTES.HOME,
    });
    
    let currentPath = '';
    pathSegments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      
      // 處理動態參數
      const isNumeric = /^\d+$/.test(segment);
      if (isNumeric && params.id) {
        // 如果是數字且有 ID 參數，可能是詳情頁
        const parentPath = pathSegments.slice(0, index).join('/') || '/';
        if (parentPath.includes('documents')) {
          breadcrumbItems.push({
            name: `公文 #${segment}`,
            path: currentPath,
          });
        }
        return;
      }
      
      // 根據路徑段生成麵包屑
      switch (segment) {
        case 'documents':
          breadcrumbItems.push({
            name: '公文管理',
            path: ROUTES.DOCUMENTS,
          });
          break;
        case 'create':
          breadcrumbItems.push({
            name: '新增公文',
            path: currentPath,
          });
          break;
        case 'edit':
          breadcrumbItems.push({
            name: '編輯公文',
            path: currentPath,
          });
          break;
        case 'dashboard':
          breadcrumbItems.push({
            name: '儀表板',
            path: ROUTES.DASHBOARD,
          });
          break;
        case 'settings':
          breadcrumbItems.push({
            name: '系統設定',
            path: ROUTES.SETTINGS,
          });
          break;
        case 'profile':
          breadcrumbItems.push({
            name: '個人資料',
            path: ROUTES.PROFILE,
          });
          break;
      }
    });
    
    return breadcrumbItems;
  }, [location.pathname, params]);
  
  return breadcrumbs;
};

// 路由權限檢查 hook
export const useRoutePermission = () => {
  // TODO: 實作真實的權限檢查邏輯
  const hasPermission = (requiredRoles: string[] = []) => {
    const userRoles = ['admin']; // 暫時設定
    return requiredRoles.length === 0 || requiredRoles.some(role => userRoles.includes(role));
  };
  
  const isAuthenticated = () => {
    // TODO: 檢查使用者認證狀態
    return true; // 暫時設為 true
  };
  
  return {
    hasPermission,
    isAuthenticated,
  };
};
