/**
 * 桃園查估派工 - 工程資訊 Tab
 *
 * 導航模式設計：
 * - 點擊工程列表項目導航至工程詳情頁
 * - 新增工程導航到獨立的新增頁面
 * - 在詳情頁進行編輯操作，列表頁只負責瀏覽和搜尋
 *
 * @version 1.2.0 - 提取欄位定義至 ProjectsTabColumns
 * @date 2026-03-25
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Card,
  Tag,
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

import { ResponsiveTable } from '../common';
import { taoyuanProjectsApi } from '../../api/taoyuanDispatchApi';
import type { TaoyuanProject } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import { useResponsive, useTaoyuanProjects } from '../../hooks';
import { buildProjectsColumns } from './ProjectsTabColumns';

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

  // 查詢工程列表 - 使用集中的 Hook
  const {
    projects,
    isLoading,
    refetch,
  } = useTaoyuanProjects({
    contract_project_id: contractProjectId,
    search: searchText || undefined,
    limit: 100,
  });

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
  const caseHandlerFilters = useMemo(
    () => [...new Set(projects.map((p) => p.case_handler).filter(Boolean))]
      .map((h) => ({ text: h as string, value: h as string })),
    [projects]
  );

  // 從資料中取得不重複的審議年度（用於篩選）
  const reviewYearFilters = useMemo(
    () => [...new Set(projects.map((p) => p.review_year).filter(Boolean))]
      .sort((a, b) => (b ?? 0) - (a ?? 0))
      .map((y) => ({ text: String(y), value: y as number })),
    [projects]
  );

  // 欄位定義（提取至 ProjectsTabColumns）
  const columns = useMemo(() => buildProjectsColumns({
    reviewYearFilters,
    caseHandlerFilters,
    projects,
    getColumnSearchProps,
    searchedColumn,
    columnSearchText,
  }), [reviewYearFilters, caseHandlerFilters, projects, getColumnSearchProps, searchedColumn, columnSearchText]);

  // 統計資料 (基於關聯資料判斷)
  const dispatchedCount = useMemo(
    () => projects.filter((p) => (p.linked_dispatches?.length ?? 0) > 0).length,
    [projects]
  );
  const completedCount = useMemo(
    () => projects.filter((p) => p.acceptance_status === '已驗收').length,
    [projects]
  );

  // 手機版卡片清單（useMemo 避免每次渲染重建元件）
  const mobileProjectList = useMemo(() => (
    <List
      dataSource={projects}
      loading={isLoading}
      pagination={{
        size: 'small',
        pageSize: 10,
        showTotal: (total: number) => `共 ${total} 筆`,
      }}
      renderItem={(project: TaoyuanProject) => (
        <Card
          size="small"
          style={{ marginBottom: 8, cursor: 'pointer' }}
          onClick={() => navigate(`/taoyuan/project/${project.id}`)}
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
                派工: {project.linked_dispatches?.length ?? 0} 筆 |
                公文: {project.linked_documents?.length ?? 0} 筆
              </div>
            </div>
            <RightOutlined style={{ color: '#ccc', marginTop: 4 }} />
          </div>
        </Card>
      )}
    />
  ), [projects, isLoading, navigate]);

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
              styles={{ content: { fontSize: isMobile ? 18 : 24 } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已派工"
              value={dispatchedCount}
              styles={{ content: { color: '#1890ff', fontSize: isMobile ? 18 : 24 } }}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={completedCount}
              styles={{ content: { color: '#52c41a', fontSize: isMobile ? 18 : 24 } }}
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
              styles={{ content: { fontSize: isMobile ? 18 : 24 } }}
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
            value={searchText}
            onChange={(e) => {
              const val = e.target.value;
              setSearchText(val);
              // 清空時立即觸發（allowClear 點擊時 value 會變成空字串）
              if (!val) setSearchText('');
            }}
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
        mobileProjectList
      ) : (
        <ResponsiveTable
          columns={columns}
          dataSource={projects}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1100 }}
          size="middle"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 筆`,
          }}
          onRow={(record: TaoyuanProject) => ({
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
