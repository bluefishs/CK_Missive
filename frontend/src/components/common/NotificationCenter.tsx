/**
 * 通知中心元件
 *
 * 使用集中的 hooks 管理 useQuery 邏輯
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import React, { useState, useCallback } from 'react';
import {
  Badge,
  Button,
  Dropdown,
  List,
  Typography,
  Tag,
  Space,
  Empty,
  Spin,
  Divider,
  message,
} from 'antd';
import { logger } from '../../utils/logger';
import {
  BellOutlined,
  CheckOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

// 使用集中的 Hooks
import {
  useUnreadNotificationCount,
  useNotificationList,
  useNotificationMutations,
  type SystemNotification,
} from '../../hooks';

const { Text, Paragraph } = Typography;

// 嚴重程度圖示和顏色（使用具體類型以支援 TypeScript 嚴格模式）
type SeverityType = 'info' | 'warning' | 'error' | 'critical';
interface SeverityConfig {
  icon: React.ReactNode;
  color: string;
}
const severityConfig: Record<SeverityType, SeverityConfig> & Record<string, SeverityConfig | undefined> = {
  info: { icon: <InfoCircleOutlined />, color: 'blue' },
  warning: { icon: <WarningOutlined />, color: 'orange' },
  error: { icon: <CloseCircleOutlined />, color: 'red' },
  critical: { icon: <ExclamationCircleOutlined />, color: 'magenta' },
};
const defaultSeverityConfig: SeverityConfig = severityConfig.info;

// 通知類型標籤
const typeLabels: Record<string, string> = {
  system: '系統',
  critical_change: '關鍵變更',
  import: '匯入',
  error: '錯誤',
  security: '安全',
  calendar_event: '行事曆',
  project_update: '專案更新',
};

export const NotificationCenter: React.FC = () => {
  const [open, setOpen] = useState(false);

  // 使用集中的 Hooks
  const { unreadCount } = useUnreadNotificationCount(true);
  const { notifications, total, isLoading } = useNotificationList(open);
  const { markRead, markAllRead, isMarkingAllRead } = useNotificationMutations();

  // 點擊通知項目
  const handleNotificationClick = useCallback((notification: SystemNotification) => {
    if (!notification.is_read) {
      markRead([notification.id]);
    }

    // 若有關聯公文，可以導航到公文詳情
    if (notification.source_table === 'documents' && notification.source_id) {
      // 這裡可以實作導航邏輯
      logger.debug(`Navigate to document ${notification.source_id}`);
    }
  }, [markRead]);

  // 全部標記已讀
  const handleMarkAllRead = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    markAllRead();
    message.success('已將所有通知標記為已讀');
  }, [markAllRead]);

  // 格式化時間
  const formatTime = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '剛剛';
    if (diffMins < 60) return `${diffMins} 分鐘前`;
    if (diffHours < 24) return `${diffHours} 小時前`;
    if (diffDays < 7) return `${diffDays} 天前`;
    return dateStr.split(' ')[0];
  };

  // 下拉內容
  const dropdownContent = (
    <div style={{ width: 380, maxHeight: 480, overflow: 'hidden' }}>
      {/* 標題列 */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Text strong style={{ fontSize: 16 }}>
          系統通知
        </Text>
        {unreadCount > 0 && (
          <Button
            type="link"
            size="small"
            icon={<CheckOutlined />}
            onClick={handleMarkAllRead}
            loading={isMarkingAllRead}
          >
            全部已讀
          </Button>
        )}
      </div>

      {/* 通知列表 */}
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        {isLoading ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <Spin />
          </div>
        ) : notifications.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暫無通知"
            style={{ padding: 40 }}
          />
        ) : (
          <List
            dataSource={notifications}
            renderItem={(item) => {
              // 取得嚴重程度配置，預設為 info
              const config: SeverityConfig =
                severityConfig[item.severity] ?? defaultSeverityConfig;
              return (
                <List.Item
                  onClick={() => handleNotificationClick(item)}
                  style={{
                    padding: '12px 16px',
                    cursor: 'pointer',
                    background: item.is_read ? '#fff' : '#f6ffed',
                    borderLeft: item.is_read ? 'none' : '3px solid #52c41a',
                  }}
                  className="notification-item"
                >
                  <List.Item.Meta
                    avatar={
                      <span style={{ color: config.color, fontSize: 20 }}>
                        {config.icon}
                      </span>
                    }
                    title={
                      <Space size={8}>
                        <Text
                          strong={!item.is_read}
                          style={{ fontSize: 14 }}
                        >
                          {item.title}
                        </Text>
                        <Tag color={config.color} style={{ fontSize: 10 }}>
                          {typeLabels[item.type] || item.type}
                        </Tag>
                      </Space>
                    }
                    description={
                      <>
                        <Paragraph
                          ellipsis={{ rows: 2 }}
                          style={{
                            marginBottom: 4,
                            fontSize: 12,
                            color: '#666',
                          }}
                        >
                          {item.message}
                        </Paragraph>
                        <Space size={8}>
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {formatTime(item.created_at)}
                          </Text>
                          {item.user_name && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                              by {item.user_name}
                            </Text>
                          )}
                        </Space>
                      </>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </div>

      {/* 底部 */}
      {notifications.length > 0 && (
        <>
          <Divider style={{ margin: 0 }} />
          <div style={{ padding: '8px 16px', textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 {total || 0} 筆通知
            </Text>
          </div>
        </>
      )}
    </div>
  );

  return (
    <Dropdown
      popupRender={() => dropdownContent}
      trigger={['click']}
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
    >
      <Button
        type="text"
        style={{ height: 'auto', padding: '4px 12px' }}
      >
        <Badge count={unreadCount} size="small" offset={[2, -2]}>
          <BellOutlined style={{ fontSize: 18 }} />
        </Badge>
      </Button>
    </Dropdown>
  );
};

export default NotificationCenter;
