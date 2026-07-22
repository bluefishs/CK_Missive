
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import type { ThemeConfig } from 'antd';
import { antdTheme } from '@ck-shared/tokens';
import { QueryProvider } from './providers';
import { ErrorBoundary } from './components/common';
import { AppRouter } from './router';
import GlobalApiErrorNotifier from './components/common/GlobalApiErrorNotifier';
import SessionGate from './components/common/SessionGate';
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

// Ant Design 主題配置 — 改引 @ck-shared/tokens 單一源（Phase 3 / L80；值不變＝視覺不變）
const theme: ThemeConfig = antdTheme;

function App() {
  return (
    <ErrorBoundary>
      <QueryProvider>
        <ConfigProvider
          theme={theme}
          locale={zhTW}
        >
          <AntdApp>
            <GlobalApiErrorNotifier />
            <BrowserRouter
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <SessionGate>
                <AppRouter />
              </SessionGate>
            </BrowserRouter>
          </AntdApp>
        </ConfigProvider>
      </QueryProvider>
    </ErrorBoundary>
  );
}

export default App;
