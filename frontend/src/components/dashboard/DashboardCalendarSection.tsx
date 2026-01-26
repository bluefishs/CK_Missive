/**
 * 儀表板行事曆區塊
 *
 * 設計原則：
 * - 消除雙滾動條，日曆與事件列表分為獨立區塊
 * - 以「承攬案件」為主要分類，附加時間狀態標籤
 * - RWD 設計：手機版垂直堆疊，桌面版並排
 *
 * @version 4.0.0 - 重構為案件導向設計
 * @date 2026-01-26
 */

import React, { useState, useMemo } from 'react';
import {
  Card,
  Typography,
  Tag,
  Button,
  Space,
  Empty,
  Row,
  Col,
  Spin,
  Calendar,
  Badge,
  Tooltip,
} from 'antd';
import type { CalendarProps } from 'antd';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  BellOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  RightOutlined,
  LeftOutlined,
  FolderOpenOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';

dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);

import {
  useDashboardCalendar,
  DashboardQuickFilter,
  EVENT_TYPE_CONFIG,
  PRIORITY_CONFIG,
} from '../../hooks/system/useDashboardCalendar';
import { useResponsive } from '../../hooks';
import type { CalendarEvent } from '../../api/calendarApi';

const { Text, Title } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

/** 時間狀態類型 */
type TimeStatus = 'overdue' | 'today' | 'thisWeek' | 'upcoming' | 'later';

/** 案件分組 */
interface ProjectGroup {
  key: string;
  projectName: string;
  docNumber?: string;
  documentId?: number;
  events: CalendarEvent[];
  timeStatuses: TimeStatus[];
  overdueCount: number;
  todayCount: number;
  thisWeekCount: number;
  upcomingCount: number;
}

// ============================================================================
// 工具函數
// ============================================================================

/** 取得事件的時間狀態 */
const getTimeStatus = (event: CalendarEvent): TimeStatus => {
  const today = dayjs().startOf('day');
  const eventDate = dayjs(event.start_datetime).startOf('day');
  const weekEnd = today.endOf('week');
  const nextWeekEnd = weekEnd.add(1, 'week');

  if (event.status === 'pending' && eventDate.isBefore(today)) {
    return 'overdue';
  }
  if (eventDate.isSame(today, 'day')) {
    return 'today';
  }
  if (eventDate.isAfter(today) && eventDate.isSameOrBefore(weekEnd)) {
    return 'thisWeek';
  }
  if (eventDate.isAfter(weekEnd) && eventDate.isSameOrBefore(nextWeekEnd)) {
    return 'upcoming';
  }
  return 'later';
};

/** 時間狀態配置 */
const TIME_STATUS_CONFIG: Record<TimeStatus, { label: string; color: string; priority: number }> = {
  overdue: { label: '已逾期', color: '#ff4d4f', priority: 1 },
  today: { label: '今日', color: '#52c41a', priority: 2 },
  thisWeek: { label: '本週', color: '#faad14', priority: 3 },
  upcoming: { label: '即將', color: '#1890ff', priority: 4 },
  later: { label: '稍後', color: '#8c8c8c', priority: 5 },
};

// ============================================================================
// 子元件
// ============================================================================

/** 時間狀態標籤 */
const TimeStatusTag: React.FC<{ status: TimeStatus; count?: number }> = ({ status, count }) => {
  const config = TIME_STATUS_CONFIG[status];
  return (
    <Tag
      color={config.color}
      style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}
    >
      {config.label}
      {count !== undefined && count > 1 && ` (${count})`}
    </Tag>
  );
};

