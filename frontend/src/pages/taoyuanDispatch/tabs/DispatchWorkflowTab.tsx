/**
 * 公文對照 Tab（統一公文關聯 + 作業歷程）
 *
 * 整合原「公文關聯」Tab 與「作業歷程」Tab，以公文對照矩陣為核心：
 * - 公文對照視圖：已指派公文（對應作業紀錄）+ 未指派公文（待建立紀錄）
 * - 表格視圖：里程碑平面列表
 * - 行內公文搜尋：直接在 Tab 內搜尋並關聯新公文
 * - 迷你統計：紀錄數 / 關聯公文 / 未指派 / 來文 / 發文
 * - 跨頁導航：前往工程總覽（高亮本派工單）
 * - CRUD：新增/編輯（導航）、刪除（行內）、關聯/解除公文
 *
 * @version 5.1.0 - 新增自動匹配公文功能（AutoMatchModal）
 * @date 2026-02-23
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Space,
  Empty,
  Popconfirm,
  Tooltip,
  Typography,
  App,
} from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../../config/queryConfig';
import dayjs from 'dayjs';

import { workflowApi } from '../../../api/taoyuan';
import { dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';
import type {
  WorkRecord,
  WorkRecordStatus,
  DocumentHistoryItem,
} from '../../../types/taoyuan';
import type { DispatchDocumentLink, LinkType } from '../../../types/api';
import { logger } from '../../../services/logger';

import {
  CorrespondenceBody,
  milestoneLabel,
  milestoneColor,
  statusLabel,
  statusColor,
  ChainTimeline,
  getEffectiveDoc,
  getDocDirection,
  getCategoryLabel,
  getCategoryColor,
} from '../../../components/taoyuan/workflow';
import {
  useDispatchWorkData,
  detectLinkType,
} from '../../../components/taoyuan/workflow/useDispatchWorkData';

import { StatsCards } from './workflow/StatsCards';
import { WorkflowToolBar } from './workflow/WorkflowToolBar';
import { InlineDocumentSearch } from './workflow/InlineDocumentSearch';
import { UnassignedDocumentsList } from './workflow/UnassignedDocumentsList';
import { AutoMatchModal } from './workflow/AutoMatchModal';

const { Text } = Typography;

// =============================================================================
// Types
// =============================================================================

type ViewMode = 'chain' | 'correspondence' | 'table';

/** 可關聯公文選項 */
interface LinkableDocumentOption {
  id: number;
  doc_number: string | null;
  subject: string | null;
  doc_date: string | null;
  category: string | null;
  sender: string | null;
  receiver: string | null;
}

export interface DispatchWorkflowTabProps {
  /** 派工單 ID */
  dispatchOrderId: number;
  /** 是否可編輯 */
  canEdit?: boolean;
  /** 關聯的工程 (用於「查看工程總覽」導航) */
  linkedProjects?: { project_id: number; project_name?: string }[];
  /** 已關聯的公文列表 (從派工單詳情取得) */
  linkedDocuments?: DispatchDocumentLink[];
  /** 重新取得派工單資料的 callback */
  onRefetchDispatch?: () => void;
  /** 工程名稱（用於自動匹配公文） */
  projectName?: string;
}

// =============================================================================
// 主元件
// =============================================================================

