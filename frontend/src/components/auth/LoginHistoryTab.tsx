/**
 * 登入歷史 Tab 元件
 *
 * 在 ProfilePage 中顯示使用者的登入歷史紀錄時間軸。
 * 使用 Ant Design Timeline 與 Tag 元件呈現。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Timeline,
  Tag,
  Pagination,
  Spin,
  Empty,
  Space,
  Typography,
  DatePicker,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  StopOutlined,
  LogoutOutlined,
  SyncOutlined,
  GlobalOutlined,
  LaptopOutlined,
  MobileOutlined,
  DesktopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-tw';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { logger } from '../../utils/logger';
import type { LoginHistoryItem, LoginHistoryResponse } from '../../types/api';

dayjs.extend(relativeTime);
dayjs.locale('zh-tw');

const { Text } = Typography;
const { RangePicker } = DatePicker;

// 事件類型對應的繁體中文名稱
const EVENT_TYPE_LABELS: Record<string, string> = {
  LOGIN_SUCCESS: '登入成功',
  LOGIN_FAILED: '登入失敗',
  LOGIN_BLOCKED: '帳號被封鎖',
  LOGOUT: '登出',
  TOKEN_REFRESH: '權杖刷新',
};

// 事件類型對應的顏色
const EVENT_TYPE_COLORS: Record<string, string> = {
  LOGIN_SUCCESS: 'green',
  LOGIN_FAILED: 'red',
  LOGIN_BLOCKED: 'orange',
  LOGOUT: 'blue',
  TOKEN_REFRESH: 'cyan',
};

// 事件類型對應的圖示
const EVENT_TYPE_ICONS: Record<string, React.ReactNode> = {
  LOGIN_SUCCESS: <CheckCircleOutlined />,
  LOGIN_FAILED: <CloseCircleOutlined />,
  LOGIN_BLOCKED: <StopOutlined />,
  LOGOUT: <LogoutOutlined />,
  TOKEN_REFRESH: <SyncOutlined />,
};

// 時間軸圓點顏色
const TIMELINE_DOT_COLORS: Record<string, string> = {
  LOGIN_SUCCESS: 'green',
  LOGIN_FAILED: 'red',
  LOGIN_BLOCKED: 'orange',
  LOGOUT: 'blue',
  TOKEN_REFRESH: 'cyan',
};

/**
 * 從 User-Agent 字串中簡化解析裝置資訊
 */
function parseUserAgent(ua?: string): { device: string; icon: React.ReactNode } {
  if (!ua) {
    return { device: '未知裝置', icon: <GlobalOutlined /> };
  }

  const lowerUA = ua.toLowerCase();

  // 行動裝置判斷
  if (lowerUA.includes('mobile') || lowerUA.includes('android') || lowerUA.includes('iphone')) {
    let device = '行動裝置';
    if (lowerUA.includes('iphone')) device = 'iPhone';
    else if (lowerUA.includes('android')) device = 'Android';
    return { device, icon: <MobileOutlined /> };
  }

  // 桌面瀏覽器判斷
  let browser = '瀏覽器';
  if (lowerUA.includes('edg/') || lowerUA.includes('edge')) browser = 'Edge';
  else if (lowerUA.includes('chrome') && !lowerUA.includes('edg')) browser = 'Chrome';
  else if (lowerUA.includes('firefox')) browser = 'Firefox';
  else if (lowerUA.includes('safari') && !lowerUA.includes('chrome')) browser = 'Safari';

  let os = '';
  if (lowerUA.includes('windows')) os = 'Windows';
  else if (lowerUA.includes('mac os')) os = 'macOS';
  else if (lowerUA.includes('linux')) os = 'Linux';

  const device = os ? `${os} ${browser}` : browser;

  return {
    device,
    icon: lowerUA.includes('mac') ? <LaptopOutlined /> : <DesktopOutlined />,
  };
}

interface LoginHistoryTabProps {
  /** 是否為行動裝置 */
  isMobile?: boolean;
}