/** 案件卡片 */
const ProjectCard: React.FC<{
  project: ProjectGroup;
  onViewDocument: (id: number) => void;
  compact?: boolean;
}> = ({ project, onViewDocument, compact }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div
      style={{
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #f0f0f0',
        marginBottom: 12,
        overflow: 'hidden',
      }}
    >
      {/* 案件標題列 */}
      <div
        style={{
          padding: compact ? '8px 12px' : '10px 16px',
          background: project.overdueCount > 0 ? '#fff1f0' : '#fafafa',
          borderBottom: expanded ? '1px solid #f0f0f0' : 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <Space size={8} wrap>
          <FolderOpenOutlined style={{ color: '#1890ff', fontSize: 16 }} />
          {project.docNumber ? (
            <Button
              type="link"
              size="small"
              style={{ padding: 0, fontSize: compact ? 13 : 14, height: 'auto', fontWeight: 500 }}
              onClick={(e) => {
                e.stopPropagation();
                if (project.documentId) {
                  onViewDocument(project.documentId);
                }
              }}
            >
              {project.projectName}
            </Button>
          ) : (
            <Text strong style={{ fontSize: compact ? 13 : 14 }}>{project.projectName}</Text>
          )}
          <Badge
            count={project.events.length}
            size="small"
            style={{ backgroundColor: '#8c8c8c' }}
          />
        </Space>
        <Space size={4}>
          {project.overdueCount > 0 && <TimeStatusTag status="overdue" count={project.overdueCount} />}
          {project.todayCount > 0 && <TimeStatusTag status="today" count={project.todayCount} />}
          {project.thisWeekCount > 0 && <TimeStatusTag status="thisWeek" count={project.thisWeekCount} />}
          {project.upcomingCount > 0 && <TimeStatusTag status="upcoming" count={project.upcomingCount} />}
        </Space>
      </div>

      {/* 事件列表 */}
      {expanded && (
        <div style={{ padding: compact ? '8px 12px' : '12px 16px' }}>
          {project.events.map((event) => (
            <EventItem
              key={event.id}
              event={event}
              compact={compact}
              onViewDocument={onViewDocument}
            />
          ))}
        </div>
      )}
    </div>
  );
};

/** 事件項目 */
const EventItem: React.FC<{
  event: CalendarEvent;
  compact?: boolean;
  onViewDocument?: (id: number) => void;
}> = ({ event, compact, onViewDocument }) => {
  const eventType = event.event_type as keyof typeof EVENT_TYPE_CONFIG;
  const config = EVENT_TYPE_CONFIG[eventType] || EVENT_TYPE_CONFIG.reminder;
  const priority = typeof event.priority === 'number' ? event.priority : 3;
  const priorityConfig = PRIORITY_CONFIG[priority] ?? { name: '普通', color: 'blue' };
  const timeStatus = getTimeStatus(event);
  const isOverdue = timeStatus === 'overdue';
  const isCompleted = event.status === 'completed';

  return (
    <div
      style={{
        padding: compact ? '6px 10px' : '8px 12px',
        background: isOverdue ? '#fff2f0' : isCompleted ? '#f6ffed' : '#fafafa',
        borderRadius: 6,
        borderLeft: `3px solid ${isOverdue ? '#ff4d4f' : isCompleted ? '#52c41a' : config.color === 'default' ? '#d9d9d9' : config.color}`,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <Space size={4} wrap>
            <Text
              strong
              style={{
                fontSize: compact ? 12 : 13,
                textDecoration: isCompleted ? 'line-through' : 'none',
                color: isCompleted ? '#999' : undefined,
              }}
            >
              {event.title}
            </Text>
            {isOverdue && <Tag color="red" style={{ margin: 0, fontSize: 10, lineHeight: '16px' }}>逾期</Tag>}
            {isCompleted && <Tag color="success" style={{ margin: 0, fontSize: 10, lineHeight: '16px' }}>完成</Tag>}
          </Space>
          <div style={{ marginTop: 4 }}>
            <Space size={4} wrap>
              <Tag color={config.color} style={{ margin: 0, fontSize: 10 }}>{config.name}</Tag>
              <Tag color={priorityConfig.color} style={{ margin: 0, fontSize: 10 }}>{priorityConfig.name}</Tag>
              <Text type="secondary" style={{ fontSize: 11 }}>
                <FieldTimeOutlined style={{ marginRight: 2 }} />
                {dayjs(event.start_datetime).format('MM/DD HH:mm')}
              </Text>
              {/* 公文連結 */}
              {event.document_id && event.doc_number && (
                <Tooltip title="檢視公文">
                  <Tag
                    color="geekblue"
                    style={{ margin: 0, fontSize: 10, cursor: 'pointer' }}
                    icon={<FileTextOutlined />}
                    onClick={() => onViewDocument?.(event.document_id!)}
                  >
                    {compact ? '公文' : event.doc_number}
                  </Tag>
                </Tooltip>
              )}
            </Space>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 主元件
// ============================================================================

interface DashboardCalendarSectionProps {
  maxEvents?: number;
}

export const DashboardCalendarSection: React.FC<DashboardCalendarSectionProps> = ({
  maxEvents = 20,
}) => {
  const navigate = useNavigate();
  const { isMobile, isTablet } = useResponsive();

  const {
    events,
    allEvents,
    statistics,
    quickFilter,
    setQuickFilter,
    getFilterLabel,
    isLoading,
  } = useDashboardCalendar();

  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [dateFilterActive, setDateFilterActive] = useState(false); // 日期篩選模式

  // ============================================================================
  // 案件分組邏輯
  // ============================================================================

  // 根據日期篩選模式決定要顯示的事件
  const displayEvents = useMemo(() => {
    if (dateFilterActive) {
      // 日期篩選模式：只顯示選中日期的事件
      return allEvents.filter((event) =>
        dayjs(event.start_datetime).isSame(selectedDate, 'day')
      );
    }
    // 正常模式：顯示篩選後的事件
    return events;
  }, [dateFilterActive, selectedDate, allEvents, events]);

  const projectGroups = useMemo<ProjectGroup[]>(() => {
    const projectMap = new Map<string, ProjectGroup>();

    displayEvents.forEach((event) => {
      // 優先使用承攬案件名稱，其次是公文號，最後是「一般待辦」
      const projectKey = event.contract_project_name || event.doc_number || '一般待辦';
      const projectName = event.contract_project_name || event.doc_number || '一般待辦';

      if (!projectMap.has(projectKey)) {
        projectMap.set(projectKey, {
          key: projectKey,
          projectName,
          docNumber: event.doc_number,
          documentId: event.document_id,
          events: [],
          timeStatuses: [],
          overdueCount: 0,
          todayCount: 0,
          thisWeekCount: 0,
          upcomingCount: 0,
        });
      }

      const group = projectMap.get(projectKey)!;
      group.events.push(event);

      const timeStatus = getTimeStatus(event);
      if (!group.timeStatuses.includes(timeStatus)) {
        group.timeStatuses.push(timeStatus);
      }

      switch (timeStatus) {
        case 'overdue':
          group.overdueCount++;
          break;
        case 'today':
          group.todayCount++;
          break;
        case 'thisWeek':
          group.thisWeekCount++;
          break;
        case 'upcoming':
          group.upcomingCount++;
          break;
      }
    });

    // 排序：有逾期的優先，然後按案件名稱
    return Array.from(projectMap.values()).sort((a, b) => {
      if (a.overdueCount > 0 && b.overdueCount === 0) return -1;
      if (a.overdueCount === 0 && b.overdueCount > 0) return 1;
      if (a.todayCount > 0 && b.todayCount === 0) return -1;
      if (a.todayCount === 0 && b.todayCount > 0) return 1;
      return a.projectName.localeCompare(b.projectName);
    });
  }, [displayEvents]);

  // 選中日期的事件
  const selectedDateEvents = useMemo(() => {
    return allEvents.filter((event) =>
      dayjs(event.start_datetime).isSame(selectedDate, 'day')
    );
  }, [allEvents, selectedDate]);

  // 有事件的日期集合
  const eventDatesSet = useMemo(() => {
    const dates = new Set<string>();
    allEvents.forEach((event) => {
      dates.add(dayjs(event.start_datetime).format('YYYY-MM-DD'));
    });
    return dates;
  }, [allEvents]);

  // ============================================================================
  // 事件處理
  // ============================================================================

  const handleViewDocument = (documentId: number) => {
    navigate(`/documents/${documentId}`);
  };

  const handleViewMore = () => {
    navigate('/calendar');
  };

  const handleFilterClick = (filter: DashboardQuickFilter) => {
    // 點擊快速篩選時，取消日期篩選模式
    setDateFilterActive(false);
    if (filter === quickFilter) {
      setQuickFilter(null);
    } else {
      setQuickFilter(filter);
    }
  };

  const handleDateSelect = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const hasEvents = eventDatesSet.has(dateStr);

    if (hasEvents) {
      // 點擊有事件的日期
      if (dateFilterActive && selectedDate.isSame(date, 'day')) {
        // 再次點擊相同日期，取消篩選
        setDateFilterActive(false);
      } else {
        // 啟用日期篩選模式
        setSelectedDate(date);
        setDateFilterActive(true);
        setQuickFilter(null); // 清除快速篩選
      }
    } else {
      // 點擊無事件的日期，只更新選中狀態
      setSelectedDate(date);
      setDateFilterActive(false);
    }
  };

  // 清除日期篩選
  const handleClearDateFilter = () => {
    setDateFilterActive(false);
  };

  // 月曆日期渲染
  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const hasEvents = eventDatesSet.has(dateStr);

    if (!hasEvents) return null;

    const dayEvents = allEvents.filter((e) =>
      dayjs(e.start_datetime).format('YYYY-MM-DD') === dateStr
    );
    const overdueCount = dayEvents.filter(
      (e) => e.status === 'pending' && dayjs(e.start_datetime).isBefore(dayjs(), 'day')
    ).length;

    return (
      <Badge
        count={dayEvents.length}
        size="small"
        style={{ backgroundColor: overdueCount > 0 ? '#ff4d4f' : '#1890ff' }}
      />
    );
  };

  const cellRender: CalendarProps<Dayjs>['cellRender'] = (current, info) => {
    if (info.type === 'date') return dateCellRender(current);
    return info.originNode;
  };

  // ============================================================================
  // 渲染
  // ============================================================================

  const renderProjectList = () => {
    if (projectGroups.length === 0) {
      let description = '目前沒有待辦事項';
      if (dateFilterActive) {
        description = `${selectedDate.format('MM/DD')} 沒有事件`;
      } else if (quickFilter) {
        description = `沒有${getFilterLabel(quickFilter)}的事件`;
      }
      return (
        <Empty
          description={description}
          style={{ padding: '40px 0' }}
        />
      );
    }

    return (
      <>
        {projectGroups.map((project) => (
          <ProjectCard
            key={project.key}
            project={project}
            onViewDocument={handleViewDocument}
            compact={isMobile}
          />
        ))}
      </>
    );
  };

  // ============================================================================
  // 主渲染
  // ============================================================================

  return (
    <Spin spinning={isLoading}>
      <Row gutter={[16, 16]}>
        {/* 左側：日曆 Card */}
        <Col xs={24} md={24} lg={8} xl={7}>
          <Card
            title={
              <Space>
                <CalendarOutlined />
                <span>行事曆</span>
              </Space>
            }
            size="small"
            styles={{ body: { padding: 0 } }}
          >
            <Calendar
              fullscreen={false}
              value={selectedDate}
              onSelect={handleDateSelect}
              cellRender={cellRender}
              headerRender={({ value, onChange }) => (
                <div
                  style={{
                    padding: '10px 16px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#fafafa',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                >
                  <Button
                    size="small"
                    type="text"
                    icon={<LeftOutlined />}
                    onClick={() => onChange(value.subtract(1, 'month'))}
                  />
                  <Text strong style={{ fontSize: 13 }}>{value.format('YYYY年 MM月')}</Text>
                  <Button
                    size="small"
                    type="text"
                    icon={<RightOutlined />}
                    onClick={() => onChange(value.add(1, 'month'))}
                  />
                </div>
              )}
            />
            {/* 選中日期摘要 */}
            <div
              style={{
                padding: '10px 16px',
                borderTop: '1px solid #f0f0f0',
                background: dateFilterActive
                  ? '#e6fffb'  // 篩選模式：青綠色
                  : selectedDate.isSame(dayjs(), 'day')
                    ? '#e6f7ff'
                    : '#fafafa',
                cursor: selectedDateEvents.length > 0 ? 'pointer' : 'default',
              }}
              onClick={() => {
                if (selectedDateEvents.length > 0) {
                  handleDateSelect(selectedDate);
                }
              }}
            >
              <Space>
                <Text strong style={{ fontSize: 13 }}>
                  {selectedDate.isSame(dayjs(), 'day')
                    ? '今日'
                    : selectedDate.format('MM/DD (ddd)')}
                </Text>
                {selectedDateEvents.length > 0 ? (
                  <Tag
                    color={dateFilterActive ? 'cyan' : 'blue'}
                    style={{ margin: 0, cursor: 'pointer' }}
                  >
                    {selectedDateEvents.length} 個事件
                    {!dateFilterActive && ' (點擊篩選)'}
                  </Tag>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>無事件</Text>
                )}
              </Space>
            </div>
          </Card>
        </Col>

        {/* 右側：待辦事項 Card */}
        <Col xs={24} md={24} lg={16} xl={17}>
          <Card
            title={
              <Space>
                <BellOutlined />
                <span>{isMobile ? '待辦事項' : '承攬案件待辦事項'}</span>
                {dateFilterActive && (
                  <Tag color="cyan" closable onClose={handleClearDateFilter}>
                    {selectedDate.format('MM/DD')} ({selectedDateEvents.length})
                  </Tag>
                )}
                {!dateFilterActive && quickFilter && (
                  <Tag color="blue" closable onClose={() => setQuickFilter(null)}>
                    {getFilterLabel(quickFilter)}
                  </Tag>
                )}
              </Space>
            }
            size="small"
            extra={
              <Button type="link" onClick={handleViewMore} size="small">
                完整行事曆 <RightOutlined />
              </Button>
            }
            styles={{ body: { padding: isMobile ? 12 : 16 } }}
          >
            {/* 快速篩選 */}
            <div style={{ marginBottom: 12 }}>
              <Space wrap size={isMobile ? 4 : 8}>
                <Button
                  type={quickFilter === 'all' ? 'primary' : 'default'}
                  size="small"
                  onClick={() => handleFilterClick('all')}
                >
                  <CalendarOutlined />
                  全部
                  <Badge
                    count={statistics.total}
                    size="small"
                    style={{ marginLeft: 4, backgroundColor: '#1890ff' }}
                  />
                </Button>
                <Button
                  type={quickFilter === 'today' ? 'primary' : 'default'}
                  size="small"
                  onClick={() => handleFilterClick('today')}
                  style={quickFilter === 'today' ? { background: '#52c41a', borderColor: '#52c41a' } : {}}
                >
                  <ClockCircleOutlined />
                  今日
                  <Badge
                    count={statistics.today}
                    size="small"
                    style={{ marginLeft: 4, backgroundColor: '#52c41a' }}
                  />
                </Button>
                <Button
                  type={quickFilter === 'thisWeek' ? 'primary' : 'default'}
                  size="small"
                  onClick={() => handleFilterClick('thisWeek')}
                  style={quickFilter === 'thisWeek' ? { background: '#faad14', borderColor: '#faad14' } : {}}
                >
                  <CalendarOutlined />
                  本週
                  <Badge
                    count={statistics.thisWeek}
                    size="small"
                    style={{ marginLeft: 4, backgroundColor: '#faad14' }}
                  />
                </Button>
                <Button
                  type={quickFilter === 'upcoming' ? 'primary' : 'default'}
                  size="small"
                  onClick={() => handleFilterClick('upcoming')}
                  style={quickFilter === 'upcoming' ? { background: '#722ed1', borderColor: '#722ed1' } : {}}
                >
                  <BellOutlined />
                  即將
                  <Badge
                    count={statistics.upcoming}
                    size="small"
                    style={{ marginLeft: 4, backgroundColor: '#722ed1' }}
                  />
                </Button>
              </Space>
            </div>

            {/* 案件列表 */}
            {renderProjectList()}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default DashboardCalendarSection;
