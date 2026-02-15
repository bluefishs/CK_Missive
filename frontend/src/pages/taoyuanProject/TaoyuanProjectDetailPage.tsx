/**
 * 桃園轄管工程詳情頁面
 *
 * 使用通用 DetailPageLayout 元件，採用 Tab 架構對應 Excel「1.轄管工程清單」。
 *
 * @version 4.0.0 - 作業歷程 + 看板整合為「作業總覽」Tab
 * @date 2026-02-13
 */

import React from 'react';
import { Button, Space, Popconfirm } from 'antd';
import {
  ProjectOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
  SendOutlined,
  EnvironmentOutlined,
  HomeOutlined,
  DollarOutlined,
  FileTextOutlined,
  AppstoreOutlined,
} from '@ant-design/icons';

import {
  DetailPageLayout,
  createTabItem,
} from '../../components/common/DetailPage';
import { useTaoyuanProjectDetail } from './hooks/useTaoyuanProjectDetail';
import {
  BasicInfoTab,
  EngineeringScopeTab,
  LandBuildingTab,
  BudgetEstimateTab,
  ReviewStatusTab,
  ProjectWorkOverviewTab,
  DispatchLinksTab,
} from './tabs';

export const TaoyuanProjectDetailPage: React.FC = () => {
  const ctx = useTaoyuanProjectDetail();

  const {
    project,
    isLoading,
    isEditing,
    setIsEditing,
    activeTab,
    setActiveTab,
    highlightDispatchId,
    canEdit,
    canDelete,
    form,
    agencyContacts,
    projectVendors,
    linkedDispatches,
    filteredDispatches,
    selectedDispatchId,
    setSelectedDispatchId,
    updateMutation,
    deleteMutation,
    linkDispatchMutation,
    unlinkDispatchMutation,
    handleSave,
    handleCancelEdit,
    handleLinkDispatch,
    refetch,
    message,
  } = ctx;

  const tabs = [
    createTabItem(
      'basic',
      { icon: <ProjectOutlined />, text: '基本資訊' },
      <BasicInfoTab
        form={form}
        isEditing={isEditing}
        project={project}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
      />
    ),
    createTabItem(
      'scope',
      { icon: <EnvironmentOutlined />, text: '工程範圍' },
      <EngineeringScopeTab form={form} isEditing={isEditing} project={project} />
    ),
    createTabItem(
      'land',
      { icon: <HomeOutlined />, text: '土地建物' },
      <LandBuildingTab form={form} isEditing={isEditing} project={project} />
    ),
    createTabItem(
      'cost',
      { icon: <DollarOutlined />, text: '經費估算' },
      <BudgetEstimateTab form={form} isEditing={isEditing} project={project} />
    ),
    createTabItem(
      'status',
      { icon: <FileTextOutlined />, text: '審議狀態' },
      <ReviewStatusTab form={form} isEditing={isEditing} project={project} />
    ),
    createTabItem(
      'overview',
      { icon: <AppstoreOutlined />, text: '作業總覽' },
      <ProjectWorkOverviewTab
        projectId={project?.id || 0}
        contractProjectId={project?.contract_project_id}
        linkedDispatches={linkedDispatches}
        canEdit={canEdit}
        initialHighlightDispatchId={highlightDispatchId}
      />
    ),
    createTabItem(
      'dispatch-links',
      { icon: <SendOutlined />, text: '派工關聯', count: linkedDispatches.length },
      <DispatchLinksTab
        isLoading={isLoading}
        isEditing={isEditing}
        canEdit={canEdit}
        linkedDispatches={linkedDispatches}
        filteredDispatches={filteredDispatches}
        selectedDispatchId={selectedDispatchId}
        setSelectedDispatchId={setSelectedDispatchId}
        handleLinkDispatch={handleLinkDispatch}
        linkDispatchMutation={linkDispatchMutation}
        unlinkDispatchMutation={unlinkDispatchMutation}
        refetch={refetch}
        message={message}
      />
    ),
  ];

  const headerConfig = {
    title: project?.project_name || '工程詳情',
    icon: <ProjectOutlined />,
    backText: '返回派工管理',
    backPath: '/taoyuan/dispatch',
    tags: project
      ? [
          ...(project.district
            ? [{ text: project.district, color: 'green' as const }]
            : []),
          ...(project.case_type
            ? [{ text: project.case_type, color: 'blue' as const }]
            : []),
          ...(project.acceptance_status === '已驗收'
            ? [{ text: '已驗收', color: 'success' as const }]
            : []),
        ]
      : [],
    extra: (
      <Space>
        {isEditing ? (
          <>
            <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={updateMutation.isPending}
              disabled={updateMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </>
        ) : (
          <>
            {canEdit && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={() => setIsEditing(true)}
              >
                編輯
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="確定要刪除此工程嗎？"
                description="刪除後將無法復原，請確認是否繼續。"
                onConfirm={() => deleteMutation.mutate()}
                okText="確定刪除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  刪除
                </Button>
              </Popconfirm>
            )}
          </>
        )}
      </Space>
    ),
  };

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={isLoading}
      hasData={!!project}
    />
  );
};

export default TaoyuanProjectDetailPage;
