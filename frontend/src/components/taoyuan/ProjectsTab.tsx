/**
 * 桃園查估派工 - 工程資訊 Tab
 *
 * 導航模式設計：
 * - 點擊工程列表項目導航至工程詳情頁
 * - 新增工程導航到獨立的新增頁面
 * - 在詳情頁進行編輯操作，列表頁只負責瀏覽和搜尋
 *
 * @version 1.1.0 - RWD 響應式改造
 * @date 2026-01-23
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Card,
  Tag,
  Table,
  Input,
  Statistic,
  Row,
  Col,
  Upload,
  Badge,
  List,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  ProjectOutlined,
  SendOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import { taoyuanProjectsApi } from '../../api/taoyuanDispatchApi';
import type { TaoyuanProject, ProjectDispatchLinkItem, ProjectDocumentLinkItem } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import { useResponsive } from '../../hooks';
import {
  DISTRICT_OPTIONS,
  CASE_TYPE_OPTIONS,
} from '../../constants/taoyuanOptions';

/**
 * 根據公文字號自動判斷關聯類型
 * - 以「乾坤」開頭的公文 → 乾坤發文 (company_outgoing)
 * - 其他 → 機關來函 (agency_incoming)
 */
const detectLinkType = (docNumber?: string): 'agency_incoming' | 'company_outgoing' => {
  if (!docNumber) return 'agency_incoming';
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  return 'agency_incoming';
};

const { Text } = Typography;
const { Search } = Input;

export interface ProjectsTabProps {
  contractProjectId: number;
}

