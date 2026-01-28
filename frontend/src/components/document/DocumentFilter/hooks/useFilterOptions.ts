/**
 * useFilterOptions Hook
 *
 * 負責從 API 獲取篩選選項資料
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../../../../api/client';
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
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/years`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (response.ok) {
        const data: YearsResponse = await response.json();
        const options = (data.years || []).map((year) => ({
          value: String(year),
          label: `${year}年`
        }));
        setYearOptions(options);
      }
    } catch (error) {
      logger.error('獲取年度選項失敗:', error);
    }
  }, []);

  // 獲取承攬案件下拉選項
  const fetchContractCaseOptions = useCallback(async () => {
    try {
      // 先嘗試新的增強版 API (使用 POST 方法)
      let response = await fetch(`${API_BASE_URL}/documents-enhanced/contract-projects-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 100 })
      });

      if (response.ok) {
        const data: ContractProjectsDropdownResponse = await response.json();
        const options = (data.options || []).map((option) => ({
          value: option.value,
          label: option.label
        }));
        setContractCaseOptions(options);
        logger.debug('成功從 contract_projects 表載入承攬案件選項:', options.length);
        return;
      }

      // 降級方案
      logger.warn('增強版 API 不可用，使用降級方案');
      response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 100 })
      });
      if (response.ok) {
        const data: DocumentListResponse = await response.json();
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
      }
    } catch (error) {
      logger.error('獲取承攬案件選項失敗:', error);
    }
  }, []);

  // 獲取機關下拉選項 (共用邏輯)
  const fetchAgencyOptions = useCallback(async (
    setter: React.Dispatch<React.SetStateAction<DropdownOption[]>>,
    label: string
  ) => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (response.ok) {
        const data: AgenciesDropdownResponse = await response.json();
        const agencies = data.options || [];
        const options = agencies
          .filter((agency) => agency.value !== '相關機關')
          .map((agency) => ({
            value: agency.value,
            label: agency.label
          }));
        setter(options);
        logger.debug(`成功載入標準化${label}選項:`, options.length);
        return;
      }

      // 降級方案
      logger.warn('增強版 API 不可用，使用降級方案');
      const fallbackResponse = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (fallbackResponse.ok) {
        const data: DocumentListResponse = await fallbackResponse.json();
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
      }
    } catch (error) {
      logger.error(`獲取${label}選項失敗:`, error);
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
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: query, limit: 50, page: 1 })
      });
      if (response.ok) {
        const data: DocumentListResponse = await response.json();
        const documents = data.items || [];
        const suggestions = documents
          .map((doc) => doc.subject || '')
          .filter((subject, index, arr) =>
            subject && arr.indexOf(subject) === index
          )
          .slice(0, 10)
          .map((subject) => ({ value: subject }));
        setSearchOptions(suggestions);
      }
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
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: query, limit: 100, page: 1 })
      });
      if (response.ok) {
        const responseData: DocumentListResponse = await response.json();
        const documents = responseData.items || [];

        if (Array.isArray(documents)) {
          const docNumbers = documents
            .map((doc) => doc.doc_number || '')
            .filter((docNumber, index, arr) =>
              docNumber && docNumber?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(docNumber) === index
            )
            .map((docNumber) => ({ value: docNumber }));
          setDocNumberOptions(docNumbers.slice(0, 10));
        } else {
          logger.warn('API 回應不包含有效的文件陣列:', responseData);
          setDocNumberOptions([]);
        }
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
