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
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';

const { Text, Paragraph } = Typography;

// 通知類型定義
interface Notification {
  id: number;
  type: string;
  severity: string;
  title: string;
  message: string;
  source_table?: string;
  source_id?: number;
  changes?: Record<string, unknown>;
  user_name?: string;
  is_read: boolean;
  created_at?: string;
}

interface NotificationListResponse {
  success: boolean;
  items: Notification[];
  total: number;
  unread_count: number;
}

interface UnreadCountResponse {
  success: boolean;
  unread_count: number;
}

interface MarkReadResponse {
  success: boolean;
  updated_count: number;
  message: string;
}

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
  const queryClient = useQueryClient();

  // 取得未讀數量
  const { data: unreadData } = useQuery<UnreadCountResponse>({
    queryKey: ['notifications-unread-count'],
    queryFn: async () => {
      // apiClient.post 已返回 response.data，無需再解包
      return await apiClient.post<UnreadCountResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.UNREAD_COUNT, {});
    },
    refetchInterval: 30000, // 每 30 秒自動刷新
  });

  // 取得通知列表
  const { data: listData, isLoading } = useQuery<NotificationListResponse>({
    queryKey: ['notifications-list'],
    queryFn: async () => {
      // apiClient.post 已返回 response.data，無需再解包
      return await apiClient.post<NotificationListResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.LIST, {
        limit: 20,
        is_read: null, // 取得所有通知
      });
    },
    enabled: open, // 只在打開時載入
  });

  // 標記已讀 mutation
  const markReadMutation = useMutation<MarkReadResponse, Error, number[]>({
    mutationFn: async (ids: number[]) => {
      // apiClient.post 已返回 response.data，無需再解包
      return await apiClient.post<MarkReadResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.MARK_READ, {
        notification_ids: ids,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] });
    },
  });

  // 全部標記已讀 mutation
  const markAllReadMutation = useMutation<MarkReadResponse, Error, void>({
    mutationFn: async () => {
      // apiClient.post 已返回 response.data，無需再解包
      return await apiClient.post<MarkReadResponse>(API_ENDPOINTS.SYSTEM_NOTIFICATIONS.MARK_ALL_READ, {});
    },
    onSuccess: (data) => {
      message.success(data.message);
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-list'] });
    },
  });

  // 點擊通知項目
  const handleNotificationClick = useCallback((notification: Notification) => {
    if (!notification.is_read) {
      markReadMutation.mutate([notification.id]);
    }

    // 若有關聯公文，可以導航到公文詳情
    if (notification.source_table === 'documents' && notification.source_id) {
      // 這裡可以實作導航邏輯
      logger.debug(`Navigate to document ${notification.source_id}`);
    }
  }, [markReadMutation]);

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

  const unreadCount = unreadData?.unread_count || 0;
  const notifications = listData?.items || [];

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
            onClick={(e) => {
              e.stopPropagation();
              markAllReadMutation.mutate();
            }}
            loading={markAllReadMutation.isPending}
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
              共 {listData?.total || 0} 筆通知
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