export const ProjectsTab: React.FC<ProjectsTabProps> = ({ contractProjectId }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [importModalVisible, setImportModalVisible] = useState(false);

  // RWD 響應式
  const { isMobile } = useResponsive();

  // 使用共用的表格搜尋 Hook
  const {
    searchText: columnSearchText,
    searchedColumn,
    getColumnSearchProps,
  } = useTableColumnSearch<TaoyuanProject>();

  // 查詢工程列表
  const {
    data: projectsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['taoyuan-projects', contractProjectId, searchText],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id: contractProjectId,
        search: searchText || undefined,
        limit: 100,
      }),
  });

  const projects = projectsData?.items ?? [];

  // 導航到新增工程頁面
  const handleCreate = () => {
    navigate('/taoyuan/project/create');
  };

  // Excel 匯入處理
  const handleImport = async (file: File) => {
    try {
      const result = await taoyuanProjectsApi.importExcel(file, contractProjectId);
      if (result.success) {
        message.success(`匯入成功: ${result.imported_count} 筆`);
        refetch();
      } else {
        message.error(`匯入失敗: ${result.errors.map((e) => e.message).join(', ')}`);
      }
    } catch {
      message.error('匯入失敗');
    }
    setImportModalVisible(false);
  };

  // 點擊列表項目導航至詳情頁
  const handleRowClick = (project: TaoyuanProject) => {
    navigate(`/taoyuan/project/${project.id}`);
  };

  // 從資料中取得不重複的承辦人清單（用於篩選）
  const caseHandlerFilters = [...new Set(projects.map((p) => p.case_handler).filter(Boolean))]
    .map((h) => ({ text: h as string, value: h as string }));

  // 從資料中取得不重複的審議年度（用於篩選）
  const reviewYearFilters = [...new Set(projects.map((p) => p.review_year).filter(Boolean))]
    .sort((a, b) => (b ?? 0) - (a ?? 0))
    .map((y) => ({ text: String(y), value: y as number }));

  // 欄位設計依據用戶需求：項次、審議年度、案件類型、行政區、工程名稱、分案名稱、案件承辦、查估單位、派工關聯、公文關聯
  const columns: ColumnsType<TaoyuanProject> = [
    {
      title: '項次',
      dataIndex: 'sequence_no',
      width: 50,
      fixed: 'left',
      align: 'center',
      render: (val: number | undefined, _record: TaoyuanProject, index: number) => val ?? index + 1,
    },
    {
      title: '審議年度',
      dataIndex: 'review_year',
      width: 80,
      align: 'center',
      sorter: (a, b) => (a.review_year ?? 0) - (b.review_year ?? 0),
      filters: reviewYearFilters,
      onFilter: (value, record) => record.review_year === value,
    },
    {
      title: '案件類型',
      dataIndex: 'case_type',
      width: 85,
      filters: CASE_TYPE_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.case_type === value,
    },
    {
      title: '行政區',
      dataIndex: 'district',
      width: 75,
      align: 'center',
      sorter: (a, b) => (a.district ?? '').localeCompare(b.district ?? ''),
      filters: DISTRICT_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.district === value,
      render: (val?: string) => val ? <Tag color="green">{val}</Tag> : '-',
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      width: 220,
      ellipsis: true,
      sorter: (a, b) => (a.project_name ?? '').localeCompare(b.project_name ?? ''),
      ...getColumnSearchProps('project_name'),
      render: (val: string) =>
        searchedColumn === 'project_name' ? (
          <Highlighter
            highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
            searchWords={[columnSearchText]}
            autoEscape
            textToHighlight={val ? val.toString() : ''}
          />
        ) : (
          <Text strong style={{ color: '#1890ff', cursor: 'pointer' }}>
            {val}
          </Text>
        ),
    },
    {
      title: '分案名稱',
      dataIndex: 'sub_case_name',
      width: 100,
      ellipsis: true,
    },
    {
      title: '承辦',
      dataIndex: 'case_handler',
      width: 60,
      align: 'center',
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: caseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
    },
    {
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 120,
      ellipsis: true,
      filters: [...new Set(projects.map((p) => p.survey_unit).filter(Boolean))]
        .map((s) => ({ text: s as string, value: s as string })),
      onFilter: (value, record) => record.survey_unit === value,
    },
    {
      title: '派工關聯',
      dataIndex: 'linked_dispatches',
      width: 145,
      render: (dispatches?: ProjectDispatchLinkItem[]) => {
        if (!dispatches || dispatches.length === 0) {
          return <Text type="secondary">-</Text>;
        }
        return (
          <Space direction="vertical" size={0}>
            {dispatches.slice(0, 2).map((d, idx) => (
              <Tag key={idx} color="blue" style={{ marginBottom: 2, fontSize: 11 }}>
                {d.dispatch_no || `派工#${d.dispatch_order_id}`}
              </Tag>
            ))}
            {dispatches.length > 2 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                +{dispatches.length - 2} 筆
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '公文關聯',
      dataIndex: 'linked_documents',
      width: 180,
      render: (docs?: ProjectDocumentLinkItem[]) => {
        if (!docs || docs.length === 0) {
          return <Text type="secondary">-</Text>;
        }
        return (
          <Space direction="vertical" size={0}>
            {docs.slice(0, 2).map((d, idx) => {
              const correctedType = detectLinkType(d.doc_number);
              const isAgency = correctedType === 'agency_incoming';
              return (
                <Tag key={idx} color={isAgency ? 'cyan' : 'orange'} style={{ marginBottom: 2, fontSize: 11 }}>
                  {d.doc_number || `公文#${d.document_id}`}
                </Tag>
              );
            })}
            {docs.length > 2 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                +{docs.length - 2} 筆
              </Text>
            )}
          </Space>
        );
      },
    },
  ];

  // 統計資料 (基於關聯資料判斷)
  // 已派工：有關聯派工單的工程
  const dispatchedCount = projects.filter((p) => (p.linked_dispatches?.length ?? 0) > 0).length;
  // 已完成：驗收狀態為「已驗收」的工程
  const completedCount = projects.filter((p) => p.acceptance_status === '已驗收').length;

  // 手機版卡片清單
  const MobileProjectList = () => (
    <List
      dataSource={projects}
      loading={isLoading}
      pagination={{
        size: 'small',
        pageSize: 10,
        showTotal: (total) => `共 ${total} 筆`,
      }}
      renderItem={(project) => (
        <Card
          size="small"
          style={{ marginBottom: 8, cursor: 'pointer' }}
          onClick={() => handleRowClick(project)}
          hoverable
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#1890ff', fontSize: 14 }}>
                {project.project_name}
              </Text>
              {project.sub_case_name && (
                <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                  {project.sub_case_name}
                </div>
              )}
              <Space wrap size={4} style={{ marginTop: 6 }}>
                {project.district && <Tag color="green" style={{ fontSize: 11 }}>{project.district}</Tag>}
                {project.case_type && <Tag style={{ fontSize: 11 }}>{project.case_type}</Tag>}
                {project.case_handler && <Tag color="blue" style={{ fontSize: 11 }}>{project.case_handler}</Tag>}
              </Space>
              <div style={{ marginTop: 6, fontSize: 11, color: '#999' }}>
                派工: {project.linked_dispatches?.length || 0} 筆 |
                公文: {project.linked_documents?.length || 0} 筆
              </div>
            </div>
            <RightOutlined style={{ color: '#ccc', marginTop: 4 }} />
          </div>
        </Card>
      )}
    />
  );

  return (
    <div>
      {/* 統計卡片 - RWD 響應式 */}
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '總數' : '總工程數'}
              value={projects.length}
              prefix={<ProjectOutlined />}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已派工"
              value={dispatchedCount}
              valueStyle={{ color: '#1890ff', fontSize: isMobile ? 18 : 24 }}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={completedCount}
              valueStyle={{ color: '#52c41a', fontSize: isMobile ? 18 : 24 }}
              prefix={<Badge status="success" />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="完成率"
              value={projects.length ? Math.round((completedCount / projects.length) * 100) : 0}
              suffix="%"
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 - RWD 響應式 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Search
            placeholder={isMobile ? '搜尋工程...' : '搜尋工程名稱、承辦人'}
            allowClear
            onSearch={setSearchText}
            style={{ width: '100%' }}
            size={isMobile ? 'middle' : 'middle'}
          />
        </Col>
        <Col xs={24} sm={12} md={16} style={{ textAlign: isMobile ? 'left' : 'right' }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetch()}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '重新整理'}
            </Button>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : 'Excel 匯入'}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '新增工程'}
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 提示文字 - 手機版隱藏 */}
      {!isMobile && (
        <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
          <Text type="secondary">點擊列表項目可進入詳情頁進行編輯</Text>
        </div>
      )}

      {/* 工程列表 - RWD: 手機用卡片清單，桌面用表格 */}
      {isMobile ? (
        <MobileProjectList />
      ) : (
        <Table
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1100 }}
          size="middle"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 筆`,
          }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
          rowClassName={() => 'clickable-row'}
        />
      )}

      {/* Excel 匯入 Modal - RWD 響應式 */}
      <Modal
        title="Excel 匯入工程資料"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={isMobile ? '95%' : 520}
      >
        <div style={{ marginBottom: 16 }}>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => taoyuanProjectsApi.downloadImportTemplate()}
          >
            下載匯入範本
          </Button>
          <span style={{ marginLeft: 8, color: '#666', fontSize: 12 }}>
            請先下載範本，按照格式填寫後再上傳
          </span>
        </div>
        <Upload.Dragger
          accept=".xlsx,.xls"
          maxCount={1}
          beforeUpload={(file) => {
            handleImport(file);
            return false;
          }}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">點擊或拖曳 Excel 檔案至此</p>
          <p className="ant-upload-hint">支援 .xlsx, .xls 格式</p>
        </Upload.Dragger>
      </Modal>
    </div>
  );
};

export default ProjectsTab;
