/**
 * 裝置管理 Tab 元件
 *
 * 在 ProfilePage 中顯示使用者的活躍 Session 列表，
 * 提供撤銷指定 Session 與撤銷所有其他 Session 的功能。
 * 使用 Ant Design List 與 Tag 元件呈現。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  List,
  Tag,
  Button,
  Spin,
  Empty,
  Space,
  Typography,
  App,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  DesktopOutlined,
  MobileOutlined,
  LaptopOutlined,
  GlobalOutlined,
  DeleteOutlined,
  DisconnectOutlined,
  ReloadOutlined,
  CheckCircleFilled,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-tw';
import { listSessions, revokeSession, revokeAllSessions } from '../../api/sessionApi';
import { logger } from '../../utils/logger';
import type { SessionInfo } from '../../api/sessionApi';

dayjs.extend(relativeTime);
dayjs.locale('zh-tw');

const { Text } = Typography;

/**
 * 從 User-Agent 字串中解析裝置與瀏覽器資訊
 */
function parseUserAgent(ua: string | null): {
  browser: string;
  os: string;
  device: string;
  icon: React.ReactNode;
} {
  if (!ua) {
    return { browser: '未知', os: '未知', device: '未知裝置', icon: <GlobalOutlined /> };
  }

  const lowerUA = ua.toLowerCase();

  // 判斷是否為行動裝置
  const isMobile =
    lowerUA.includes('mobile') ||
    lowerUA.includes('android') ||
    lowerUA.includes('iphone') ||
    lowerUA.includes('ipad');

  // 瀏覽器判斷
  let browser = '瀏覽器';
  if (lowerUA.includes('edg/') || lowerUA.includes('edge')) {
    browser = 'Edge';
  } else if (lowerUA.includes('chrome') && !lowerUA.includes('edg')) {
    browser = 'Chrome';
  } else if (lowerUA.includes('firefox')) {
    browser = 'Firefox';
  } else if (lowerUA.includes('safari') && !lowerUA.includes('chrome')) {
    browser = 'Safari';
  }

  // 作業系統判斷
  let os = '';
  if (lowerUA.includes('iphone')) {
    os = 'iPhone';
  } else if (lowerUA.includes('ipad')) {
    os = 'iPad';
  } else if (lowerUA.includes('android')) {
    os = 'Android';
  } else if (lowerUA.includes('windows')) {
    os = 'Windows';
  } else if (lowerUA.includes('mac os')) {
    os = 'macOS';
  } else if (lowerUA.includes('linux')) {
    os = 'Linux';
  }

  const device = os ? `${os} ${browser}` : browser;

  let icon: React.ReactNode;
  if (isMobile) {
    icon = <MobileOutlined />;
  } else if (lowerUA.includes('mac')) {
    icon = <LaptopOutlined />;
  } else {
    icon = <DesktopOutlined />;
  }

  return { browser, os, device, icon };
}

interface SessionManagementTabProps {
  /** 是否為行動裝置 */
  isMobile?: boolean;
}

