/**
 * 派工紀錄表格欄位定義 Hook
 *
 * 從 DispatchOrdersTab 提取的欄位定義，包含：
 * - 序號、派工單號、工程名稱、作業類別、履約期限
 * - 承辦、查估單位、雲端、關聯公文、關聯工程、附件
 *
 * @version 1.0.0
 * @date 2026-02-27
 */

import React, { useMemo } from 'react';
import { Typography, Space, Tag, Button, Tooltip } from 'antd';
import { LinkOutlined, PaperClipOutlined } from '@ant-design/icons';
import type { ColumnsType, ColumnType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import type { DispatchOrder } from '../../../types/api';
import { WORK_TYPE_OPTIONS } from '../../../constants/taoyuanOptions';

const { Text } = Typography;

export interface UseDispatchOrderColumnsParams {
  /** Column search text from useTableColumnSearch */
  columnSearchText: string;
  /** Currently searched column from useTableColumnSearch */
  searchedColumn: string;
  /** getColumnSearchProps function from useTableColumnSearch */
  getColumnSearchProps: (dataIndex: keyof DispatchOrder) => ColumnType<DispatchOrder>;
  /** React Router navigate function */
  navigate: (path: string) => void;
  /** Dynamic filter values for case_handler column */
  dispatchCaseHandlerFilters: { text: string; value: string }[];
  /** Dynamic filter values for survey_unit column */
  dispatchSurveyUnitFilters: { text: string; value: string }[];
}

/**
 * Detect link type based on document number prefix.
 * Documents starting with "乾坤" are company outgoing; all others are agency incoming.
 */
const detectLinkType = (docNumber?: string): 'agency_incoming' | 'company_outgoing' => {
  if (!docNumber) return 'agency_incoming';
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  return 'agency_incoming';
};

/**
 * Custom hook that returns table column definitions for dispatch orders.
 *
 * Column order: 序、派工單號、工程名稱、作業類別、履約期限、承辦、查估單位、雲端、關聯公文、關聯工程、附件
 */
export function useDispatchOrderColumns({
  columnSearchText,
  searchedColumn,
  getColumnSearchProps,
  navigate,
  dispatchCaseHandlerFilters,
  dispatchSurveyUnitFilters,
}: UseDispatchOrderColumnsParams): ColumnsType<DispatchOrder> {
  const columns: ColumnsType<DispatchOrder> = useMemo(() => [
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
  ], [
    columnSearchText,
    searchedColumn,
    getColumnSearchProps,
    navigate,
    dispatchCaseHandlerFilters,
    dispatchSurveyUnitFilters,
  ]);

  return columns;
}

export default useDispatchOrderColumns;
