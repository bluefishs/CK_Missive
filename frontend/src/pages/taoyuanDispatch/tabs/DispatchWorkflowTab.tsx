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
 * @version 4.0.0 - 整合公文關聯與作業歷程
 * @date 2026-02-13
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
  Segmented,
  Statistic,
  Row,
  Col,
  Card,
  App,
  Select,
  Radio,
  Badge,
  theme,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  SendOutlined,
  OrderedListOutlined,
  CheckCircleOutlined,
  ProjectOutlined,
  LinkOutlined,
  DisconnectOutlined,
  ExclamationCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { workflowApi } from '../../../api/taoyuan';
import { dispatchOrdersApi } from '../../../api/taoyuanDispatchApi';
import type {
  WorkRecord,
  WorkRecordStatus,
} from '../../../types/taoyuan';
import type { DispatchDocumentLink, LinkType } from '../../../types/api';
import { isReceiveDocument } from '../../../types/api';
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
  InlineRecordCreator,
} from '../../../components/taoyuan/workflow';
import {
  useDispatchWorkData,
  detectLinkType,
} from '../../../components/taoyuan/workflow/useDispatchWorkData';

const { Text } = Typography;
const { Option } = Select;

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
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();
  const { token } = theme.useToken();

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
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders'] });
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
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders'] });
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
    },
    onError: () => message.error('移除關聯失敗'),
  });

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

  // 從未指派公文快速建立作業紀錄（導航到新增頁面，帶入公文 ID — 統一用新格式）
  const handleQuickCreateRecord = useCallback(
    (doc: DispatchDocumentLink) => {
      navigate(
        `/taoyuan/dispatch/${dispatchOrderId}/workflow/create?document_id=${doc.document_id}`,
      );
    },
    [navigate, dispatchOrderId],
  );

  // ===========================================================================
  // Table Columns
  // ===========================================================================

  const columns: ColumnsType<WorkRecord> = useMemo(
    () => [
      {
        title: '序號',
        dataIndex: 'sort_order',
        key: 'sort_order',
        width: 60,
        align: 'center' as const,
      },
      {
        title: '類別',
        key: 'category',
        width: 110,
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
              <Text ellipsis style={{ maxWidth: 250 }}>{text}</Text>
            </Tooltip>
          );
        },
      },
      {
        title: '紀錄日期',
        dataIndex: 'record_date',
        key: 'record_date',
        width: 110,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '期限',
        dataIndex: 'deadline_date',
        key: 'deadline_date',
        width: 110,
        render: (val: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
      },
      {
        title: '狀態',
        dataIndex: 'status',
        key: 'status',
        width: 90,
        render: (status: WorkRecordStatus) => (
          <Tag color={statusColor(status)}>{statusLabel(status)}</Tag>
        ),
      },
      {
        title: '來文',
        key: 'incoming_doc',
        width: 120,
        render: (_: unknown, record: WorkRecord) => {
          // 舊格式
          if (record.incoming_doc?.doc_number) {
            return (
              <Tooltip title={record.incoming_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 100, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.incoming_doc?.id && handleDocClick(record.incoming_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.incoming_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          // 新格式：document_id + direction = incoming
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'incoming') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 100, cursor: 'pointer', color: '#1677ff' }}
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
        width: 120,
        render: (_: unknown, record: WorkRecord) => {
          // 舊格式
          if (record.outgoing_doc?.doc_number) {
            return (
              <Tooltip title={record.outgoing_doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 100, cursor: 'pointer', color: '#1677ff' }}
                  onClick={() => record.outgoing_doc?.id && handleDocClick(record.outgoing_doc.id)}
                >
                  <FileTextOutlined style={{ marginRight: 4 }} />
                  {record.outgoing_doc.doc_number}
                </Text>
              </Tooltip>
            );
          }
          // 新格式：document_id + direction = outgoing
          const doc = getEffectiveDoc(record);
          const dir = getDocDirection(record);
          if (doc?.doc_number && dir === 'outgoing') {
            return (
              <Tooltip title={doc.subject}>
                <Text
                  ellipsis
                  style={{ maxWidth: 100, cursor: 'pointer', color: '#1677ff' }}
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
              width: 100,
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
  // 未指派公文子元件
  // ===========================================================================

  const renderUnassignedDoc = useCallback(
    (doc: DispatchDocumentLink, direction: 'incoming' | 'outgoing') => {
      const isIncoming = direction === 'incoming';
      return (
        <div
          key={`unassigned-${doc.document_id}`}
          style={{
            padding: '6px 8px',
            borderBottom: `1px dashed ${token.colorBorderSecondary}`,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 4,
            background: token.colorBgTextHover,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {isIncoming ? (
                <FileTextOutlined style={{ color: token.colorPrimary, fontSize: 12 }} />
              ) : (
                <SendOutlined style={{ color: '#52c41a', fontSize: 12 }} />
              )}
              <Text
                style={{
                  fontSize: 12,
                  cursor: 'pointer',
                  color: token.colorPrimary,
                }}
                onClick={() => handleDocClick(doc.document_id)}
              >
                {doc.doc_number || `#${doc.document_id}`}
              </Text>
              {doc.doc_date && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {dayjs(doc.doc_date).format('YYYY.MM.DD')}
                </Text>
              )}
            </div>
            {doc.subject && (
              <Text
                type="secondary"
                ellipsis={{ tooltip: doc.subject }}
                style={{ display: 'block', fontSize: 12, marginTop: 1 }}
              >
                {doc.subject}
              </Text>
            )}
          </div>

          {canEdit && (
            <Space size={2}>
              <Tooltip title="新增作業紀錄">
                <Button
                  type="link"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => handleQuickCreateRecord(doc)}
                  style={{ fontSize: 12 }}
                />
              </Tooltip>
              {doc.link_id !== undefined && (
                <Popconfirm
                  title="確定移除此公文關聯？"
                  onConfirm={() => handleUnlinkDocument(doc.link_id)}
                  okText="確定"
                  cancelText="取消"
                >
                  <Tooltip title="移除關聯">
                    <Button
                      type="link"
                      size="small"
                      danger
                      icon={<DisconnectOutlined />}
                      loading={unlinkDocMutation.isPending}
                      style={{ fontSize: 12 }}
                    />
                  </Tooltip>
                </Popconfirm>
              )}
            </Space>
          )}
        </div>
      );
    },
    [token, canEdit, handleDocClick, handleQuickCreateRecord, handleUnlinkDocument, unlinkDocMutation.isPending],
  );

  // ===========================================================================
  // 公文對照視圖（含未指派區塊）
  // ===========================================================================

  const hasUnassigned = unassignedDocs.incoming.length > 0 || unassignedDocs.outgoing.length > 0;
  const hasCorrespondence =
    correspondenceData.incomingDocs.length > 0 ||
    correspondenceData.outgoingDocs.length > 0;

  const renderCorrespondenceView = () => {
    if (!hasCorrespondence && !hasUnassigned && linkedDocuments.length === 0) {
      return (
        <Empty
          description="尚無公文關聯與作業紀錄"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          style={{ padding: '40px 0' }}
        />
      );
    }

    return (
      <>
        {/* 已指派公文（對應作業紀錄的公文） */}
        {hasCorrespondence && (
          <CorrespondenceBody
            data={correspondenceData}
            onDocClick={handleDocClick}
            onEditRecord={canEdit ? handleEdit : undefined}
            canEdit={canEdit}
          />
        )}

        {/* 未指派公文區塊 */}
        {hasUnassigned && (
          <>
            {hasCorrespondence && (
              <Divider style={{ margin: '8px 0' }}>
                <Space size={4}>
                  <ExclamationCircleOutlined style={{ color: token.colorWarning }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    未指派公文 ({unassignedDocs.incoming.length + unassignedDocs.outgoing.length})
                  </Text>
                </Space>
              </Divider>
            )}
            <Row gutter={12}>
              {/* 未指派來文 */}
              <Col xs={24} md={12}>
                {unassignedDocs.incoming.length > 0 && (
                  <div
                    style={{
                      borderRadius: 6,
                      border: `1px dashed ${token.colorWarning}`,
                      overflow: 'hidden',
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        padding: '4px 10px',
                        background: '#fffbe6',
                        borderBottom: `1px dashed ${token.colorWarning}`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Text style={{ fontSize: 12, color: token.colorWarning }}>
                        <FileTextOutlined /> 待指派來文
                      </Text>
                      <Badge
                        count={unassignedDocs.incoming.length}
                        style={{ backgroundColor: token.colorWarning }}
                        size="small"
                      />
                    </div>
                    {unassignedDocs.incoming.map((doc) =>
                      renderUnassignedDoc(doc, 'incoming'),
                    )}
                  </div>
                )}
              </Col>

              {/* 未指派發文 */}
              <Col xs={24} md={12}>
                {unassignedDocs.outgoing.length > 0 && (
                  <div
                    style={{
                      borderRadius: 6,
                      border: `1px dashed ${token.colorWarning}`,
                      overflow: 'hidden',
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        padding: '4px 10px',
                        background: '#fffbe6',
                        borderBottom: `1px dashed ${token.colorWarning}`,
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                      }}
                    >
                      <Text style={{ fontSize: 12, color: token.colorWarning }}>
                        <SendOutlined /> 待指派發文
                      </Text>
                      <Badge
                        count={unassignedDocs.outgoing.length}
                        style={{ backgroundColor: token.colorWarning }}
                        size="small"
                      />
                    </div>
                    {unassignedDocs.outgoing.map((doc) =>
                      renderUnassignedDoc(doc, 'outgoing'),
                    )}
                  </div>
                )}
              </Col>
            </Row>
          </>
        )}
      </>
    );
  };

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <div>
      {/* 迷你統計 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={[16, 8]} align="middle">
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="紀錄數"
              value={stats.total}
              prefix={<OrderedListOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="已完成"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ fontSize: 18, color: '#52c41a' }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="已暫緩"
              value={stats.onHold}
              valueStyle={{ fontSize: 18, color: stats.onHold > 0 ? '#faad14' : undefined }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="關聯公文"
              value={stats.linkedDocCount}
              prefix={<LinkOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="未指派"
              value={stats.unassignedDocCount}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{
                fontSize: 18,
                color: stats.unassignedDocCount > 0 ? '#faad14' : undefined,
              }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="來文"
              value={stats.incomingDocs}
              prefix={<FileTextOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Statistic
              title="發文"
              value={stats.outgoingDocs}
              prefix={<SendOutlined />}
              valueStyle={{ fontSize: 18 }}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              當前階段
            </Text>
            <div>
              <Tag
                color={stats.currentStage === '全部完成' ? 'success' : 'processing'}
                style={{ marginTop: 2 }}
              >
                {stats.currentStage}
              </Tag>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 工具列 */}
      <div
        style={{
          marginBottom: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
        }}
      >
        <Space wrap>
          {canEdit && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
              新增紀錄
            </Button>
          )}
          {linkedProjects && linkedProjects.length > 0 && (
            <>
              {linkedProjects.map((proj) => (
                <Tooltip
                  key={proj.project_id}
                  title={`前往「${proj.project_name || '工程'}」總覽，查看本派工在整體工程中的進度`}
                >
                  <Button
                    icon={<ProjectOutlined />}
                    onClick={() => handleGoToProjectOverview(proj.project_id)}
                  >
                    查看工程總覽
                  </Button>
                </Tooltip>
              ))}
            </>
          )}
        </Space>

        <Segmented
          value={viewMode}
          onChange={(val) => setViewMode(val as ViewMode)}
          options={[
            {
              value: 'chain',
              label: '時間軸',
              icon: <LinkOutlined />,
            },
            {
              value: 'correspondence',
              label: '公文對照',
              icon: <FileTextOutlined />,
            },
            {
              value: 'table',
              label: '表格',
              icon: <OrderedListOutlined />,
            },
          ]}
        />
      </div>

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

      {/* 行內新增作業紀錄（時間軸模式） */}
      {canEdit && viewMode === 'chain' && (
        <InlineRecordCreator
          dispatchOrderId={dispatchOrderId}
          existingRecords={records}
          linkedDocuments={linkedDocuments}
          onCreated={onRefetchDispatch}
        />
      )}

      {/* 行內公文搜尋區（非時間軸模式才顯示） */}
      {canEdit && viewMode !== 'chain' && (
        <Card
          size="small"
          style={{ marginTop: 12 }}
          styles={{
            header: { minHeight: 36, padding: '0 12px' },
            body: { padding: '8px 12px' },
          }}
          title={
            <Space size={4}>
              <SearchOutlined />
              <Text style={{ fontSize: 13 }}>新增公文關聯</Text>
            </Space>
          }
        >
          <Row gutter={[8, 8]} align="middle">
            <Col xs={24} sm={24} md={12} lg={12}>
              <Select
                showSearch
                allowClear
                placeholder="搜尋公文字號或主旨..."
                style={{ width: '100%' }}
                value={selectedDocId}
                onChange={handleDocumentChange}
                onSearch={setDocSearchKeyword}
                filterOption={false}
                popupMatchSelectWidth={false}
                styles={{ popup: { root: { minWidth: 500, maxWidth: 700 } } }}
                notFoundContent={
                  docSearchKeyword ? (
                    <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Text type="secondary">請輸入關鍵字搜尋</Text>
                  )
                }
                loading={searchingDocs}
                optionLabelProp="label"
                size="small"
              >
                {availableDocs.map((doc) => {
                  const docNumber = doc.doc_number || `#${doc.id}`;
                  const subject = doc.subject || '(無主旨)';
                  const docIsReceive = isReceiveDocument(doc.category);
                  const dateStr = doc.doc_date ? doc.doc_date.substring(0, 10) : '';
                  const tooltipContent = (
                    <div style={{ maxWidth: 400 }}>
                      <div><strong>字號：</strong>{docNumber}</div>
                      <div><strong>主旨：</strong>{subject}</div>
                      {dateStr && <div><strong>日期：</strong>{dateStr}</div>}
                      {doc.sender && <div><strong>發文：</strong>{doc.sender}</div>}
                      {doc.receiver && <div><strong>受文：</strong>{doc.receiver}</div>}
                    </div>
                  );

                  return (
                    <Option key={doc.id} value={doc.id} label={docNumber}>
                      <Tooltip title={tooltipContent} placement="right" mouseEnterDelay={0.5}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Tag
                            color={docIsReceive ? 'blue' : 'green'}
                            style={{ flexShrink: 0, margin: 0 }}
                          >
                            {docIsReceive ? '收' : '發'}
                          </Tag>
                          <Text strong style={{ flexShrink: 0, minWidth: 140 }}>
                            {docNumber}
                          </Text>
                          <Text
                            type="secondary"
                            ellipsis
                            style={{ flex: 1, maxWidth: 250 }}
                          >
                            {subject}
                          </Text>
                        </div>
                      </Tooltip>
                    </Option>
                  );
                })}
              </Select>
            </Col>
            <Col xs={16} sm={14} md={7} lg={7}>
              <Radio.Group
                value={selectedLinkType}
                onChange={(e) => setSelectedLinkType(e.target.value)}
                size="small"
              >
                <Radio.Button value="agency_incoming">機關來函</Radio.Button>
                <Radio.Button value="company_outgoing">乾坤發文</Radio.Button>
              </Radio.Group>
            </Col>
            <Col xs={8} sm={10} md={5} lg={5}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleLinkDocument}
                loading={linkDocMutation.isPending}
                disabled={!selectedDocId}
                size="small"
              >
                建立關聯
              </Button>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
};

export default DispatchWorkflowTab;
