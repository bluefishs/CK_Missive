/**
 * 桃園查估派工 - 派工紀錄 Tab
 *
 * 導航模式設計：
 * - 新增派工單導航到獨立的新增頁面
 * - 點擊列表項目導航至派工單詳情頁進行編輯
 *
 * @version 1.1.0
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
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  FileExcelOutlined,
  SendOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import type { DispatchOrder } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import { WORK_TYPE_OPTIONS } from '../../constants/taoyuanOptions';

const { Text } = Typography;
const { Search } = Input;

export interface DispatchOrdersTabProps {
  contractProjectId: number;
  contractCode: string;
}

export const DispatchOrdersTab: React.FC<DispatchOrdersTabProps> = ({
  contractProjectId,
  contractCode,
}) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [searchText, setSearchText] = useState('');
  const [importModalVisible, setImportModalVisible] = useState(false);

  // 使用共用的表格搜尋 Hook
  const {
    searchText: columnSearchText,
    searchedColumn,
    getColumnSearchProps,
  } = useTableColumnSearch<DispatchOrder>();

  const {
    data: ordersData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['dispatch-orders', contractProjectId, searchText],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        search: searchText || undefined,
        limit: 1000,
      }),
  });

  const orders = ordersData?.items ?? [];

  // 導航到新增派工單頁面
  const handleCreate = () => {
    navigate('/taoyuan/dispatch/create');
  };

  // 匯入派工紀錄 - 使用統一的 API 方法
  const handleImport = async (file: File) => {
    try {
      const result = await dispatchOrdersApi.importExcel(file, contractProjectId);
      if (result.success) {
        message.success(`匯入成功: ${result.imported_count} 筆`);
        refetch();
      } else {
        const errorMsg = result.errors.length > 0
          ? result.errors.map(e => e.message).join(', ')
          : '未知錯誤';
        message.error(`匯入失敗: ${errorMsg}`);
      }
    } catch (error) {
      message.error('匯入失敗');
    }
    setImportModalVisible(false);
  };

  // 下載匯入範本 (POST + blob 下載，符合資安規範)
  const handleDownloadTemplate = async () => {
    try {
      await dispatchOrdersApi.downloadImportTemplate();
    } catch (error) {
      message.error('下載範本失敗');
    }
  };

  // 從資料中取得不重複的承辦人清單（用於篩選）
  const dispatchCaseHandlerFilters = [...new Set(orders.map((o) => o.case_handler).filter(Boolean))]
    .map((h) => ({ text: h as string, value: h as string }));

  // 從資料中取得不重複的查估單位（用於篩選）
  const dispatchSurveyUnitFilters = [...new Set(orders.map((o) => o.survey_unit).filter(Boolean))]
    .map((s) => ({ text: s as string, value: s as string }));

  // 對應原始需求的 17 欄位表格（含篩選排序）
  const columns: ColumnsType<DispatchOrder> = [
    {
      title: '序',
      dataIndex: 'id',
      width: 60,
      fixed: 'left',
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 130,
      fixed: 'left',
      sorter: (a, b) => (a.dispatch_no ?? '').localeCompare(b.dispatch_no ?? ''),
      ...getColumnSearchProps('dispatch_no'),
      render: (val: string) =>
        searchedColumn === 'dispatch_no' ? (
          <Highlighter
            highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
            searchWords={[columnSearchText]}
            autoEscape
            textToHighlight={val ? val.toString() : ''}
          />
        ) : (
          val
        ),
    },
    {
      title: '機關函文號',
      dataIndex: 'agency_doc_number',
      width: 140,
      render: (val?: string) => val || '-',
    },
    {
      title: '工程名稱/派工事項',
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
          val
        ),
    },
    {
      title: '作業類別',
      dataIndex: 'work_type',
      width: 150,
      filters: WORK_TYPE_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.work_type === value,
      render: (val?: string) => val ? <Tag color="blue">{val}</Tag> : '-',
    },
    {
      title: '分案名稱/派工備註',
      dataIndex: 'sub_case_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '履約期限',
      dataIndex: 'deadline',
      width: 120,
      sorter: (a, b) => (a.deadline ?? '').localeCompare(b.deadline ?? ''),
    },
    {
      title: '案件承辦',
      dataIndex: 'case_handler',
      width: 100,
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: dispatchCaseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
    },
    {
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 100,
      filters: dispatchSurveyUnitFilters,
      onFilter: (value, record) => record.survey_unit === value,
    },
    {
      title: '乾坤函文號',
      dataIndex: 'company_doc_number',
      width: 140,
      render: (val?: string) => val || '-',
    },
    {
      title: '雲端資料夾',
      dataIndex: 'cloud_folder',
      width: 150,
      ellipsis: true,
      render: (val?: string) => val ? (
        <Tooltip title={val}>
          <a href={val} target="_blank" rel="noopener noreferrer">
            <LinkOutlined /> 連結
          </a>
        </Tooltip>
      ) : '-',
    },
    {
      title: '專案資料夾',
      dataIndex: 'project_folder',
      width: 150,
      ellipsis: true,
    },
    {
      title: '聯絡備註',
      dataIndex: 'contact_note',
      width: 150,
      ellipsis: true,
    },
    {
      title: '關聯公文',
      key: 'linked_documents',
      width: 180,
      render: (_, record) => {
        const docs = record.linked_documents || [];
        if (docs.length === 0) return <Text type="secondary">-</Text>;
        return (
          <Space size={[0, 4]} wrap>
            {docs.map((doc) => (
              <Tooltip key={doc.link_id} title={doc.subject || ''}>
                <Tag color={doc.link_type === 'agency_incoming' ? 'blue' : 'green'}>
                  {doc.doc_number || `#${doc.document_id}`}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        );
      },
    },
    {
      title: '關聯工程',
      key: 'linked_projects',
      width: 200,
      render: (_, record) => {
        const projects = record.linked_projects || [];
        if (projects.length === 0) return <Text type="secondary">-</Text>;
        return (
          <Space size={[0, 4]} wrap>
            {projects.map((proj) => (
              <Tooltip key={proj.id} title={proj.project_name}>
                <Tag color="purple">{proj.project_name?.slice(0, 15) || `工程#${proj.id}`}</Tag>
              </Tooltip>
            ))}
          </Space>
        );
      },
    },
  ];

  // 點擊行導航到詳情頁
  const handleRowClick = (record: DispatchOrder) => {
    navigate(`/taoyuan/dispatch/${record.id}`);
  };

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="總派工單數" value={orders.length} prefix={<SendOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="有機關函文"
              value={orders.filter((o) => o.agency_doc_number).length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="有乾坤函文"
              value={orders.filter((o) => o.company_doc_number).length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="作業類別數"
              value={new Set(orders.map((o) => o.work_type).filter(Boolean)).size}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜尋派工單號、工程名稱"
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
          新增派工單
        </Button>
      </Space>

      {/* 派工紀錄表格 - 點擊行導航到詳情頁 */}
      <Table
        columns={columns}
        dataSource={orders}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 2100 }}
        size="small"
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 筆`,
        }}
        onRow={(record) => ({
          onClick: () => handleRowClick(record),
          style: { cursor: 'pointer' },
        })}
      />

      {/* Excel 匯入 Modal */}
      <Modal
        title="Excel 匯入派工紀錄"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
            下載匯入範本
          </Button>
          <span style={{ marginLeft: 8, color: '#666', fontSize: 12 }}>
            範本包含 13 個欄位：派工單號、機關函文號、工程名稱...等
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
            <FileExcelOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          </p>
          <p className="ant-upload-text">點擊或拖曳 Excel 檔案至此區域</p>
          <p className="ant-upload-hint">
            支援 .xlsx, .xls 格式，對應原始需求 17 欄位設計
          </p>
        </Upload.Dragger>
        <div style={{ marginTop: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
          <Text strong>匯入欄位說明：</Text>
          <div style={{ marginTop: 8, fontSize: 12 }}>
            <Row gutter={[8, 4]}>
              <Col span={8}>1. 派工單號 *</Col>
              <Col span={8}>2. 機關函文號</Col>
              <Col span={8}>3. 工程名稱/派工事項</Col>
              <Col span={8}>4. 作業類別</Col>
              <Col span={8}>5. 分案名稱/派工備註</Col>
              <Col span={8}>6. 履約期限</Col>
              <Col span={8}>7. 案件承辦</Col>
              <Col span={8}>8. 查估單位</Col>
              <Col span={8}>9. 乾坤函文號</Col>
              <Col span={8}>10. 雲端資料夾</Col>
              <Col span={8}>11. 專案資料夾</Col>
              <Col span={8}>12. 聯絡備註</Col>
            </Row>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DispatchOrdersTab;
