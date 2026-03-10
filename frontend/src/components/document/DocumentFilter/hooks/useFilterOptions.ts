/**
 * useFilterOptions Hook
 *
 * 負責從 API 獲取篩選選項資料
 * 使用 React Query 管理快取，避免重複請求
 *
 * @version 2.0.0 - 重構為 React Query（修復 useEffect + 直接 API 造成的輪刷問題）
 * @date 2026-03-10
 */

import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../../../api/client';
import { API_ENDPOINTS } from '../../../../api/endpoints';
import { defaultQueryOptions } from '../../../../config/queryConfig';
import { logger } from '../../../../utils/logger';
import type {
  FilterOptionsData,
  AgenciesDropdownResponse,
  ContractProjectsDropdownResponse,
  YearsResponse,
} from '../types';

/** 公文列表 API 回應 */
interface DocumentListResponse {
  items?: Array<{ subject?: string; doc_number?: string; contract_case?: string; sender?: string; receiver?: string }>;
  documents?: Array<{ contract_case?: string; sender?: string; receiver?: string }>;
  total?: number;
}

/**
 * 獲取篩選選項的 Hook（React Query 版）
 *
 * 使用 dropdown 快取策略：staleTime 10 分鐘，refetchOnMount: false
 * 避免每次元件渲染都重新請求
 */
export function useFilterOptions(): FilterOptionsData {
  // 年度選項
  const { data: yearOptions = [], isLoading: yearLoading } = useQuery({
    queryKey: ['documents', 'filter-options', 'years'],
    queryFn: async () => {
      const data = await apiClient.post<YearsResponse>(
        API_ENDPOINTS.DOCUMENTS.YEARS,
        {}
      );
      return (data.years || []).map((year) => ({
        value: String(year),
        label: `${year}年`,
      }));
    },
    ...defaultQueryOptions.dropdown,
  });

  // 承攬案件下拉選項
  const { data: contractCaseOptions = [], isLoading: contractLoading } = useQuery({
    queryKey: ['documents', 'filter-options', 'contract-projects'],
    queryFn: async () => {
      try {
        const data = await apiClient.post<ContractProjectsDropdownResponse>(
          API_ENDPOINTS.DOCUMENTS.CONTRACT_PROJECTS_DROPDOWN,
          { limit: 100 }
        );
        const options = (data.options || []).map((option) => ({
          value: option.value,
          label: option.label,
        }));
        logger.debug('成功從 contract_projects 表載入承攬案件選項:', options.length);
        return options;
      } catch {
        // 降級方案
        logger.warn('增強版 API 不可用，使用降級方案');
        const data = await apiClient.post<DocumentListResponse>(
          API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH,
          { limit: 100 }
        );
        const documents = data.documents || [];
        const contractCases = documents
          .map((doc) => doc.contract_case || '')
          .filter((contractCase, index, arr) =>
            contractCase && arr.indexOf(contractCase) === index
          )
          .sort()
          .map((contractCase) => ({
            value: contractCase,
            label: contractCase,
          }));
        logger.debug('從公文表載入承攬案件選項:', contractCases.length);
        return contractCases;
      }
    },
    ...defaultQueryOptions.dropdown,
  });

  // 機關下拉選項（sender + receiver 共用同一查詢，避免重複請求）
  const { data: agencyOptions = [], isLoading: agencyLoading } = useQuery({
    queryKey: ['documents', 'filter-options', 'agencies'],
    queryFn: async () => {
      try {
        const data = await apiClient.post<AgenciesDropdownResponse>(
          API_ENDPOINTS.DOCUMENTS.AGENCIES_DROPDOWN,
          { limit: 500 }
        );
        const agencies = data.options || [];
        const options = agencies
          .filter((agency) => agency.value !== '相關機關')
          .map((agency) => ({
            value: agency.value,
            label: agency.label,
          }));
        logger.debug('成功載入標準化機關選項:', options.length);
        return options;
      } catch {
        // 降級方案
        logger.warn('增強版 API 不可用，使用降級方案');
        const data = await apiClient.post<DocumentListResponse>(
          API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH,
          { limit: 500 }
        );
        const documents = data.documents || [];
        const options = documents
          .map((doc) => doc.sender || '')
          .concat(documents.map((doc) => doc.receiver || ''))
          .filter((value, index, arr) =>
            value && value !== '相關機關' && arr.indexOf(value) === index
          )
          .sort()
          .map((value) => ({
            value,
            label: value,
          }));
        logger.debug('從公文表載入機關選項:', options.length);
        return options;
      }
    },
    ...defaultQueryOptions.dropdown,
  });

  const isLoading = yearLoading || contractLoading || agencyLoading;

  return {
    yearOptions,
    contractCaseOptions,
    senderOptions: agencyOptions,
    receiverOptions: agencyOptions,
    isLoading,
  };
}

/**
 * 獲取 AutoComplete 建議的 Hook
 */
export function useAutocompleteSuggestions() {
  const [searchOptions, setSearchOptions] = useState<{ value: string }[]>([]);
  const [docNumberOptions, setDocNumberOptions] = useState<{ value: string }[]>([]);

  // 獲取主旨搜尋建議
  const fetchSearchSuggestions = useCallback(async (query: string) => {
    if (query.length < 2) {
      setSearchOptions([]);
      return;
    }

    try {
      const data = await apiClient.post<DocumentListResponse>(
        API_ENDPOINTS.DOCUMENTS.LIST,
        { keyword: query, limit: 50, page: 1 }
      );
      const documents = data.items || [];
      const suggestions = documents
        .map((doc) => doc.subject || '')
        .filter((subject, index, arr) =>
          subject && arr.indexOf(subject) === index
        )
        .slice(0, 10)
        .map((subject) => ({ value: subject }));
      setSearchOptions(suggestions);
    } catch (error) {
      logger.error('獲取搜尋建議失敗:', error);
    }
  }, []);

  // 獲取公文字號建議
  const fetchDocNumberSuggestions = useCallback(async (query: string) => {
    if (query.length < 2) {
      setDocNumberOptions([]);
      return;
    }

    try {
      const data = await apiClient.post<DocumentListResponse>(
        API_ENDPOINTS.DOCUMENTS.LIST,
        { keyword: query, limit: 100, page: 1 }
      );
      const documents = data.items || [];

      if (Array.isArray(documents)) {
        const docNumbers = documents
          .map((doc) => doc.doc_number || '')
          .filter((docNumber, index, arr) =>
            docNumber && docNumber?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(docNumber) === index
          )
          .map((docNumber) => ({ value: docNumber }));
        setDocNumberOptions(docNumbers.slice(0, 10));
      } else {
        logger.warn('API 回應不包含有效的文件陣列:', data);
        setDocNumberOptions([]);
      }
    } catch (error) {
      logger.error('獲取公文字號建議失敗:', error);
      setDocNumberOptions([]);
    }
  }, []);

  return {
    searchOptions,
    docNumberOptions,
    fetchSearchSuggestions,
    fetchDocNumberSuggestions,
  };
}
