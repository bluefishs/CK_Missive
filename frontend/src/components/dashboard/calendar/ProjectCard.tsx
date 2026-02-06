/**
 * 案件卡片元件（含事件項目）
 */

import React, { useState } from 'react';
import { Typography, Tag, Button, Space, Badge, Tooltip } from 'antd';
import {
  FolderOpenOutlined,
  FileTextOutlined,
  FieldTimeOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CalendarEvent } from '../../../api/calendarApi';
import {
  EVENT_TYPE_CONFIG,
  PRIORITY_CONFIG,
} from '../../../hooks/system/useDashboardCalendar';
import type { ProjectGroup } from './types';
import { getTimeStatus } from './types';
import { TimeStatusTag } from './TimeStatusTag';

const { Text } = Typography;

const EventItemInner: React.FC<{
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

const EventItem = React.memo(EventItemInner);

const ProjectCardInner: React.FC<{
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

export const ProjectCard = React.memo(ProjectCardInner);