export const SessionManagementTab: React.FC<SessionManagementTabProps> = ({
  isMobile = false,
}) => {
  const { message } = App.useApp();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [revokingId, setRevokingId] = useState<number | null>(null);
  const [revokingAll, setRevokingAll] = useState(false);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await listSessions();
      setSessions(response.sessions);
    } catch (error) {
      logger.error('載入 Session 列表失敗:', error);
      // 保留現有資料，不清空
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleRevokeSession = useCallback(
    async (sessionId: number) => {
      setRevokingId(sessionId);
      try {
        await revokeSession(sessionId);
        message.success('已成功登出該裝置');
        // 重新載入列表
        await fetchSessions();
      } catch (error) {
        const detail = (error as { message?: string })?.message;
        message.error(detail || '撤銷 Session 失敗');
      } finally {
        setRevokingId(null);
      }
    },
    [fetchSessions, message]
  );

  const handleRevokeAll = useCallback(async () => {
    setRevokingAll(true);
    try {
      const response = await revokeAllSessions();
      message.success(response.message || '已成功登出所有其他裝置');
      // 重新載入列表
      await fetchSessions();
    } catch (error) {
      const detail = (error as { message?: string })?.message;
      message.error(detail || '撤銷所有 Session 失敗');
    } finally {
      setRevokingAll(false);
    }
  }, [fetchSessions, message]);

  // 計算是否有可撤銷的其他 session
  const otherSessionCount = useMemo(
    () => sessions.filter((s) => !s.is_current).length,
    [sessions]
  );

  return (
    <div>
      {/* 操作列 */}
      <div
        style={{
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <Space size={8}>
          <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>
            共 {sessions.length} 個活躍裝置
          </Text>
          <Tooltip title="重新整理">
            <Button
              type="text"
              icon={<ReloadOutlined />}
              size="small"
              onClick={fetchSessions}
              loading={loading}
              aria-label="重新整理"
            />
          </Tooltip>
        </Space>

        {otherSessionCount > 0 && (
          <Popconfirm
            title="登出所有其他裝置"
            description={`確定要登出其他 ${otherSessionCount} 個裝置嗎？此操作無法復原。`}
            onConfirm={handleRevokeAll}
            okText="確定登出"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              danger
              icon={<DisconnectOutlined />}
              size={isMobile ? 'small' : 'middle'}
              loading={revokingAll}
            >
              {isMobile ? '登出所有' : '登出所有其他裝置'}
            </Button>
          </Popconfirm>
        )}
      </div>

      {/* Session 列表 */}
      <Spin spinning={loading}>
        {sessions.length === 0 && !loading ? (
          <Empty description="目前沒有活躍的 Session" />
        ) : (
          <List
            itemLayout={isMobile ? 'vertical' : 'horizontal'}
            dataSource={sessions}
            renderItem={(session) => {
              const { device, icon: deviceIcon } = parseUserAgent(session.user_agent);
              const createdAt = dayjs(session.created_at);
              const lastActivity = session.last_activity
                ? dayjs(session.last_activity)
                : null;

              return (
                <List.Item
                  key={session.id}
                  style={{
                    backgroundColor: session.is_current ? '#f6ffed' : undefined,
                    padding: isMobile ? '12px 8px' : '12px 16px',
                    borderRadius: 6,
                    marginBottom: 4,
                  }}
                  actions={
                    session.is_current
                      ? [
                          <Tag
                            key="current"
                            icon={<CheckCircleFilled />}
                            color="success"
                          >
                            目前裝置
                          </Tag>,
                        ]
                      : [
                          <Popconfirm
                            key="revoke"
                            title="登出此裝置"
                            description="確定要登出此裝置嗎？"
                            onConfirm={() => handleRevokeSession(session.id)}
                            okText="確定"
                            cancelText="取消"
                            okButtonProps={{ danger: true }}
                          >
                            <Button
                              danger
                              type="link"
                              icon={<DeleteOutlined />}
                              size="small"
                              loading={revokingId === session.id}
                            >
                              登出
                            </Button>
                          </Popconfirm>,
                        ]
                  }
                >
                  <List.Item.Meta
                    avatar={
                      <span
                        style={{
                          fontSize: isMobile ? 20 : 24,
                          color: session.is_current ? '#52c41a' : '#8c8c8c',
                        }}
                      >
                        {deviceIcon}
                      </span>
                    }
                    title={
                      <Space size={8} wrap>
                        <Text strong style={{ fontSize: isMobile ? 13 : 14 }}>
                          {device}
                        </Text>
                        {session.is_current && (
                          <Tag color="green" style={{ marginLeft: 0 }}>
                            目前使用中
                          </Tag>
                        )}
                      </Space>
                    }
                    description={
                      <Space
                        direction="vertical"
                        size={2}
                        style={{ width: '100%' }}
                      >
                        {session.ip_address && (
                          <Text
                            type="secondary"
                            style={{ fontSize: isMobile ? 11 : 12 }}
                          >
                            <GlobalOutlined style={{ marginRight: 4 }} />
                            {session.ip_address}
                          </Text>
                        )}
                        <Text
                          type="secondary"
                          style={{ fontSize: isMobile ? 11 : 12 }}
                        >
                          <ClockCircleOutlined style={{ marginRight: 4 }} />
                          登入時間：{createdAt.format('YYYY-MM-DD HH:mm:ss')}
                          {lastActivity && (
                            <span style={{ marginLeft: 12 }}>
                              最後活動：{lastActivity.fromNow()}
                            </span>
                          )}
                        </Text>
                      </Space>
                    }
                  />
                </List.Item>
              );
            }}
          />
        )}
      </Spin>
    </div>
  );
};

export default SessionManagementTab;
