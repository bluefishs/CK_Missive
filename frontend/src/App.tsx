
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntdApp } from 'antd';
import type { ThemeConfig } from 'antd';
import { createAntdTheme } from '@ck-shared/tokens';
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

// Ant Design 主題配置 — 引 @ck-shared/tokens 共享結構 + Missive 品牌主色（Phase 3 / L80）。
// 主色配合專案律定（Missive '#1976d2'）；圓角/字級/語意色/版面色全平臺共享。值不變＝視覺不變。
const theme: ThemeConfig = createAntdTheme('#1976d2');

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
