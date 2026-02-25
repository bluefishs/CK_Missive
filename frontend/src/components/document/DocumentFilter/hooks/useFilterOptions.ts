/**
 * useFilterOptions Hook
 *
 * 負責從 API 獲取篩選選項資料
 *
 * @version 1.1.0 - 統一使用 apiClient 取代 raw fetch
 * @date 2026-02-25
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../../../../api/client';
import { API_ENDPOINTS } from '../../../../api/endpoints';
import { logger } from '../../../../utils/logger';
import type {
  DropdownOption,
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
 * 獲取篩選選項的 Hook
 */
export function useFilterOptions(): FilterOptionsData {
  const [yearOptions, setYearOptions] = useState<DropdownOption[]>([]);
  const [contractCaseOptions, setContractCaseOptions] = useState<DropdownOption[]>([]);
  const [senderOptions, setSenderOptions] = useState<DropdownOption[]>([]);
  const [receiverOptions, setReceiverOptions] = useState<DropdownOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // 獲取年度選項
  const fetchYearOptions = useCallback(async () => {
    try {
      const data = await apiClient.post<YearsResponse>(
        API_ENDPOINTS.DOCUMENTS.YEARS,
        {}
      );
      const options = (data.years || []).map((year) => ({
        value: String(year),
        label: `${year}年`
      }));
      setYearOptions(options);
    } catch (error) {
      logger.error('獲取年度選項失敗:', error);
    }
  }, []);

  // 獲取承攬案件下拉選項
  const fetchContractCaseOptions = useCallback(async () => {
    try {
      // 先嘗試新的增強版 API
      const data = await apiClient.post<ContractProjectsDropdownResponse>(
        API_ENDPOINTS.DOCUMENTS.CONTRACT_PROJECTS_DROPDOWN,
        { limit: 100 }
      );
      const options = (data.options || []).map((option) => ({
        value: option.value,
        label: option.label
      }));
      setContractCaseOptions(options);
      logger.debug('成功從 contract_projects 表載入承攬案件選項:', options.length);
    } catch {
      // 降級方案
      try {
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
            label: contractCase
          }));
        setContractCaseOptions(contractCases);
        logger.debug('從公文表載入承攬案件選項:', contractCases.length);
      } catch (fallbackError) {
        logger.error('獲取承攬案件選項失敗:', fallbackError);
      }
    }
  }, []);

  // 獲取機關下拉選項 (共用邏輯)
  const fetchAgencyOptions = useCallback(async (
    setter: React.Dispatch<React.SetStateAction<DropdownOption[]>>,
    label: string
  ) => {
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
          label: agency.label
        }));
      setter(options);
      logger.debug(`成功載入標準化${label}選項:`, options.length);
    } catch {
      // 降級方案
      try {
        logger.warn('增強版 API 不可用，使用降級方案');
        const data = await apiClient.post<DocumentListResponse>(
          API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH,
          { limit: 500 }
        );
        const documents = data.documents || [];
        const field = label === '發文單位' ? 'sender' : 'receiver';
        const options = documents
          .map((doc) => (doc as Record<string, string>)[field] || '')
          .filter((value, index, arr) =>
            value && value !== '相關機關' && arr.indexOf(value) === index
          )
          .sort()
          .map((value) => ({
            value,
            label: value
          }));
        setter(options);
        logger.debug(`從公文表載入${label}選項:`, options.length);
      } catch (fallbackError) {
        logger.error(`獲取${label}選項失敗:`, fallbackError);
      }
    }
  }, []);

  // 組件載入時獲取所有選項
  useEffect(() => {
    const loadAllOptions = async () => {
      setIsLoading(true);
      await Promise.all([
        fetchYearOptions(),
        fetchContractCaseOptions(),
        fetchAgencyOptions(setSenderOptions, '發文單位'),
        fetchAgencyOptions(setReceiverOptions, '受文單位'),
      ]);
      setIsLoading(false);
    };

    loadAllOptions();
  }, [fetchYearOptions, fetchContractCaseOptions, fetchAgencyOptions]);

  return {
    yearOptions,
    contractCaseOptions,
    senderOptions,
    receiverOptions,
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
