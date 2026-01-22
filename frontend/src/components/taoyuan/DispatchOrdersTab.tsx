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
  PaperClipOutlined,
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

  // 欄位順序：序、派工單號、工程名稱/派工事項、作業類別、履約期限、承辦、查估單位、雲端、關聯公文、關聯工程
  const columns: ColumnsType<DispatchOrder> = [
    {
      title: '序',
      dataIndex: 'id',
      width: 45,
      fixed: 'left',
      align: 'center',
      sorter: (a, b) => a.id - b.id,
    },
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 135,
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
          <Text style={{ color: '#1890ff', cursor: 'pointer' }}>{val}</Text>
        ),
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
      width: 180,
      ellipsis: false,
      filters: WORK_TYPE_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.work_type === value,
      render: (val?: string) => {
        if (!val) return '-';
        // 支援逗號分隔的多個作業類別
        const types = val.split(',').map((t) => t.trim()).filter(Boolean);
        if (types.length === 1) {
          return <Tag color="blue">{types[0]}</Tag>;
        }
        // 多個作業類別顯示為多個 Tag
        return (
          <Space direction="vertical" size={2}>
            {types.slice(0, 2).map((t, idx) => (
              <Tag key={idx} color="blue" style={{ fontSize: 11 }}>{t}</Tag>
            ))}
            {types.length > 2 && (
              <Tooltip title={types.slice(2).join(', ')}>
                <Text type="secondary" style={{ fontSize: 11 }}>+{types.length - 2} 項</Text>
              </Tooltip>
            )}
          </Space>
        );
      },
    },
    {
      title: '履約期限',
      dataIndex: 'deadline',
      width: 140,
      ellipsis: true,
      sorter: (a, b) => (a.deadline ?? '').localeCompare(b.deadline ?? ''),
      render: (val?: string) => val ? (
        <Tooltip title={val}>
          <span>{val}</span>
        </Tooltip>
      ) : '-',
    },
    {
      title: '承辦',
      dataIndex: 'case_handler',
      width: 60,
      align: 'center',
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: dispatchCaseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
    },
    {
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 130,
      ellipsis: true,
      filters: dispatchSurveyUnitFilters,
      onFilter: (value, record) => record.survey_unit === value,
      render: (val?: string) => val ? (
        <Tooltip title={val}>
          <span>{val}</span>
        </Tooltip>
      ) : '-',
    },
    {
      title: '雲端',
      dataIndex: 'cloud_folder',
      width: 55,
      align: 'center',
      render: (val?: string) => val ? (
        <Tooltip title={val}>
          <a href={val} target="_blank" rel="noopener noreferrer">
            <LinkOutlined />
          </a>
        </Tooltip>
      ) : '-',
    },
    {
      title: '關聯公文',
      key: 'linked_documents',
      width: 155,
      render: (_, record) => {
        const docs = record.linked_documents || [];
        if (docs.length === 0) return <Text type="secondary">-</Text>;
        // 依日期排序（最新的在前）
        const sortedDocs = [...docs].sort((a, b) => {
          const dateA = a.doc_date || '';
          const dateB = b.doc_date || '';
          return dateB.localeCompare(dateA);
        });
        return (
          <Space direction="vertical" size={0}>
            {sortedDocs.slice(0, 2).map((doc) => {
              const correctedType = detectLinkType(doc.doc_number);
              const isAgency = correctedType === 'agency_incoming';
              return (
                <Tooltip key={doc.link_id} title={doc.subject || ''}>
                  <Tag color={isAgency ? 'cyan' : 'orange'} style={{ marginBottom: 2, fontSize: 11 }}>
                    {doc.doc_number || `#${doc.document_id}`}
                  </Tag>
                </Tooltip>
              );
            })}
            {sortedDocs.length > 2 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                +{sortedDocs.length - 2} 筆
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '關聯工程',
      key: 'linked_projects',
      width: 145,
      render: (_, record) => {
        const projects = record.linked_projects || [];
        if (projects.length === 0) return <Text type="secondary">-</Text>;
        return (
          <Space direction="vertical" size={0}>
            {projects.slice(0, 2).map((proj) => (
              <Tooltip key={proj.id} title={proj.project_name}>
                <Tag color="purple" style={{ marginBottom: 2, fontSize: 11 }}>
                  {proj.project_name?.slice(0, 10) || `工程#${proj.id}`}
                </Tag>
              </Tooltip>
            ))}
            {projects.length > 2 && (
              <Text type="secondary" style={{ fontSize: 11 }}>
                +{projects.length - 2} 筆
              </Text>
            )}
          </Space>
        );
      },
    },
    {
      title: '附件',
      key: 'attachment_count',
      width: 60,
      align: 'center',
      render: (_, record) => {
        const count = record.attachment_count ?? 0;
        if (count === 0) return <Text type="secondary">-</Text>;
        return (
          <Tooltip title={`${count} 個附件`}>
            <Button
              type="link"
              size="small"
              icon={<PaperClipOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                // 導航到派工單詳情頁的附件 Tab
                navigate(`/taoyuan/dispatch/${record.id}?tab=attachments`);
              }}
            >
              {count}
            </Button>
          </Tooltip>
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
              title="關聯公文"
              value={orders.reduce((sum, o) => sum + (o.linked_documents?.length ?? 0), 0)}
              valueStyle={{ color: '#1890ff' }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="關聯工程"
              value={orders.reduce((sum, o) => sum + (o.linked_projects?.length ?? 0), 0)}
              valueStyle={{ color: '#52c41a' }}
              prefix={<LinkOutlined />}
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

      {/* 提示文字 */}
      <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
        <Text type="secondary">點擊列表項目可進入詳情頁進行編輯</Text>
      </div>

      {/* 派工紀錄表格 - 點擊行導航到詳情頁 */}
      <Table
        columns={columns}
        dataSource={orders}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1250 }}
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
