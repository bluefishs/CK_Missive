/**
 * PM 案件里程碑管理頁籤
 *
 * 提供里程碑的 CRUD 功能（子表格模式）
 *
 * 2026-08-02：新增／編輯改為獨立路由頁 `PMMilestoneFormPage`（去彈跳視窗）。
 * 原豁免理由「導頁會失去詳情頁捲動位置與 tab 狀態」在桌面成立，但未考慮行動情境；
 * 返回時已帶 ?tab=milestones 保留分頁。刪除仍就地用 Popconfirm。
 */
import { useCallback } from 'react';
import { Button, Tag, Space, message } from 'antd';
import { PlusOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { Upload } from 'antd';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import type { ResponsiveColumn } from '../../components/common/EnhancedTable';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/types';
import { useResponsive } from '../../hooks';
import type { PMMilestone, PMMilestoneType, PMMilestoneStatus } from '../../types/pm';
import { PM_MILESTONE_TYPE_LABELS, PM_MILESTONE_STATUS_LABELS } from '../../types/pm';
import { usePMMilestones } from '../../hooks/business/usePMCases';
import { apiClient } from '../../api/client';
import { PM_ENDPOINTS } from '../../api/endpoints';
import { getErrorMessage } from '../../utils/apiErrorParser';

interface MilestonesTabProps {
  pmCaseId: number;
}

const MILESTONE_STATUS_COLOR: Record<PMMilestoneStatus, string> = {
  pending: 'default',
  in_progress: 'processing',
  completed: 'success',
  overdue: 'error',
  skipped: 'warning',
};



export default function MilestonesTab({ pmCaseId }: MilestonesTabProps) {
  const navigate = useNavigate();
  const { isMobile } = useResponsive();

  const { data: milestones, isLoading } = usePMMilestones(pmCaseId);

  // 新增／編輯改為獨立頁 PMMilestoneFormPage（2026-08-02，去彈跳視窗）；
  const goCreate = useCallback(
    () => navigate(ROUTES.PM_MILESTONE_CREATE.replace(':caseId', String(pmCaseId))),
    [navigate, pmCaseId],
  );

  const goEdit = useCallback(
    (milestoneId: number) =>
      navigate(
        ROUTES.PM_MILESTONE_EDIT
          .replace(':caseId', String(pmCaseId))
          .replace(':milestoneId', String(milestoneId)),
      ),
    [navigate, pmCaseId],
  );


  const columns: ResponsiveColumn<PMMilestone>[] = [
    {
      title: '里程碑名稱',
      dataIndex: 'milestone_name',
      key: 'milestone_name',
      ellipsis: true,
    },
    {
      title: '類型',
      dataIndex: 'milestone_type',
      key: 'milestone_type',
      width: 100,
      render: (val: PMMilestoneType | null) => (val ? <Tag>{PM_MILESTONE_TYPE_LABELS[val]}</Tag> : '-'),
    },
    {
      title: '預計日期',
      dataIndex: 'planned_date',
      hideOnMobile: true,
      key: 'planned_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '實際日期',
      dataIndex: 'actual_date',
      hideOnMobile: true,
      key: 'actual_date',
      width: 120,
      render: (val: string | null) => val ?? '-',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val: PMMilestoneStatus) => (
        <Tag color={MILESTONE_STATUS_COLOR[val]}>{PM_MILESTONE_STATUS_LABELS[val]}</Tag>
      ),
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      hideOnMobile: true,
      key: 'sort_order',
      width: 70,
      align: 'center',
    },
  ];



  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={goCreate} block={isMobile}>
            新增里程碑
          </Button>
          <Button icon={<DownloadOutlined />} onClick={async () => {
            try {
              // ⚠️ 原本用裸 fetch：不經 apiClient 就不帶認證 cookie 與 X-CSRF-Token，
              // 這個功能一直是壞的（同型掃全 4 處，2026-08-19 一併改）。
              const res = await apiClient.post(
                PM_ENDPOINTS.MILESTONES_EXPORT, { pm_case_id: pmCaseId }, { responseType: 'blob' },
              );
              const raw = res as unknown as { data?: Blob } | Blob;
              const blob = raw instanceof Blob ? raw : (raw.data as Blob);
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a'); a.href = url;
              a.download = `milestones_${pmCaseId}.xlsx`; a.click();
              URL.revokeObjectURL(url);
              message.success('匯出成功');
            } catch (e) { message.error(getErrorMessage(e, '匯出失敗'), 8); }
          }}>
            匯出 XLSX
          </Button>
          <Upload accept=".xlsx,.xls" showUploadList={false} beforeUpload={async (file) => {
            try {
              message.loading({ content: '匯入中...', key: 'ms-import' });
              const formData = new FormData(); formData.append('file', file);
              type MsImportResult = {
                success?: boolean; created?: number; updated?: number; error?: string;
              };
              const res = await apiClient.post(PM_ENDPOINTS.MILESTONES_IMPORT, formData);
              const result = ((res as unknown as { data?: MsImportResult })?.data
                ?? (res as unknown as MsImportResult));
              if (result.success) {
                message.success({ content: `匯入完成: 新增 ${result.created} 筆, 更新 ${result.updated} 筆`, key: 'ms-import', duration: 5 });
                window.location.reload();
              } else {
                message.error({ content: result.error || '匯入失敗', key: 'ms-import' });
              }
            } catch (e) { message.error({ content: getErrorMessage(e, '匯入失敗'), key: 'ms-import', duration: 8 }); }
            return false;
          }}>
            <Button icon={<UploadOutlined />}>匯入 XLSX</Button>
          </Upload>
        </Space>
      </div>

      <EnhancedTable<PMMilestone>
        rowKey="id"
        columns={columns}
        dataSource={milestones ?? []}
        loading={isLoading}
        pagination={false}
        size="small"
        onRow={(row: PMMilestone) => ({
          // 2026-08-04：操作欄移除（詳情頁 tab 只呈現，比照 /documents/:id）——
          // 點列進填報頁，編輯與刪除都在那一頁的標題列。
          onClick: () => goEdit(row.id),
          style: { cursor: 'pointer' },
        })}
      />

      {/* 新增／編輯已改為獨立頁 PMMilestoneFormPage */}
    </>
  );
}
