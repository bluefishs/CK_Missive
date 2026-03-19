/**
 * PM 案件 — 相關公文頁籤
 *
 * 透過 case_code 軟連結 ContractProject，列出關聯公文。
 */
import React from 'react';
import { Table, Empty, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { usePMLinkedDocuments } from '../../hooks/business/usePMCases';
import type { PMLinkedDocument } from '../../types/pm';

const { Link } = Typography;

interface LinkedDocsTabProps {
  caseCode: string;
}

const columns: ColumnsType<PMLinkedDocument> = [
  {
    title: '文號',
    dataIndex: 'doc_number',
    key: 'doc_number',
    width: 200,
    render: (val: string | null) => val ?? '-',
  },
  {
    title: '主旨',
    dataIndex: 'subject',
    key: 'subject',
    ellipsis: true,
    render: (val: string | null) => val ?? '-',
  },
  {
    title: '類型',
    dataIndex: 'doc_type',
    key: 'doc_type',
    width: 80,
    render: (val: string | null) => val ?? '-',
  },
  {
    title: '日期',
    dataIndex: 'doc_date',
    key: 'doc_date',
    width: 120,
    render: (val: string | null) => val ?? '-',
  },
];

const LinkedDocsTab: React.FC<LinkedDocsTabProps> = ({ caseCode }) => {
  const navigate = useNavigate();
  const { data: docs, isLoading } = usePMLinkedDocuments(caseCode);

  const handleRowClick = (record: PMLinkedDocument) => {
    navigate(`/documents/${record.id}`);
  };

  if (!isLoading && (!docs || docs.length === 0)) {
    return <Empty description="此案號尚無關聯公文" />;
  }

  return (
    <Table<PMLinkedDocument>
      rowKey="id"
      columns={[
        ...columns,
        {
          title: '操作',
          key: 'action',
          width: 80,
          render: (_: unknown, record: PMLinkedDocument) => (
            <Link onClick={() => handleRowClick(record)}>查看</Link>
          ),
        },
      ]}
      dataSource={docs ?? []}
      loading={isLoading}
      pagination={false}
      size="small"
    />
  );
};

export default LinkedDocsTab;
