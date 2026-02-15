/**
 * 儀表板行事曆區塊
 *
 * 設計原則：
 * - 消除雙滾動條，日曆與事件列表分為獨立區塊
 * - 以「承攬案件」為主要分類，附加時間狀態標籤
 * - RWD 設計：手機版垂直堆疊，桌面版並排
 *
 * @version 5.0.0 - 模組化重構：Hook + 子元件提取
 * @date 2026-01-28
 */

import React from 'react';
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
} from 'antd';
import type { CalendarProps } from 'antd';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  BellOutlined,
  RightOutlined,
  LeftOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/types';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore';
import isSameOrAfter from 'dayjs/plugin/isSameOrAfter';

dayjs.extend(isSameOrBefore);
dayjs.extend(isSameOrAfter);

import { useResponsive } from '../../hooks';
import { ProjectCard } from './calendar/ProjectCard';
import { useDashboardCalendarView } from './calendar/useDashboardCalendarView';

const { Text } = Typography;

interface DashboardCalendarSectionProps {
  maxEvents?: number;
}

export const DashboardCalendarSection: React.FC<DashboardCalendarSectionProps> = ({
  maxEvents: _maxEvents = 20,
}) => {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();

  const {
    allEvents,
    statistics,
    quickFilter,
    getFilterLabel,
    isLoading,
    selectedDate,
    dateFilterActive,
    projectGroups,
    selectedDateEvents,
    eventDatesSet,
    handleFilterClick,
    handleDateSelect,
    handleClearDateFilter,
  } = useDashboardCalendarView();

  const handleViewDocument = (documentId: number) => {
    navigate(ROUTES.DOCUMENT_DETAIL.replace(':id', String(documentId)));
  };

  const handleViewEvent = (eventId: number) => {
    navigate(ROUTES.CALENDAR_EVENT_EDIT.replace(':id', String(eventId)));
  };

  const handleViewMore = () => {
    navigate(ROUTES.CALENDAR);
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

  // 案件列表渲染
  const renderProjectList = () => {
    if (projectGroups.length === 0) {
      let description = '目前沒有待辦事項';
      if (dateFilterActive) {
        description = `${selectedDate.format('MM/DD')} 沒有事件`;
      } else if (quickFilter) {
        description = `沒有${getFilterLabel(quickFilter)}的事件`;
      }
      return <Empty description={description} style={{ padding: '40px 0' }} />;
    }

    return (
      <>
        {projectGroups.map((project) => (
          <ProjectCard
            key={project.key}
            project={project}
            onViewDocument={handleViewDocument}
            onViewEvent={handleViewEvent}
            compact={isMobile}
          />
        ))}
      </>
    );
  };

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
                  ? '#e6fffb'
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
                  <Tag color="blue" closable onClose={() => handleFilterClick(quickFilter)}>
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
                  下週
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
