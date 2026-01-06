import React, { useState } from 'react';
import { Button, message, Tooltip } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { documentsApi } from '../../api/documentsApi';

const ExportButton = ({ filters = {}, disabled = false, children }) => {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      await documentsApi.exportDocuments({
        category: filters.category,
        year: filters.year,
      });
      message.success('匯出成功！檔案已開始下載');
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error('匯出失敗，請稍後再試');
    } finally {
      setExporting(false);
    }
  };

  return (
    <Tooltip title="匯出目前篩選結果為Excel檔案">
      <Button
        type="primary"
        icon={<DownloadOutlined />}
        onClick={handleExport}
        loading={exporting}
        disabled={disabled}
      >
        {children || '匯出Excel'}
      </Button>
    </Tooltip>
  );
};

export default ExportButton;
