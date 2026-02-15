/**
 * 桃園查估派工 - 派工紀錄 Tab
 *
 * 導航模式設計：
 * - 新增派工單導航到獨立的新增頁面
 * - 點擊列表項目導航至派工單詳情頁進行編輯
 *
 * @version 1.3.0 - 新增文字欄位 (分案名稱、聯絡備註、專案資料夾)
 * @date 2026-01-29
 */

import React, { useState, useCallback, useMemo } from 'react';
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
  Tooltip,
  List,
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
  RightOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import { ResponsiveTable } from '../common';
import { dispatchOrdersApi } from '../../api/taoyuanDispatchApi';
import type { DispatchOrder } from '../../types/api';
import { useTableColumnSearch } from '../../hooks/utility/useTableColumnSearch';
import { useResponsive, useTaoyuanDispatchOrders } from '../../hooks';
import { WORK_TYPE_OPTIONS } from '../../constants/taoyuanOptions';

const { Text } = Typography;
const { Search } = Input;

export interface DispatchOrdersTabProps {
  contractProjectId: number;
  contractCode: string;
}

export const DispatchOrdersTab: React.FC<DispatchOrdersTabProps> = ({
  contractProjectId,
  contractCode: _contractCode,
}) => {
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
  } = useTableColumnSearch<DispatchOrder>();

  // 使用集中的 Hook 查詢派工紀錄
  const {
    dispatchOrders: orders,
    isLoading,
    refetch,
  } = useTaoyuanDispatchOrders({
    contract_project_id: contractProjectId,
    search: searchText || undefined,
    limit: 100,
  });

  const handleCreate = useCallback(() => {
    navigate('/taoyuan/dispatch/create');
  }, [navigate]);

  const handleImport = useCallback(async (file: File) => {
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
  }, [contractProjectId, message, refetch]);

  const handleDownloadTemplate = useCallback(async () => {
    try {
      await dispatchOrdersApi.downloadImportTemplate();
    } catch (error) {
      message.error('下載範本失敗');
    }
  }, [message]);

  const dispatchCaseHandlerFilters = useMemo(() =>
    [...new Set(orders.map((o) => o.case_handler).filter(Boolean))]
      .map((h) => ({ text: h as string, value: h as string })),
    [orders]
  );

  const dispatchSurveyUnitFilters = useMemo(() =>
    [...new Set(orders.map((o) => o.survey_unit).filter(Boolean))]
      .map((s) => ({ text: s as string, value: s as string })),
    [orders]
  );

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

  // 欄位順序：序、派工單號、工程名稱、作業類別、履約期限、承辦、查估單位、雲端、關聯公文、關聯工程、附件
  const columns: ColumnsType<DispatchOrder> = [
    {
      title: '序',
      key: 'rowIndex',
      width: 40,
      fixed: 'left',
      align: 'center',
      render: (_: unknown, __: DispatchOrder, index: number) => index + 1,
    },
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 125,
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
      width: 180,
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
          <Tooltip title={val}><span>{val}</span></Tooltip>
        ),
    },
    {
      title: '作業類別',
      dataIndex: 'work_type',
      width: 140,
      ellipsis: false,
      filters: WORK_TYPE_OPTIONS.map((opt) => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => (record.work_type || '').includes(value as string),
      render: (val?: string) => {
        if (!val) return '-';
        const types = val.split(',').map((t) => t.trim()).filter(Boolean);
        if (types.length === 1) {
          return <Tag color="blue">{types[0]}</Tag>;
        }
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
      width: 105,
      ellipsis: true,
      sorter: (a, b) => (a.deadline ?? '').localeCompare(b.deadline ?? ''),
      render: (val?: string) => val ? (
        <Tooltip title={val}>
          <span style={{ fontSize: 12 }}>{val}</span>
        </Tooltip>
      ) : '-',
    },
    {
      title: '承辦',
      dataIndex: 'case_handler',
      width: 65,
      align: 'center',
      ellipsis: true,
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: dispatchCaseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
      render: (val?: string) => val ? (
        <Tooltip title={val}><span>{val}</span></Tooltip>
      ) : '-',
    },
    {
      title: '查估單位',
      dataIndex: 'survey_unit',
      width: 100,
      ellipsis: true,
      filters: dispatchSurveyUnitFilters,
      onFilter: (value, record) => record.survey_unit === value,
      render: (val?: string) => val ? (
        <Tooltip title={val}><span>{val}</span></Tooltip>
      ) : '-',
    },
    {
      title: '雲端',
      dataIndex: 'cloud_folder',
      width: 50,
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
      width: 130,
      render: (_, record) => {
        const docs = record.linked_documents || [];
        if (docs.length === 0) return <Text type="secondary">-</Text>;
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
      width: 120,
      render: (_, record) => {
        const projects = record.linked_projects || [];
        if (projects.length === 0) return <Text type="secondary">-</Text>;
        return (
          <Space direction="vertical" size={0}>
            {projects.slice(0, 2).map((proj) => (
              <Tooltip key={proj.id} title={proj.project_name}>
                <Tag color="purple" style={{ marginBottom: 2, fontSize: 11 }}>
                  {proj.project_name?.slice(0, 8) || `工程#${proj.id}`}
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
      width: 50,
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

  const handleRowClick = useCallback((record: DispatchOrder) => {
    navigate(`/taoyuan/dispatch/${record.id}`);
  }, [navigate]);

  // 手機版卡片清單
  const MobileDispatchList = () => (
    <List
      dataSource={orders}
      loading={isLoading}
      pagination={{
        size: 'small',
        pageSize: 10,
        showTotal: (total) => `共 ${total} 筆`,
      }}
      renderItem={(order) => (
        <Card
          size="small"
          style={{ marginBottom: 8, cursor: 'pointer' }}
          onClick={() => handleRowClick(order)}
          hoverable
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <Text strong style={{ color: '#1890ff', fontSize: 13 }}>
                {order.dispatch_no}
              </Text>
              <div style={{ fontSize: 13, marginTop: 2 }}>
                {order.project_name}
              </div>
              <Space wrap size={4} style={{ marginTop: 6 }}>
                {order.work_type && (
                  <Tag color="blue" style={{ fontSize: 11 }}>
                    {order.work_type.split(',')[0]}
                  </Tag>
                )}
                {order.case_handler && <Tag style={{ fontSize: 11 }}>{order.case_handler}</Tag>}
              </Space>
              {order.sub_case_name && (
                <div style={{ marginTop: 4, fontSize: 11, color: '#666' }}>
                  分案: {order.sub_case_name}
                </div>
              )}
              {order.contact_note && (
                <div style={{ fontSize: 11, color: '#888' }}>
                  備註: {order.contact_note}
                </div>
              )}
              <div style={{ marginTop: 6, fontSize: 11, color: '#999' }}>
                公文: {order.linked_documents?.length || 0} |
                工程: {order.linked_projects?.length || 0} |
                附件: {order.attachment_count || 0}
              </div>
            </div>
            <RightOutlined style={{ color: '#ccc', marginTop: 4 }} />
          </div>
        </Card>
      )}
    />
  );

  const stats = useMemo(() => ({
    total: orders.length,
    linkedDocs: orders.reduce((sum, o) => sum + (o.linked_documents?.length ?? 0), 0),
    linkedProjects: orders.reduce((sum, o) => sum + (o.linked_projects?.length ?? 0), 0),
    workTypes: new Set(orders.map((o) => o.work_type).filter(Boolean)).size,
  }), [orders]);

  return (
    <div>
      {/* 統計卡片 - RWD 響應式 */}
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '總數' : '總派工單數'}
              value={stats.total}
              prefix={<SendOutlined />}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '公文' : '關聯公文'}
              value={stats.linkedDocs}
              valueStyle={{ color: '#1890ff', fontSize: isMobile ? 18 : 24 }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '工程' : '關聯工程'}
              value={stats.linkedProjects}
              valueStyle={{ color: '#52c41a', fontSize: isMobile ? 18 : 24 }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card size="small">
            <Statistic
              title={isMobile ? '類別' : '作業類別數'}
              value={stats.workTypes}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 - RWD 響應式 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Search
            placeholder={isMobile ? '搜尋派工單...' : '搜尋派工單號、工程名稱'}
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
              {isMobile ? '' : '新增派工單'}
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

      {/* 派工紀錄 - RWD: 手機用卡片清單，桌面用表格 */}
      {isMobile ? (
        <MobileDispatchList />
      ) : (
        <ResponsiveTable
          columns={columns}
          dataSource={orders}
          rowKey="id"
          loading={isLoading}
          scroll={{ x: 1450 }}
          size="small"
          mobileHiddenColumns={['sub_case_name', 'contact_note', 'project_folder', 'survey_unit']}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total: number) => `共 ${total} 筆`,
          }}
          onRow={(record) => ({
            onClick: () => handleRowClick(record),
            style: { cursor: 'pointer' },
          })}
        />
      )}

      {/* Excel 匯入 Modal - RWD 響應式 */}
      <Modal
        title="Excel 匯入派工紀錄"
        open={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
        width={isMobile ? '95%' : 600}
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
