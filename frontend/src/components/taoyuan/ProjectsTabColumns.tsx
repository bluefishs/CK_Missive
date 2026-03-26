/**
 * 桃園查估派工 - 工程資訊 Tab 欄位定義
 *
 * 從 ProjectsTab.tsx 提取的表格欄位配置
 *
 * @version 1.0.0
 * @date 2026-03-25
 */

import { Typography, Space, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import Highlighter from 'react-highlight-words';

import type { TaoyuanProject, ProjectDispatchLinkItem, ProjectDocumentLinkItem } from '../../types/api';
import {
  DISTRICT_OPTIONS,
  CASE_TYPE_OPTIONS,
} from '../../constants/taoyuanOptions';

const { Text } = Typography;

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

export interface ProjectsTabColumnsParams {
  reviewYearFilters: Array<{ text: string; value: number }>;
  caseHandlerFilters: Array<{ text: string; value: string }>;
  projects: TaoyuanProject[];
  getColumnSearchProps: (dataIndex: keyof TaoyuanProject) => object;
  searchedColumn: string;
  columnSearchText: string;
}

export function buildProjectsColumns({
  reviewYearFilters,
  caseHandlerFilters,
  projects,
  getColumnSearchProps,
  searchedColumn,
  columnSearchText,
}: ProjectsTabColumnsParams): ColumnsType<TaoyuanProject> {
  return [
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
      width: 80,
      align: 'center',
      ellipsis: true,
      sorter: (a, b) => (a.case_handler ?? '').localeCompare(b.case_handler ?? ''),
      filters: caseHandlerFilters,
      onFilter: (value, record) => record.case_handler === value,
      render: (val?: string) => val ? (
        <Tooltip title={val}><span>{val}</span></Tooltip>
      ) : '-',
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
          <Space vertical size={0}>
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
          <Space vertical size={0}>
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
}