export const DispatchWorkflowTab: React.FC<DispatchWorkflowTabProps> = ({
  dispatchOrderId,
  canEdit = true,
  linkedProjects,
  linkedDocuments = [],
  onRefetchDispatch,
  projectName,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [viewMode, setViewMode] = useState<ViewMode>('chain');

  // 公文搜尋相關狀態
  const [docSearchKeyword, setDocSearchKeyword] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<number>();
  const [selectedLinkType, setSelectedLinkType] = useState<LinkType>('agency_incoming');

  // ===========================================================================
  // 統一資料
  // ===========================================================================

  const {
    records,
    stats,
    correspondenceData,
    matrixRows,
    unassignedDocs,
    isLoading,
  } = useDispatchWorkData({
    dispatchOrderId,
    linkedDocuments,
  });

  // ===========================================================================
  // 公文搜尋 Query
  // ===========================================================================

  const linkedDocIds = useMemo(
    () => linkedDocuments.map((d) => d.document_id),
    [linkedDocuments],
  );

  const { data: searchedDocsResult, isLoading: searchingDocs } = useQuery({
    queryKey: [
      'documents-for-dispatch-link',
      docSearchKeyword,
      linkedDocIds,
      selectedLinkType,
    ],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return { items: [] };
      return dispatchOrdersApi.searchLinkableDocuments(
        docSearchKeyword,
        20,
        linkedDocIds.length > 0 ? linkedDocIds : undefined,
        selectedLinkType,
      );
    },
    enabled: !!docSearchKeyword.trim(),
  });

  const availableDocs = useMemo(
    () => (searchedDocsResult?.items || []) as LinkableDocumentOption[],
    [searchedDocsResult?.items],
  );

  // ===========================================================================
  // Mutations
  // ===========================================================================

  const deleteMutation = useMutation({
    mutationFn: (id: number) => workflowApi.delete(id),
    onSuccess: () => {
      message.success('作業紀錄已刪除');
      queryClient.invalidateQueries({
        queryKey: ['dispatch-work-records', dispatchOrderId],
      });
      queryClient.invalidateQueries({
        queryKey: ['project-work-records'],
      });
    },
    onError: (error: Error) => {
      logger.error('[WorkflowTab] 刪除失敗:', error);
      message.error('刪除失敗，請稍後再試');
    },
  });

  const linkDocMutation = useMutation({
    mutationFn: (data: { documentId: number; linkType: LinkType }) =>
      dispatchOrdersApi.linkDocument(dispatchOrderId, {
        document_id: data.documentId,
        link_type: data.linkType,
      }),
    onSuccess: () => {
      message.success('公文關聯成功');
      setSelectedDocId(undefined);
      setDocSearchKeyword('');
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('關聯失敗'),
  });

  const unlinkDocMutation = useMutation({
    mutationFn: (linkId: number) =>
      dispatchOrdersApi.unlinkDocument(dispatchOrderId, linkId),
    onSuccess: () => {
      message.success('已移除公文關聯');
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('移除關聯失敗'),
  });

  // ===========================================================================
  // 自動匹配公文
  // ===========================================================================

  const [autoMatchModalOpen, setAutoMatchModalOpen] = useState(false);
  const [autoMatchResults, setAutoMatchResults] = useState<{
    agency: DocumentHistoryItem[];
    company: DocumentHistoryItem[];
  }>({ agency: [], company: [] });
  const [selectedAutoMatchIds, setSelectedAutoMatchIds] = useState<Set<number>>(new Set());

  const autoMatchMutation = useMutation({
    mutationFn: () => dispatchOrdersApi.matchDocuments(projectName || '', dispatchOrderId),
    onSuccess: (result) => {
      if (!result.success) {
        message.warning('匹配失敗');
        return;
      }
      // 過濾掉已關聯的公文
      const agency = result.agency_documents.filter((d) => !linkedDocIds.includes(d.id));
      const company = result.company_documents.filter((d) => !linkedDocIds.includes(d.id));
      if (agency.length === 0 && company.length === 0) {
        message.info('所有匹配公文皆已關聯，無需再新增');
        return;
      }
      setAutoMatchResults({ agency, company });
      setSelectedAutoMatchIds(new Set([...agency, ...company].map((d) => d.id)));
      setAutoMatchModalOpen(true);
    },
    onError: () => message.error('自動匹配失敗'),
  });

  const batchLinkMutation = useMutation({
    mutationFn: async (items: { documentId: number; linkType: LinkType }[]) => {
      let successCount = 0;
      let failCount = 0;
      for (const item of items) {
        try {
          await dispatchOrdersApi.linkDocument(dispatchOrderId, {
            document_id: item.documentId,
            link_type: item.linkType,
          });
          successCount++;
        } catch {
          failCount++;
        }
      }
      return { successCount, failCount };
    },
    onSuccess: ({ successCount, failCount }) => {
      if (failCount === 0) {
        message.success(`批次關聯完成，共 ${successCount} 筆`);
      } else {
        message.warning(`${successCount} 筆關聯成功，${failCount} 筆失敗`);
      }
      setAutoMatchModalOpen(false);
      setAutoMatchResults({ agency: [], company: [] });
      setSelectedAutoMatchIds(new Set());
      onRefetchDispatch?.();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('批次關聯失敗'),
  });

  const handleAutoMatchConfirm = useCallback(() => {
    const items: { documentId: number; linkType: LinkType }[] = [];
    for (const doc of autoMatchResults.agency) {
      if (selectedAutoMatchIds.has(doc.id)) {
        items.push({ documentId: doc.id, linkType: 'agency_incoming' });
      }
    }
    for (const doc of autoMatchResults.company) {
      if (selectedAutoMatchIds.has(doc.id)) {
        items.push({ documentId: doc.id, linkType: 'company_outgoing' });
      }
    }
    if (items.length === 0) {
      message.warning('請至少勾選一筆公文');
      return;
    }
    batchLinkMutation.mutate(items);
  }, [autoMatchResults, selectedAutoMatchIds, batchLinkMutation, message]);

  // ===========================================================================
  // Handlers
  // ===========================================================================

  const handleAdd = useCallback(() => {
    navigate(`/taoyuan/dispatch/${dispatchOrderId}/workflow/create`);
  }, [navigate, dispatchOrderId]);

  const handleEdit = useCallback(
    (record: WorkRecord) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/${record.id}/edit`,
      );
    },
    [navigate, dispatchOrderId],
  );

  const handleDocClick = useCallback(
    (docId: number) => {
      navigate(`/documents/${docId}`);
    },
    [navigate],
  );

  const handleGoToProjectOverview = useCallback(
    (projectId: number) => {
      navigate(
        `/taoyuan/project/${projectId}?tab=overview&highlight=${dispatchOrderId}`,
      );
    },
    [navigate, dispatchOrderId],
  );

  // 關聯公文
  const handleLinkDocument = useCallback(() => {
    if (!selectedDocId) {
      message.warning('請先選擇要關聯的公文');
      return;
    }
    linkDocMutation.mutate({
      documentId: selectedDocId,
      linkType: selectedLinkType,
    });
  }, [selectedDocId, selectedLinkType, linkDocMutation, message]);

  // 解除公文關聯（含 link_id 防禦性檢查）
  const handleUnlinkDocument = useCallback(
    (linkId: number | undefined) => {
      if (linkId === undefined || linkId === null) {
        message.error('關聯資料缺少 link_id，請重新整理頁面');
        onRefetchDispatch?.();
        return;
      }
      unlinkDocMutation.mutate(linkId);
    },
    [unlinkDocMutation, message, onRefetchDispatch],
  );

  // 公文選取時建議關聯類型（不覆蓋用戶手動選擇）
  const handleDocumentChange = useCallback(
    (docId: number | undefined) => {
      setSelectedDocId(docId);
      if (docId) {
        const selectedDoc = availableDocs.find((d) => d.id === docId);
        if (selectedDoc?.doc_number) {
          const detected = detectLinkType(selectedDoc.doc_number);
          if (detected !== selectedLinkType) {
            const label = detected === 'company_outgoing' ? '乾坤發文' : '機關來函';
            message.info(`依公文字號建議為「${label}」，已自動切換`);
            setSelectedLinkType(detected);
          }
        }
      }
    },
    [availableDocs, selectedLinkType, message],
  );

  // 從未指派公文快速建立作業紀錄
  const handleQuickCreateRecord = useCallback(
    (doc: DispatchDocumentLink) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/create?document_id=${doc.document_id}`,
      );
    },
    [navigate, dispatchOrderId],
  );

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  // ===========================================================================
  // Table Columns
  // ===========================================================================

  const columns: ColumnsType<WorkRecord> = useMemo(
    () => [
      {
        title: '序號',
        dataIndex: 'sort_order',
        key: 'sort_order',
        width: 50,
        align: 'center' as const,
      },
      {
        title: '類別',
        key: 'category',
        width: 90,
        render: (_: unknown, record: WorkRecord) =>
          record.work_category ? (
            <Tag color={getCategoryColor(record)}>{getCategoryLabel(record)}</Tag>
          ) : (
            <Tag color={milestoneColor(record.milestone_type)}>{milestoneLabel(record.milestone_type)}</Tag>
          ),
      },
      {
        title: '說明',
        key: 'description',
        ellipsis: true,
        render: (_: unknown, record: WorkRecord) => {
          const doc = getEffectiveDoc(record);
          const text = record.description || doc?.subject;
          if (!text) return '-';
          return (
            <Tooltip title={text}>
              <Text ellipsis style={{ maxWidth: 200 }}>{text}</Text>
            </Tooltip>
          );
        },
      },
      {
        title: '紀錄日期',
        dataIndex: 'record_date',
        key: 'record_date',
        width: 100,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '期限',
        dataIndex: 'deadline_date',
        key: 'deadline_date',
        width: 95,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '狀態',
        dataIndex: 'status',
        key: 'status',
        width: 80,
        render: (status: WorkRecordStatus) => (
          <Tag color={statusColor(status)}>{statusLabel(status)}</Tag>
        ),
      },
      {
        title: '來文',
        key: 'incoming_doc',
        width: 155,
        render: (_: unknown, record: WorkRecord) => {
          if (record.incoming_doc?.doc_number) {
            return (
              <Tooltip title={record.incoming_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.incoming_doc?.id && handleDocClick(record.incoming_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.incoming_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'incoming') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => doc.id && handleDocClick(doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          return '-';
        },
      },
      {
        title: '覆文',
        key: 'outgoing_doc',
        width: 155,
        render: (_: unknown, record: WorkRecord) => {
          if (record.outgoing_doc?.doc_number) {
            return (
              <Tooltip title={record.outgoing_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.outgoing_doc?.id && handleDocClick(record.outgoing_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.outgoing_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'outgoing') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 135, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => doc.id && handleDocClick(doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          return '-';
        },
      },
      ...(canEdit
        ? [
            {
              title: '操作',
              key: 'action',
              width: 80,
              fixed: 'right' as const,
              render: (_: unknown, record: WorkRecord) => (
                <Space size="small">
                  <Tooltip title="編輯">
                    <Button
                      type="link"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => handleEdit(record)}
                    />
                  </Tooltip>
                  <Popconfirm
                    title="確定要刪除此紀錄嗎？"
                    onConfirm={() => deleteMutation.mutate(record.id)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Tooltip title="刪除">
                      <Button
                        type="link"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                      />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              ),
            },
          ]
        : []),
    ],
    [canEdit, handleEdit, handleDocClick, deleteMutation],
  );

  // ===========================================================================
  // 公文對照視圖（含未指派區塊）
  // ===========================================================================

  const hasUnassigned = unassignedDocs.incoming.length > 0 || unassignedDocs.outgoing.length > 0;
  const hasCorrespondence =
    correspondenceData.incomingDocs.length > 0 ||
    correspondenceData.outgoingDocs.length > 0;

  const renderCorrespondenceView = () => {
    if (matrixRows.length === 0 && linkedDocuments.length === 0) {
      return (
        <Empty
          description="尚無公文關聯與作業紀錄"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: '40px 0' }}
        />
      );
    }

    return (
      <CorrespondenceBody
        data={correspondenceData}
        matrixRows={matrixRows}
        onDocClick={handleDocClick}
        onEditRecord={canEdit ? handleEdit : undefined}
        onQuickCreateRecord={canEdit ? handleQuickCreateRecord : undefined}
        canEdit={canEdit}
      />
    );
  };

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 迷你統計 */}
      <StatsCards stats={stats} />

      {/* 工具列 */}
      <WorkflowToolBar
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
        canEdit={canEdit}
        onAdd={handleAdd}
        linkedProjects={linkedProjects}
        onGoToProjectOverview={handleGoToProjectOverview}
      />

      {/* 視圖內容 */}
      {viewMode === 'chain' ? (
        <ChainTimeline
          records={records}
          onDocClick={handleDocClick}
          onEditRecord={canEdit ? handleEdit : undefined}
          onDeleteRecord={canEdit ? (id) => deleteMutation.mutate(id) : undefined}
          canEdit={canEdit}
        />
      ) : viewMode === 'correspondence' ? (
        renderCorrespondenceView()
      ) : (
        <Table<WorkRecord>
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={isLoading}
          size="small"
          pagination={false}
          scroll={{ x: 1100 }}
          locale={{
            emptyText: (
              <Empty
                description="尚無作業歷程紀錄"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      )}

      {/* 未指派公文列表（所有視圖通用） */}
      {viewMode !== 'correspondence' && hasUnassigned && (
        <UnassignedDocumentsList
          unassignedDocs={unassignedDocs}
          hasCorrespondence={hasCorrespondence}
          canEdit={canEdit}
          unlinkPending={unlinkDocMutation.isPending}
          onDocClick={handleDocClick}
          onQuickCreateRecord={handleQuickCreateRecord}
          onUnlinkDocument={handleUnlinkDocument}
        />
      )}

      {/* 行內公文搜尋區（所有視圖通用） */}
      {canEdit && (
        <InlineDocumentSearch
          availableDocs={availableDocs}
          selectedDocId={selectedDocId}
          selectedLinkType={selectedLinkType}
          docSearchKeyword={docSearchKeyword}
          searchingDocs={searchingDocs}
          linkingDoc={linkDocMutation.isPending}
          onDocumentChange={handleDocumentChange}
          onSearchKeywordChange={setDocSearchKeyword}
          onLinkTypeChange={setSelectedLinkType}
          onLinkDocument={handleLinkDocument}
        />
      )}

      {/* 自動匹配公文按鈕 */}
      {canEdit && projectName && (
        <div style={{ marginTop: 12, textAlign: 'right' }}>
          <Button
            icon={<ThunderboltOutlined />}
            onClick={() => autoMatchMutation.mutate()}
            loading={autoMatchMutation.isPending}
          >
            自動匹配公文
          </Button>
        </div>
      )}

      {/* 自動匹配結果 Modal */}
      <AutoMatchModal
        open={autoMatchModalOpen}
        projectName={projectName || ''}
        agencyDocs={autoMatchResults.agency}
        companyDocs={autoMatchResults.company}
        selectedIds={selectedAutoMatchIds}
        onSelectedIdsChange={setSelectedAutoMatchIds}
        onConfirm={handleAutoMatchConfirm}
        onCancel={() => setAutoMatchModalOpen(false)}
        loading={batchLinkMutation.isPending}
      />
    </div>
  );
};

export default DispatchWorkflowTab;
