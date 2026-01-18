import React, { useState, useEffect } from 'react';
import {
  Drawer,
  List,
  Badge,
  Button,
  Typography,
  Card,
  Space,
  Tag,
  Empty,
  Spin,
  message,
  Tooltip,
  Divider
} from 'antd';
import { logger } from '../utils/logger';
import {
  BellOutlined,
  CheckOutlined,
  DeleteOutlined,
  CalendarOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  ProjectOutlined
} from '@ant-design/icons';
import { secureApiService } from '../services/secureApiService';

const { Text, Title } = Typography;

interface SystemNotification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  priority: number;
  is_read: boolean;
  created_at: string;
  related_object_type?: string;
  related_object_id?: number;
  action_url?: string;
}

interface NotificationResponse {
  success: boolean;
  data: {
    notifications: SystemNotification[];
    total_count: number;
    unread_count: number;
  };
  message: string;
}

const NotificationCenter: React.FC = () => {
  const [visible, setVisible] = useState(false);
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  // 獲取通知列表
  const fetchNotifications = async (unreadOnly: boolean = false) => {
    try {
      setLoading(true);
      const response = await secureApiService.post<NotificationResponse>(
        '/api/project-notifications/user-notifications',
        'get_notifications',
        {
          data: {
            unread_only: unreadOnly,
            limit: 50
          }
        }
      );

      if (response.success) {
        setNotifications(response.data.notifications);
        setUnreadCount(response.data.unread_count);
      }
    } catch (error) {
      logger.error('獲取通知失敗:', error);
      message.error('獲取通知失敗');
    } finally {
      setLoading(false);
    }
  };

  // 獲取未讀通知數量
  const fetchUnreadCount = async () => {
    try {
      const response = await secureApiService.post<{
        success: boolean;
        data: { unread_count: number };
      }>('/api/project-notifications/unread-count', 'get_unread_count', { data: {} });

      if (response.success) {
        setUnreadCount(response.data.unread_count);
      }
    } catch (error) {
      logger.error('獲取未讀通知數量失敗:', error);
    }
  };

  // 標記通知為已讀
  const markAsRead = async (notificationId: number) => {
    try {
      const response = await secureApiService.post(
        '/api/project-notifications/mark-read',
        'mark_as_read',
        {
          data: {
            notification_id: notificationId
          }
        }
      ) as { success?: boolean };

      if (response?.success) {
        // 更新本地狀態
        setNotifications(prev =>
          prev.map(notification =>
            notification.id === notificationId
              ? { ...notification, is_read: true }
              : notification
          )
        );
        setUnreadCount(prev => Math.max(0, prev - 1));
        message.success('已標記為已讀');
      }
    } catch (error) {
      logger.error('標記已讀失敗:', error);
      message.error('標記已讀失敗');
    }
  };

  // 獲取通知類型圖標
  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'calendar_event':
        return <CalendarOutlined style={{ color: '#1890ff' }} />;
      case 'deadline_reminder':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'project_update':
        return <ProjectOutlined style={{ color: '#52c41a' }} />;
      case 'broadcast':
        return <InfoCircleOutlined style={{ color: '#722ed1' }} />;
      default:
        return <BellOutlined style={{ color: '#8c8c8c' }} />;
    }
  };

  // 獲取優先級標籤
  const getPriorityTag = (priority: number) => {
    if (priority === 1) {
      return <Tag color="red">高</Tag>;
    } else if (priority === 2) {
      return <Tag color="orange">中高</Tag>;
    } else if (priority === 3) {
      return <Tag color="blue">中</Tag>;
    } else if (priority === 4) {
      return <Tag color="green">低</Tag>;
    }
    return <Tag color="default">一般</Tag>;
  };

  // 格式化時間
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (days > 0) {
      return `${days}天前`;
    } else if (hours > 0) {
      return `${hours}小時前`;
    } else if (minutes > 0) {
      return `${minutes}分鐘前`;
    } else {
      return '剛剛';
    }
  };

  // 初始載入
  useEffect(() => {
    fetchUnreadCount();

    // 定期更新未讀數量
    const interval = setInterval(fetchUnreadCount, 30000); // 每30秒更新一次

    return () => clearInterval(interval);
  }, []);

  // 打開通知中心時載入通知
  useEffect(() => {
    if (visible) {
      fetchNotifications();
    }
  }, [visible]);

  return (
    <>
      {/* 通知鈴鐺按鈕 */}
      <Badge count={unreadCount} overflowCount={99}>
        <Button
          type="text"
          icon={<BellOutlined />}
          onClick={() => setVisible(true)}
          style={{ fontSize: '16px' }}
        />
      </Badge>

      {/* 通知中心抽屜 */}
      <Drawer
        title={
          <Space>
            <BellOutlined />
            通知中心
            {unreadCount > 0 && (
              <Badge count={unreadCount} style={{ marginLeft: 8 }} />
            )}
          </Space>
        }
        placement="right"
        width={400}
        open={visible}
        onClose={() => setVisible(false)}
        extra={
          <Space>
            <Button size="small" onClick={() => fetchNotifications()}>
              重新整理
            </Button>
            <Button
              size="small"
              type={notifications.some(n => !n.is_read) ? 'default' : 'primary'}
              onClick={() => fetchNotifications(!notifications.some(n => !n.is_read))}
            >
              {notifications.some(n => !n.is_read) ? '只看未讀' : '顯示全部'}
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {notifications.length === 0 ? (
            <Empty
              description="沒有通知"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <List
              dataSource={notifications}
              renderItem={(notification) => (
                <List.Item style={{ padding: 0, border: 'none' }}>
                  <Card
                    size="small"
                    style={{
                      width: '100%',
                      marginBottom: 8,
                      backgroundColor: notification.is_read ? '#fafafa' : '#f6ffed',
                      border: notification.is_read ? '1px solid #d9d9d9' : '1px solid #b7eb8f'
                    }}
                    actions={[
                      !notification.is_read && (
                        <Tooltip title="標記為已讀">
                          <Button
                            type="text"
                            size="small"
                            icon={<CheckOutlined />}
                            onClick={() => markAsRead(notification.id)}
                          />
                        </Tooltip>
                      )
                    ].filter(Boolean)}
                  >
                    <Card.Meta
                      avatar={getNotificationIcon(notification.notification_type)}
                      title={
                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                          <Text
                            strong={!notification.is_read}
                            style={{ fontSize: '14px' }}
                          >
                            {notification.title}
                          </Text>
                          {getPriorityTag(notification.priority)}
                        </Space>
                      }
                      description={
                        <div>
                          <Text
                            style={{
                              fontSize: '12px',
                              color: notification.is_read ? '#8c8c8c' : '#595959'
                            }}
                          >
                            {notification.message.length > 100
                              ? `${notification.message.substring(0, 100)}...`
                              : notification.message
                            }
                          </Text>
                          <Divider style={{ margin: '8px 0' }} />
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <Text style={{ fontSize: '11px', color: '#bfbfbf' }}>
                              {formatTime(notification.created_at)}
                            </Text>
                            {notification.related_object_type && (
                              <Tag color="geekblue" style={{ fontSize: '10px' }}>
                                {notification.related_object_type === 'document' && '公文'}
                                {notification.related_object_type === 'project' && '專案'}
                                {notification.related_object_type === 'event' && '事件'}
                              </Tag>
                            )}
                          </Space>
                        </div>
                      }
                    />
                  </Card>
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Drawer>
    </>
  );
};

export default NotificationCenter;