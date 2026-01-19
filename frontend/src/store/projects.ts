/**
 * 專案管理 Store
 * 基於 Zustand 的專案狀態管理
 *
 * @version 1.0.0
 * @date 2026-01-19
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Project } from '../types/api';

/** 專案篩選條件 */
export interface ProjectFilter {
  search?: string;
  year?: number;
  category?: string;
  status?: string;
}

interface ProjectsState {
  // 專案列表
  projects: Project[];

  // 當前選中的專案
  selectedProject: Project | null;

  // 篩選條件
  filters: ProjectFilter;

  // 分頁資訊
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };

  // 載入狀態
  loading: boolean;

  // Actions
  setProjects: (projects: Project[]) => void;
  setSelectedProject: (project: Project | null) => void;
  setFilters: (filters: Partial<ProjectFilter>) => void;
  setPagination: (pagination: Partial<ProjectsState['pagination']>) => void;
  setLoading: (loading: boolean) => void;
  addProject: (project: Project) => void;
  updateProject: (id: number, project: Partial<Project>) => void;
  removeProject: (id: number) => void;
  resetFilters: () => void;
}

const initialFilters: ProjectFilter = {
  search: '',
};

export const useProjectsStore = create<ProjectsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      projects: [],
      selectedProject: null,
      filters: initialFilters,
      pagination: {
        page: 1,
        limit: 10,
        total: 0,
        totalPages: 0,
      },
      loading: false,

      // Actions
      setProjects: (projects) => set({ projects }),

      setSelectedProject: (selectedProject) => set({ selectedProject }),

      setFilters: (newFilters) =>
        set((state) => ({
          filters: { ...state.filters, ...newFilters },
          pagination: { ...state.pagination, page: 1 },
        })),

      setPagination: (newPagination) =>
        set((state) => ({
          pagination: { ...state.pagination, ...newPagination },
        })),

      setLoading: (loading) => set({ loading }),

      addProject: (project) =>
        set((state) => ({
          projects: [project, ...state.projects],
        })),

      updateProject: (id, updates) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === id ? ({ ...p, ...updates } as Project) : p
          ),
          selectedProject:
            state.selectedProject?.id === id
              ? ({ ...state.selectedProject, ...updates } as Project)
              : state.selectedProject,
        })),

      removeProject: (id) =>
        set((state) => ({
          projects: state.projects.filter((p) => p.id !== id),
          selectedProject:
            state.selectedProject?.id === id ? null : state.selectedProject,
        })),

      resetFilters: () =>
        set({
          filters: initialFilters,
          pagination: { ...get().pagination, page: 1 },
        }),
    }),
    { name: 'projects-store' }
  )
);

export type { ProjectsState };