export const LoginHistoryTab: React.FC<LoginHistoryTabProps> = ({ isMobile = false }) => {
  const [items, setItems] = useState<LoginHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(() => [
    dayjs().subtract(30, 'day'),
    dayjs(),
  ]);

  const fetchLoginHistory = useCallback(async (currentPage: number) => {
    setLoading(true);
    try {
      const response = await apiClient.post<LoginHistoryResponse>(
        API_ENDPOINTS.AUTH.LOGIN_HISTORY,
        {},
        { params: { page: currentPage, page_size: pageSize } }
      );
      setItems(response.items);
      setTotal(response.total);
    } catch (error) {
      logger.error('載入登入歷史失敗:', error);
      // 保留現有資料，不清空
    } finally {
      setLoading(false);
    }
  }, [pageSize]);

  useEffect(() => {
    fetchLoginHistory(page);
  }, [page, fetchLoginHistory]);

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  // 根據日期範圍篩選（前端篩選已載入的資料，日期範圍作為視覺參考）
  const filteredItems = useMemo(() => {
    if (!dateRange || dateRange.length !== 2) return items;
    const [start, end] = dateRange;
    return items.filter((item) => {
      const itemDate = dayjs(item.created_at);
      return itemDate.isAfter(start.startOf('day')) && itemDate.isBefore(end.endOf('day'));
    });
  }, [items, dateRange]);

  const timelineItems = useMemo(
    () =>
      filteredItems.map((item) => {
        const { device, icon: deviceIcon } = parseUserAgent(item.user_agent);
        const eventLabel = EVENT_TYPE_LABELS[item.event_type] || item.event_type;
        const eventColor = EVENT_TYPE_COLORS[item.event_type] || 'default';
        const eventIcon = EVENT_TYPE_ICONS[item.event_type];
        const dotColor = TIMELINE_DOT_COLORS[item.event_type] || 'gray';
        const relativeTimeStr = dayjs(item.created_at).fromNow();
        const absoluteTimeStr = dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss');

        return {
          key: item.id,
          color: dotColor,
          dot: eventIcon,
          children: (
            <div style={{ paddingBottom: 8 }}>
              <Space direction={isMobile ? 'vertical' : 'horizontal'} size={isMobile ? 2 : 8} wrap>
                <Tag icon={eventIcon} color={eventColor}>
                  {eventLabel}
                </Tag>
                {item.ip_address && (
                  <Text type="secondary" style={{ fontSize: isMobile ? 11 : 13 }}>
                    <GlobalOutlined style={{ marginRight: 4 }} />
                    {item.ip_address}
                  </Text>
                )}
                <Text type="secondary" style={{ fontSize: isMobile ? 11 : 13 }}>
                  {deviceIcon}
                  <span style={{ marginLeft: 4 }}>{device}</span>
                </Text>
              </Space>
              <div style={{ marginTop: 4 }}>
                <Text type="secondary" style={{ fontSize: isMobile ? 11 : 12 }}>
                  {relativeTimeStr}
                  <span style={{ marginLeft: 8, color: '#bbb' }}>{absoluteTimeStr}</span>
                </Text>
              </div>
            </div>
          ),
        };
      }),
    [filteredItems, isMobile]
  );

  return (
    <div>
      {/* 日期範圍篩選 */}
      <div style={{ marginBottom: 16 }}>
        <Space direction={isMobile ? 'vertical' : 'horizontal'} size={8}>
          <Text strong style={{ fontSize: isMobile ? 12 : 14 }}>
            篩選日期範圍：
          </Text>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            size={isMobile ? 'small' : 'middle'}
            allowClear
            style={{ width: isMobile ? '100%' : undefined }}
          />
        </Space>
      </div>

      {/* 載入狀態 */}
      <Spin spinning={loading}>
        {filteredItems.length === 0 && !loading ? (
          <Empty description="暫無登入紀錄" />
        ) : (
          <>
            <Timeline items={timelineItems} />

            {/* 分頁 */}
            {total > pageSize && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Pagination
                  current={page}
                  total={total}
                  pageSize={pageSize}
                  onChange={handlePageChange}
                  showTotal={(t) => `共 ${t} 筆紀錄`}
                  size={isMobile ? 'small' : 'default'}
                  showSizeChanger={false}
                />
              </div>
            )}
          </>
        )}
      </Spin>
    </div>
  );
};

export default LoginHistoryTab;
