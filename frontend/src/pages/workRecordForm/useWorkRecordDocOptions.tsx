/**
 * WorkRecordFormPage — 公文選項 Hook
 *
 * 管理公文搜尋、已關聯公文、搜尋結果的合併與選項生成
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import React, { useMemo, useState } from 'react';
import { Tag, Tooltip } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import { isReceiveDocument } from '../../types/api';
import type { DispatchDocumentLink } from '../../types/taoyuan';
import type { WorkRecord } from '../../types/taoyuan';

interface DocOption {
  value: number;
  label: React.ReactNode;
  searchText: string;
}

export function useWorkRecordDocOptions(
  dispatchOrderId: number,
  record: WorkRecord | undefined,
) {
  const [docSearchKeyword, setDocSearchKeyword] = useState('');

  const { data: linkedDocs } = useQuery({
    queryKey: ['dispatch-documents', dispatchOrderId],
    queryFn: async () => {
      const resp = await apiClient.post<{ items: DispatchDocumentLink[] }>(
        API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_DOCUMENTS(dispatchOrderId),
      );
      return resp.items ?? [];
    },
    enabled: dispatchOrderId > 0,
  });

  const { data: searchedDocsResult, isLoading: searchingDocs } = useQuery({
    queryKey: ['documents-for-work-record', docSearchKeyword],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return { items: [] };
      return dispatchOrdersApi.searchLinkableDocuments(
        docSearchKeyword,
        20,
      );
    },
    enabled: !!docSearchKeyword.trim(),
  });

  const docOptions = useMemo(() => {
    const seenIds = new Set<number>();
    const options: DocOption[] = [];

    // 當前紀錄已選的公文
    if (record?.document_id && record.document) {
      seenIds.add(record.document_id);
      const doc = record.document;
      const isOutgoing = doc.doc_number?.startsWith('乾坤');
      const tag = isOutgoing ? '發' : '收';
      const color = isOutgoing ? 'green' : 'blue';
      const docNumber = doc.doc_number || `#${record.document_id}`;
      const subject = doc.subject || '';
      options.push({
        value: record.document_id,
        label: (
          <Tooltip title={subject} placement="right" mouseEnterDelay={0.5}>
            <span>
              <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
              {docNumber}
              {doc.doc_date ? ` (${doc.doc_date.substring(0, 10)})` : ''}
            </span>
          </Tooltip>
        ),
        searchText: `${doc.doc_number || ''} ${subject}`,
      });
    }

    // 已關聯公文
    if (linkedDocs) {
      for (const d of linkedDocs) {
        if (seenIds.has(d.document_id)) continue;
        seenIds.add(d.document_id);
        const isOutgoing = d.doc_number?.startsWith('乾坤');
        const tag = isOutgoing ? '發' : '收';
        const color = isOutgoing ? 'green' : 'blue';
        const docNumber = d.doc_number || `ID:${d.document_id}`;
        const subject = d.subject || '';
        options.push({
          value: d.document_id,
          label: (
            <Tooltip
              title={subject}
              placement="right"
              mouseEnterDelay={0.5}
            >
              <span>
                <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
                {docNumber}
                {d.doc_date ? ` (${d.doc_date.substring(0, 10)})` : ''}
              </span>
            </Tooltip>
          ),
          searchText: `${d.doc_number || ''} ${subject}`,
        });
      }
    }

    // 搜尋結果
    const searchedDocs = searchedDocsResult?.items ?? [];
    for (const d of searchedDocs) {
      if (seenIds.has(d.id)) continue;
      seenIds.add(d.id);
      const docIsReceive = isReceiveDocument(d.category);
      const tag = docIsReceive ? '收' : '發';
      const color = docIsReceive ? 'blue' : 'green';
      const docNumber = d.doc_number || `#${d.id}`;
      const subject = d.subject || '(無主旨)';
      options.push({
        value: d.id,
        label: (
          <Tooltip
            title={<div><div>{docNumber}</div><div>{subject}</div></div>}
            placement="right"
            mouseEnterDelay={0.5}
          >
            <span>
              <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
              {docNumber}
              {d.doc_date ? ` (${d.doc_date.substring(0, 10)})` : ''}
              <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                {subject.length > 20 ? subject.substring(0, 20) + '...' : subject}
              </span>
            </span>
          </Tooltip>
        ),
        searchText: `${d.doc_number || ''} ${subject}`,
      });
    }

    return options;
  }, [record, linkedDocs, searchedDocsResult?.items]);

  return {
    docOptions,
    linkedDocs,
    searchedDocsResult,
    docSearchKeyword,
    setDocSearchKeyword,
    searchingDocs,
  };
}
