/**
 * 行事曆整合 Hook
 * 封裝公文與行事曆整合的邏輯，提供統一的介面給組件使用
 */

import { useState, useCallback } from 'react';
import { Document } from '../../types';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';

export const useCalendarIntegration = () => {
  const [loading, setLoading] = useState(false);
  const [batchLoading, setBatchLoading] = useState(false);

  /**
   * 單一公文加入行事曆
   */
  const addToCalendar = useCallback(async (document: Document) => {
    if (loading) return false;

    setLoading(true);
    try {
      const result = await calendarIntegrationService.addDocumentToCalendar(document);
      return result.success;
    } catch (error) {
      console.error('Calendar integration hook error:', error);
      return false;
    } finally {
      setLoading(false);
    }
  }, [loading]);

  /**
   * 批量加入行事曆
   */
  const batchAddToCalendar = useCallback(async (documents: Document[]) => {
    if (batchLoading) return { successCount: 0, failedCount: 0 };

    setBatchLoading(true);
    try {
      const result = await calendarIntegrationService.batchAddDocumentsToCalendar(documents);
      return result;
    } catch (error) {
      console.error('Batch calendar integration hook error:', error);
      return { successCount: 0, failedCount: documents.length };
    } finally {
      setBatchLoading(false);
    }
  }, [batchLoading]);

  /**
   * 檢查公文是否已在行事曆中
   */
  const checkInCalendar = useCallback(async (documentId: number) => {
    try {
      return await calendarIntegrationService.isDocumentInCalendar(documentId);
    } catch (error) {
      console.error('Check calendar status error:', error);
      return false;
    }
  }, []);

  /**
   * 從行事曆移除公文
   */
  const removeFromCalendar = useCallback(async (documentId: number) => {
    try {
      return await calendarIntegrationService.removeDocumentFromCalendar(documentId);
    } catch (error) {
      console.error('Remove from calendar error:', error);
      return false;
    }
  }, []);

  return {
    loading,
    batchLoading,
    addToCalendar,
    batchAddToCalendar,
    checkInCalendar,
    removeFromCalendar,
  };
};

export default useCalendarIntegration;