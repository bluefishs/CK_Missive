/**
 * ERP 填報頁共用外殼（2026-08-02）
 *
 * 為什麼抽這一層：ERP 的填報頁陸續由 Modal 改為獨立路由頁（去彈跳視窗），
 * 每一頁重複的其實只有「返回鍵 + 標題 + Card + 送出/取消 + 行動版尺寸調整」
 * 這層版面。欄位、型別、mutation 各自不同，**刻意不抽**成萬用表單引擎——
 * 那會變成每次改一個欄位都要繞過抽象層（同 L53 facade 過度工程的教訓）。
 *
 * RWD 行為集中在這裡，改一次全部填報頁一致；
 * 沿用 ERP 既有的 ResponsiveContent 慣例 + 公文頁的 isMobile 細節。
 */

import React from 'react';
import { Card, Button, Space, Typography, Spin } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';

import { useResponsive } from '../../hooks';

const { Title, Text } = Typography;

export interface ErpFormPageShellProps {
  /** 頁面標題（例：新增請款 / 編輯發票） */
  title: string;
  /** 返回上一層（通常是回到來源詳情頁） */
  onBack: () => void;
  /** 送出 */
  onSubmit: () => void;
  submitting?: boolean;
  /** 送出鍵文字，預設依 isEdit 決定 */
  submitText?: string;
  isEdit?: boolean;
  /** 載入中（編輯時取單筆） */
  loading?: boolean;
  /** 找不到資料時顯示的訊息；有值即取代表單內容 */
  notFoundMessage?: string;
  /** 返回鍵文字（桌面版），手機一律顯示「返回」 */
  backText?: string;
  /** 標題列右側的額外操作（如編輯模式下的「刪除」）。
      2026-08-04：來源詳情頁的表格操作欄移除後，刪除這類動作需要有地方安放，
      比照 DetailPageLayout 的 header 放法 —— 操作在標題列，不在列表列。 */
  headerExtra?: React.ReactNode;
  children: React.ReactNode;
}

export const ErpFormPageShell: React.FC<ErpFormPageShellProps> = ({
  title,
  onBack,
  onSubmit,
  submitting = false,
  submitText,
  isEdit = false,
  loading = false,
  notFoundMessage,
  backText = '返回',
  headerExtra,
  children,
}) => {
  const { isMobile } = useResponsive();

  if (loading) {
    return (
      <ResponsiveContent maxWidth="md">
        <div style={{ textAlign: 'center', padding: 48 }}><Spin /></div>
      </ResponsiveContent>
    );
  }

  if (notFoundMessage) {
    return (
      <ResponsiveContent maxWidth="md">
        <Card>
          <Text type="secondary">{notFoundMessage}</Text>
          <div style={{ marginTop: 16 }}>
            <Button icon={<ArrowLeftOutlined />} onClick={onBack}>{backText}</Button>
          </div>
        </Card>
      </ResponsiveContent>
    );
  }

  return (
    <ResponsiveContent maxWidth="md">
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: isMobile ? 8 : 16,
        marginBottom: isMobile ? 16 : 24,
      }}>
        <Button
          icon={<ArrowLeftOutlined />}
          size={isMobile ? 'small' : 'middle'}
          onClick={onBack}
        >
          {isMobile ? '返回' : backText}
        </Button>
        <Title level={isMobile ? 5 : 4} style={{ margin: 0, flex: 1 }}>{title}</Title>
        {headerExtra}
      </div>

      <Card size={isMobile ? 'small' : 'default'} styles={{ body: { padding: isMobile ? 12 : 24 } }}>
        {children}

        <Space
          direction={isMobile ? 'vertical' : 'horizontal'}
          style={{ width: isMobile ? '100%' : undefined, marginTop: isMobile ? 8 : 16 }}
        >
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={submitting}
            onClick={onSubmit}
            block={isMobile}
          >
            {submitText ?? (isEdit ? '儲存變更' : '新增')}
          </Button>
          <Button onClick={onBack} block={isMobile} disabled={submitting}>
            取消
          </Button>
        </Space>
      </Card>
    </ResponsiveContent>
  );
};

export default ErpFormPageShell;
