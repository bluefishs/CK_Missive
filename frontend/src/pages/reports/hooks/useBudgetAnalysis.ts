/**
 * 經費分析 Hook
 *
 * 管理經費分析 Tab 的所有狀態與資料邏輯：
 * - 年度選擇與資料載入（分頁取全部）
 * - 三維篩選（案件類別/執行狀態/委託單位）
 * - 統計計算（useMemo）
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { App } from 'antd';
import { projectsApi } from '../../../api/projectsApi';
import type { Project } from '../../../types/api';
import {
  EXCLUDED_STATUSES,
  normalizeName,
  getCategoryDisplayName,
  getStatusDisplayName,
} from '../constants';

interface AgencyStats {
  name: string;
  count: number;
  amount: number;
  projects: Project[];
}

interface CategoryStats {
  name: string;
  count: number;
  amount: number;
}

interface StatusStats {
  name: string;
  count: number;
  amount: number;
}

export interface BudgetStats {
  totalProjects: number;
  totalAmount: number;
  uniqueAgencyCount: number;
  byAgency: AgencyStats[];
  byCategory: CategoryStats[];
  byStatus: StatusStats[];
}

export interface AllStats {
  categories: string[];
  statuses: string[];
  agencies: string[];
  totalCount: number;
}

export interface UseBudgetAnalysisReturn {
  loading: boolean;
  selectedYear: number | 'all' | null;
  setSelectedYear: (year: number | 'all') => void;
  yearOptions: number[];
  projects: Project[];
  filteredProjects: Project[];
  stats: BudgetStats;
  allStats: AllStats;
  filterCategory: string | null;
  setFilterCategory: (v: string | null) => void;
  filterStatus: string | null;
  setFilterStatus: (v: string | null) => void;
  filterAgency: string | null;
  setFilterAgency: (v: string | null) => void;
  hasFilter: boolean;
  clearAllFilters: () => void;
  handleCategoryClick: (name: string) => void;
  handleStatusClick: (name: string) => void;
  handleAgencyClick: (name: string) => void;
}

export function useBudgetAnalysis(): UseBudgetAnalysisReturn {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  // 初始值改為 null，表示尚未載入年度選項
  const [selectedYear, setSelectedYear] = useState<number | 'all' | null>(null);
  const [yearOptions, setYearOptions] = useState<number[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);

  // 三維篩選狀態
  const [filterCategory, setFilterCategory] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [filterAgency, setFilterAgency] = useState<string | null>(null);

  // 載入年度選項
  useEffect(() => {
    const loadYears = async () => {
      try {
        const years = await projectsApi.getYearOptions();
        setYearOptions(years.sort((a, b) => b - a));
        // 預設選擇最新年度
        if (years.length > 0 && years[0] !== undefined) {
          setSelectedYear(years[0]);
        } else {
          setSelectedYear('all');
        }
      } catch (error) {
        console.error('載入年度選項失敗:', error);
        setSelectedYear('all');
      }
    };
    loadYears();
  }, []);

  // 載入承攬案件資料（分頁獲取全部）
  const loadProjects = useCallback(async () => {
    // 等待年度選項載入完成
    if (selectedYear === null) return;

    setLoading(true);
    try {
      const params: { year?: number; limit: number; page: number } = { limit: 100, page: 1 };
      // 只有選擇具體年度時才傳遞 year 參數
      if (typeof selectedYear === 'number') {
        params.year = selectedYear;
      }

      const firstResponse = await projectsApi.getProjects(params);
      let allItems = [...firstResponse.items];

      const totalPages = firstResponse.pagination.total_pages;
      for (let page = 2; page <= totalPages && page <= 10; page++) {
        const response = await projectsApi.getProjects({ ...params, page });
        allItems = [...allItems, ...response.items];
      }

      setProjects(allItems);
      // 重置篩選條件
      setFilterCategory(null);
      setFilterStatus(null);
      setFilterAgency(null);
    } catch (error) {
      console.error('載入承攬案件失敗:', error);
      message.error('載入資料失敗');
    } finally {
      setLoading(false);
    }
  }, [selectedYear, message]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const hasFilter = !!(filterCategory || filterStatus || filterAgency);

  const clearAllFilters = () => {
    setFilterCategory(null);
    setFilterStatus(null);
    setFilterAgency(null);
  };

  // 排除不納入統計的案件
  const validProjects = useMemo(() => {
    return projects.filter((p) => {
      const status = normalizeName(p.status) || '未設定';
      return !EXCLUDED_STATUSES.includes(status);
    });
  }, [projects]);

  // 根據篩選條件過濾
  const filteredProjects = useMemo(() => {
    return validProjects.filter((p) => {
      if (filterCategory) {
        const rawCat = normalizeName(p.category) || '未分類';
        const cat = getCategoryDisplayName(rawCat);
        if (cat !== filterCategory) return false;
      }
      if (filterStatus) {
        const status = getStatusDisplayName(normalizeName(p.status) || '未設定');
        if (status !== filterStatus) return false;
      }
      if (filterAgency) {
        const agency = normalizeName(p.client_agency) || '未指定單位';
        if (agency !== filterAgency) return false;
      }
      return true;
    });
  }, [validProjects, filterCategory, filterStatus, filterAgency]);

  // 全量統計（用於顯示選項）
  const allStats = useMemo((): AllStats => {
    const categories = new Set<string>();
    const statuses = new Set<string>();
    const agencies = new Set<string>();

    validProjects.forEach((p) => {
      const rawCategory = normalizeName(p.category) || '未分類';
      categories.add(getCategoryDisplayName(rawCategory));
      statuses.add(getStatusDisplayName(normalizeName(p.status) || '未設定'));
      agencies.add(normalizeName(p.client_agency) || '未指定單位');
    });

    return {
      categories: Array.from(categories).sort(),
      statuses: Array.from(statuses).sort(),
      agencies: Array.from(agencies).sort(),
      totalCount: validProjects.length,
    };
  }, [validProjects]);

  // 篩選後統計
  const stats = useMemo((): BudgetStats => {
    const totalAmount = filteredProjects.reduce((sum, p) => sum + (p.contract_amount || 0), 0);

    const byAgency: Record<string, { count: number; amount: number; projects: Project[] }> = {};
    filteredProjects.forEach((p) => {
      const agency = normalizeName(p.client_agency) || '未指定單位';
      if (!byAgency[agency]) {
        byAgency[agency] = { count: 0, amount: 0, projects: [] };
      }
      byAgency[agency].count++;
      byAgency[agency].amount += p.contract_amount || 0;
      byAgency[agency].projects.push(p);
    });

    const byCategory: Record<string, { count: number; amount: number }> = {};
    filteredProjects.forEach((p) => {
      const rawCategory = normalizeName(p.category) || '未分類';
      const category = getCategoryDisplayName(rawCategory);
      if (!byCategory[category]) {
        byCategory[category] = { count: 0, amount: 0 };
      }
      byCategory[category].count++;
      byCategory[category].amount += p.contract_amount || 0;
    });

    const byStatus: Record<string, { count: number; amount: number }> = {};
    filteredProjects.forEach((p) => {
      const status = getStatusDisplayName(normalizeName(p.status) || '未設定');
      if (!byStatus[status]) {
        byStatus[status] = { count: 0, amount: 0 };
      }
      byStatus[status].count++;
      byStatus[status].amount += p.contract_amount || 0;
    });

    const uniqueAgencyCount = Object.keys(byAgency).length;

    return {
      totalProjects: filteredProjects.length,
      totalAmount,
      uniqueAgencyCount,
      byAgency: Object.entries(byAgency)
        .map(([name, data]) => ({ name, ...data }))
        .sort((a, b) => b.amount - a.amount),
      byCategory: Object.entries(byCategory)
        .map(([name, data]) => ({ name, ...data }))
        .sort((a, b) => b.amount - a.amount),
      byStatus: Object.entries(byStatus)
        .map(([name, data]) => ({ name, ...data }))
        .sort((a, b) => b.count - a.count),
    };
  }, [filteredProjects]);

  const handleCategoryClick = (categoryName: string) => {
    setFilterCategory(filterCategory === categoryName ? null : categoryName);
  };

  const handleStatusClick = (statusName: string) => {
    setFilterStatus(filterStatus === statusName ? null : statusName);
  };

  const handleAgencyClick = (agencyName: string) => {
    setFilterAgency(filterAgency === agencyName ? null : agencyName);
  };

  return {
    loading,
    selectedYear,
    setSelectedYear,
    yearOptions,
    projects,
    filteredProjects,
    stats,
    allStats,
    filterCategory,
    setFilterCategory,
    filterStatus,
    setFilterStatus,
    filterAgency,
    setFilterAgency,
    hasFilter,
    clearAllFilters,
    handleCategoryClick,
    handleStatusClick,
    handleAgencyClick,
  };
}
