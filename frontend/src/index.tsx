import React from 'react';
import ReactDOM from 'react-dom/client';

// 2026-09-04 owner「頁面載入失敗（chunk 404）前端常發生」：部署後舊分頁要的 hash chunk 已換新，
// vite 會發 vite:preloadError。在這裡攔下來直接整頁重載（拿新 index.html），不要先炸到 ErrorBoundary 的錯誤頁。
// 60 秒內只重載一次，避免真的壞掉時無限迴圈。
window.addEventListener('vite:preloadError', (event) => {
  const key = 'vite_preload_reload_ts';
  const last = Number(sessionStorage.getItem(key) || 0);
  if (Date.now() - last < 60_000) return;
  sessionStorage.setItem(key, String(Date.now()));
  event.preventDefault();
  window.location.reload();
});
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);