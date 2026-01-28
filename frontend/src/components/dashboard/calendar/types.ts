/**
 * 儀表板行事曆 - 型別定義與常數
 */

import dayjs from 'dayjs';
import type { CalendarEvent } from '../../../api/calendarApi';

/** 時間狀態類型 */
export type TimeStatus = 'overdue' | 'today' | 'thisWeek' | 'upcoming' | 'later';

/** 案件分組 */
export interface ProjectGroup {
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

/** 時間狀態配置 */
export const TIME_STATUS_CONFIG: Record<TimeStatus, { label: string; color: string; priority: number }> = {
  overdue: { label: '已逾期', color: '#ff4d4f', priority: 1 },
  today: { label: '今日', color: '#52c41a', priority: 2 },
  thisWeek: { label: '本週', color: '#faad14', priority: 3 },
  upcoming: { label: '下週', color: '#1890ff', priority: 4 },
  later: { label: '稍後', color: '#8c8c8c', priority: 5 },
};

/** 取得事件的時間狀態 */
export const getTimeStatus = (event: CalendarEvent): TimeStatus => {
  const today = dayjs().startOf('day');
  const eventDate = dayjs(event.start_datetime).startOf('day');
  const weekEnd = today.endOf('isoWeek');
  const nextWeekStart = weekEnd.add(1, 'day').startOf('day');
  const nextWeekEnd = nextWeekStart.add(6, 'day').endOf('day');

  if (event.status === 'pending' && eventDate.isBefore(today)) {
    return 'overdue';
  }
  if (eventDate.isSame(today, 'day')) {
    return 'today';
  }
  if (eventDate.isAfter(today) && eventDate.isSameOrBefore(weekEnd)) {
    return 'thisWeek';
  }
  if (eventDate.isSameOrAfter(nextWeekStart, 'day') && eventDate.isSameOrBefore(nextWeekEnd, 'day')) {
    return 'upcoming';
  }
  return 'later';
};
