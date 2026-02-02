/**
 * 公文數量分析 Hook
 *
 * 管理公文數量分析 Tab 的所有狀態與資料邏輯：
 * - 年度選擇與資料載入（分頁取全部）
 * - 收發文統計計算
 * - 來文機關/受文者排名
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { App } from 'antd';
import { documentsApi } from '../../../api/documentsApi';
import type { OfficialDocument } from '../../../types/api';
import { isReceiveDocument, isSendDocument } from '../../../types/api';
import { extractAgencyList } from '../constants';
import { logger } from '../../../services/logger';

interface NameCount {
  name: string;
  count: number;
}

interface TypeCount {
  name: string;
  value: number;
}

export interface DocumentStats {
  totalDocuments: number;
  sendCount: number;
  receiveCount: number;
  bySender: NameCount[];
  byReceiver: NameCount[];
  byType: TypeCount[];
}

export interface UseDocumentAnalysisReturn {
  loading: boolean;
  selectedYear: number | 'all' | null;
  setSelectedYear: (year: number | 'all') => void;
  yearOptions: number[];
  documents: OfficialDocument[];
  stats: DocumentStats;
}

export function useDocumentAnalysis(): UseDocumentAnalysisReturn {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(true);
  // 初始值改為 null，表示尚未載入年度選項
  const [selectedYear, setSelectedYear] = useState<number | 'all' | null>(null);
  const [yearOptions, setYearOptions] = useState<number[]>([]);
  const [documents, setDocuments] = useState<OfficialDocument[]>([]);

  // 載入年度選項
  useEffect(() => {
    const loadYears = async () => {
      try {
        const years = await documentsApi.getYearOptions();
        setYearOptions(years.sort((a, b) => b - a));
        // 預設選擇最新年度
        if (years.length > 0 && years[0] !== undefined) {
          setSelectedYear(years[0]);
        } else {
          // 無年度資料時設為 'all'
          setSelectedYear('all');
        }
      } catch (error) {
        logger.error('載入年度選項失敗:', error);
        setSelectedYear('all');
      }
    };
    loadYears();
  }, []);

  // 載入公文資料（分頁獲取全部）
  const loadDocuments = useCallback(async () => {
    // 等待年度選項載入完成
    if (selectedYear === null) return;

    setLoading(true);
    try {
      const params: { year?: number; limit: number; page: number } = { limit: 100, page: 1 };
      // 只有選擇具體年度時才傳遞 year 參數
      if (typeof selectedYear === 'number') {
        params.year = selectedYear;
      }

      const firstResponse = await documentsApi.getDocuments(params);
      let allItems = [...firstResponse.items];

      const totalPages = firstResponse.pagination.total_pages;
      for (let page = 2; page <= totalPages && page <= 20; page++) {
        const response = await documentsApi.getDocuments({ ...params, page });
        allItems = [...allItems, ...response.items];
      }

      setDocuments(allItems);
    } catch (error) {
      logger.error('載入公文資料失敗:', error);
      message.error('載入資料失敗');
    } finally {
      setLoading(false);
    }
  }, [selectedYear, message]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // 計算統計資料
  const stats = useMemo((): DocumentStats => {
    const sendDocs = documents.filter((d) => isSendDocument(d.category));
    const receiveDocs = documents.filter((d) => isReceiveDocument(d.category));

    // 來文機關統計：只統計「收文」的 sender
    // 使用 extractAgencyList 分割多單位並標準化名稱
    const bySender: Record<string, number> = {};
    receiveDocs.forEach((d) => {
      const agencies = extractAgencyList(d.sender);
      if (agencies.length === 0) {
        bySender['未指定機關'] = (bySender['未指定機關'] || 0) + 1;
      } else {
        agencies.forEach((agency) => {
          bySender[agency] = (bySender[agency] || 0) + 1;
        });
      }
    });

    // 受文者統計：只統計「發文」的 receiver
    // 使用 extractAgencyList 分割多單位並標準化名稱
    const byReceiver: Record<string, number> = {};
    sendDocs.forEach((d) => {
      const receivers = extractAgencyList(d.receiver);
      if (receivers.length === 0) {
        byReceiver['未指定受文者'] = (byReceiver['未指定受文者'] || 0) + 1;
      } else {
        receivers.forEach((receiver) => {
          byReceiver[receiver] = (byReceiver[receiver] || 0) + 1;
        });
      }
    });

    // 收發文類型分組
    const byType: Record<string, number> = {
      '收文': receiveDocs.length,
      '發文': sendDocs.length,
    };

    return {
      totalDocuments: documents.length,
      sendCount: sendDocs.length,
      receiveCount: receiveDocs.length,
      bySender: Object.entries(bySender)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
      byReceiver: Object.entries(byReceiver)
        .map(([name, count]) => ({ name, count }))
        .sort((a, b) => b.count - a.count),
      byType: Object.entries(byType)
        .map(([name, value]) => ({ name, value }))
        .filter(item => item.value > 0),
    };
  }, [documents]);

  return {
    loading,
    selectedYear,
    setSelectedYear,
    yearOptions,
    documents,
    stats,
  };
}
