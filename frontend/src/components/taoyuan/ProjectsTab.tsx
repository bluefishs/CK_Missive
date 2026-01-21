/**
 * 桃園查估派工 - 工程資訊 Tab
 *
 * 導航模式設計：
 * - 點擊工程列表項目導航至工程詳情頁
 * - 新增工程導航到獨立的新增頁面
 * - 在詳情頁進行編輯操作，列表頁只負責瀏覽和搜尋
 *
 * @version 1.0.0
 * @date 2026-01-21
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
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  SearchOutlined,
  ProjectOutlined,
  SendOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import { taoyuanProjectsApi } from '../../api/taoyuanDispatchApi';
import type { TaoyuanProject } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import {
  DISTRICT_OPTIONS,
  CASE_TYPE_OPTIONS,
} from '../../constants/taoyuanOptions';

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
        limit: 1000,
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

  // 欄位設計依據 Excel「1.轄管工程清單」工作表（含篩選排序）
  const columns: ColumnsType<TaoyuanProject> = [
    {
      title: '項次',
      dataIndex: 'sequence_no',
      width: 60,
      fixed: 'left',
      render: (val: number | undefined, _record: TaoyuanProject, index: number) => val ?? index + 1,
    },
    {
      title: '審議年度',
      dataIndex: 'review_year',
      width: 90,
      sorter: (a, b) => (a.review_year ?? 0) - (b.review_year ?? 0),
      filters: reviewYearFilters,
      onFilter: (value, record) => record.review_year === value,
    },
    {
      title: '案件類型',
      dataIndex: 'case_type',
      width: 100,
      filters: CASE_TYPE_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.case_type === value,
    },
    {
      title: '行政區',
      dataIndex: 'district',
      width: 90,
      sorter: (a, b) => (a.district ?? '').localeCompare(b.district ?? ''),
      filters: DISTRICT_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.district === value,
      render: (val?: string) => val ? <Tag color="green">{val}</Tag> : '-',
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      width: 250,
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
      width: 120,
      ellipsis: true,
    },
    {
      title: '案件承辦',
      dataIndex: 'case_handler',
      width: 100,
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: caseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
    },
    {
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 100,
      filters: [...new Set(projects.map((p) => p.survey_unit).filter(Boolean))]
        .map((s) => ({ text: s as string, value: s as string })),
      onFilter: (value, record) => record.survey_unit === value,
    },
    {
      title: '審議結果',
      dataIndex: 'review_result',
      width: 100,
      ellipsis: true,
    },
    {
      title: '備註',
      dataIndex: 'remark',
      width: 120,
      ellipsis: true,
    },
  ];

  // 統計資料 (基於進度狀態判斷)
  const dispatchedCount = projects.filter((p) => p.land_agreement_status || p.building_survey_status).length;
  const completedCount = projects.filter((p) => p.acceptance_status === '已驗收').length;

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="總工程數" value={projects.length} prefix={<ProjectOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已派工"
              value={dispatchedCount}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SendOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="已完成"
              value={completedCount}
              valueStyle={{ color: '#52c41a' }}
              prefix={<Badge status="success" />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="完成率"
              value={projects.length ? Math.round((completedCount / projects.length) * 100) : 0}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜尋工程名稱、承辦人"
          allowClear
          onSearch={setSearchText}
          style={{ width: 280 }}
        />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          重新整理
        </Button>
        <Button icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>
          Excel 匯入
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增工程
        </Button>
      </Space>

      {/* 提示文字 */}
      <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
        <Text type="secondary">點擊列表項目可進入詳情頁進行編輯</Text>
      </div>

      {/* 工程列表表格 */}
      <Table
        columns={columns}
        dataSource={projects}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1100 }}
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

      {/* Excel 匯入 Modal */}
      <Modal
        title="Excel 匯入工程資料"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
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
