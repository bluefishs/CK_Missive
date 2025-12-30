
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import { QueryProvider } from './providers';
import { ErrorBoundary } from './components/common';
import { AppRouter } from './router';
import zhTW from 'antd/locale/zh_TW';
import './App.css';

// Ant Design 主題配置
const theme = {
  token: {
    colorPrimary: '#1976d2',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Layout: {
      siderBg: '#001529',
      triggerBg: '#001529',
    },
    Menu: {
      darkItemBg: '#001529',
      darkSubMenuItemBg: '#000c17',
    },
  },
};

function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <ConfigProvider 
          theme={theme} 
          locale={zhTW}
          componentSize="middle"
        >
          <AntdApp>
            <BrowserRouter
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <AppRouter />
            </BrowserRouter>
          </AntdApp>
        </ConfigProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
}

export default App;
