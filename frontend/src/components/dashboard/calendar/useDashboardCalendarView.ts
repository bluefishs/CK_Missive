/**
 * 儀表板行事曆視圖 Hook
 *
 * 管理案件分組邏輯、日期篩選、事件計算。
 */

import { useState, useMemo } from 'react';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import type { CalendarEvent } from '../../../api/calendarApi';
import {
  useDashboardCalendar,
  type DashboardQuickFilter,
} from '../../../hooks/system/useDashboardCalendar';
import type { ProjectGroup } from './types';
import { getTimeStatus } from './types';

export interface UseDashboardCalendarViewReturn {
  // Data from useDashboardCalendar
  events: CalendarEvent[];
  allEvents: CalendarEvent[];
  statistics: { total: number; today: number; thisWeek: number; upcoming: number };
  quickFilter: DashboardQuickFilter | null;
  setQuickFilter: (filter: DashboardQuickFilter | null) => void;
  getFilterLabel: (filter: DashboardQuickFilter) => string;
  isLoading: boolean;
  // View state
  selectedDate: Dayjs;
  dateFilterActive: boolean;
  projectGroups: ProjectGroup[];
  selectedDateEvents: CalendarEvent[];
  eventDatesSet: Set<string>;
  // Handlers
  handleFilterClick: (filter: DashboardQuickFilter) => void;
  handleDateSelect: (date: Dayjs) => void;
  handleClearDateFilter: () => void;
}

export function useDashboardCalendarView(): UseDashboardCalendarViewReturn {
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
  const [dateFilterActive, setDateFilterActive] = useState(false);

  // 根據日期篩選模式決定要顯示的事件
  const displayEvents = useMemo(() => {
    if (dateFilterActive) {
      return allEvents.filter((event) =>
        dayjs(event.start_datetime).isSame(selectedDate, 'day')
      );
    }
    return events;
  }, [dateFilterActive, selectedDate, allEvents, events]);

  // 案件分組
  const projectGroups = useMemo<ProjectGroup[]>(() => {
    const projectMap = new Map<string, ProjectGroup>();

    displayEvents.forEach((event) => {
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

    // 對每個案件內的事件按日期降冪排序
    projectMap.forEach((group) => {
      group.events.sort((a, b) => {
        const dateA = dayjs(a.start_datetime);
        const dateB = dayjs(b.start_datetime);
        return dateB.valueOf() - dateA.valueOf();
      });
    });

    // 排序：有逾期的優先
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

  // 事件處理
  const handleFilterClick = (filter: DashboardQuickFilter) => {
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
      if (dateFilterActive && selectedDate.isSame(date, 'day')) {
        setDateFilterActive(false);
      } else {
        setSelectedDate(date);
        setDateFilterActive(true);
        setQuickFilter(null);
      }
    } else {
      setSelectedDate(date);
      setDateFilterActive(false);
    }
  };

  const handleClearDateFilter = () => {
    setDateFilterActive(false);
  };

  return {
    events,
    allEvents,
    statistics,
    quickFilter,
    setQuickFilter,
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
  };
}
