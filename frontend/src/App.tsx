
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import { QueryProvider } from './providers';
import { ErrorBoundary } from './components/common';
import { AppRouter } from './router';
import GlobalApiErrorNotifier from './components/common/GlobalApiErrorNotifier';
import zhTW from 'antd/locale/zh_TW';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-tw';
import updateLocale from 'dayjs/plugin/updateLocale';
import './App.css';

// 設定 dayjs 使用繁體中文，並將週一設為每週起始日
dayjs.extend(updateLocale);
dayjs.locale('zh-tw');
dayjs.updateLocale('zh-tw', {
  weekStart: 1, // 週一為起始日 (0=週日, 1=週一)
});

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
            <GlobalApiErrorNotifier />
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
