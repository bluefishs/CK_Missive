import React, { useState } from 'react';
import {
  Modal,
  Upload,
  Button,
  Tabs,
  Alert,
  Space,
  Typography,
  Divider,
  List,
  Tag,
  Progress,
  Card,
  Result,
  Table,
  Tooltip,
} from 'antd';
import {
  FileExcelOutlined,
  FileTextOutlined,
  DownloadOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  EyeOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { API_BASE_URL } from '../../api/client';

const { Dragger } = Upload;
const { Text, Title } = Typography;

interface PreviewRow {
  row: number;
  data: Record<string, unknown>;
  status: 'valid' | 'warning';
  issues: string[];
  action: 'insert' | 'update';
}

interface PreviewResult {
  success: boolean;
  filename: string;
  total_rows: number;
  preview_rows: PreviewRow[];
  headers: string[];
  validation: {
    missing_required_fields: string[];
    invalid_categories: number[];
    invalid_doc_types: number[];
    duplicate_doc_numbers: number[];
    existing_in_db: number[];  // 資料庫中已存在的公文字號
    will_insert: number;
    will_update: number;
  };
  errors: string[];
}

interface ImportResult {
  success: boolean;
  filename: string;
  total_rows: number;
  inserted: number;
  updated: number;
  skipped: number;
  errors: string[];
  details?: Array<{
    row: number;
    status: string;
    message: string;
    doc_number: string;
  }>;
}

interface DocumentImportProps {
  visible: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type ImportStep = 'upload' | 'preview' | 'result';

export const DocumentImport: React.FC<DocumentImportProps> = ({
  visible,
  onClose,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<string>('excel');
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [step, setStep] = useState<ImportStep>('upload');
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);

  // 重置狀態
  const handleReset = () => {
    setStep('upload');
    setPreviewResult(null);
    setImportResult(null);
    setCurrentFile(null);
  };

  // 關閉時重置
  const handleClose = () => {
    handleReset();
    onClose();
  };

  // 匯入成功後回調
  const handleImportSuccess = () => {
    if (onSuccess) {
      onSuccess();
    }
  };

  // Excel 預覽處理
  const handleExcelPreview = async (file: File) => {
    setUploading(true);
    setCurrentFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/import/excel/preview`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      setPreviewResult(result);
      setStep('preview');
    } catch (error) {
      setPreviewResult({
        success: false,
        filename: file.name,
        total_rows: 0,
        preview_rows: [],
        headers: [],
        validation: {
          missing_required_fields: [],
          invalid_categories: [],
          invalid_doc_types: [],
          duplicate_doc_numbers: [],
          existing_in_db: [],
          will_insert: 0,
          will_update: 0,
        },
        errors: [`預覽失敗: ${error}`],
      });
      setStep('preview');
    } finally {
      setUploading(false);
    }

    return false;
  };

  // Excel 正式匯入
  const handleExcelImport = async () => {
    if (!currentFile) return;

    setImporting(true);

    const formData = new FormData();
    formData.append('file', currentFile);

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/import/excel`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      setImportResult(result);
      setStep('result');

      if (result.success && (result.inserted > 0 || result.updated > 0)) {
        handleImportSuccess();
      }
    } catch (error) {
      setImportResult({
        success: false,
        filename: currentFile.name,
        total_rows: 0,
        inserted: 0,
        updated: 0,
        skipped: 0,
        errors: [`匯入失敗: ${error}`],
      });
      setStep('result');
    } finally {
      setImporting(false);
    }
  };

  // CSV 匯入處理 (暫時不加預覽)
  const handleCsvUpload = async (file: File) => {
    setUploading(true);
    setCurrentFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/csv-import/upload-and-import`, {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      setImportResult(result);
      setStep('result');

      if (result.success && result.inserted > 0) {
        handleImportSuccess();
      }
    } catch (error) {
      setImportResult({
        success: false,
        filename: file.name,
        total_rows: 0,
        inserted: 0,
        updated: 0,
        skipped: 0,
        errors: [`匯入失敗: ${error}`],
      });
      setStep('result');
    } finally {
      setUploading(false);
    }

    return false;
  };

  // 下載 Excel 範本
  const handleDownloadTemplate = () => {
    window.open(`${API_BASE_URL}/documents-enhanced/import/excel/template`, '_blank');
  };

  // 渲染預覽結果
  const renderPreviewResult = () => {
    if (!previewResult) return null;

    const { success, filename, total_rows, preview_rows, validation, errors } = previewResult;

    // 預覽表格欄位
    const previewColumns = [
      {
        title: '列',
        dataIndex: 'row',
        key: 'row',
        width: 50,
      },
      {
        title: '操作',
        dataIndex: 'action',
        key: 'action',
        width: 70,
        render: (action: string) => (
          <Tag color={action === 'insert' ? 'green' : 'blue'}>
            {action === 'insert' ? '新增' : '更新'}
          </Tag>
        ),
      },
      {
        title: '公文字號',
        key: 'doc_number',
        width: 180,
        render: (_: unknown, record: PreviewRow) => record.data['公文字號'] || '-',
      },
      {
        title: '主旨',
        key: 'subject',
        ellipsis: true,
        render: (_: unknown, record: PreviewRow) => record.data['主旨'] || '-',
      },
      {
        title: '狀態',
        key: 'status',
        width: 100,
        render: (_: unknown, record: PreviewRow) => {
          if (record.issues.length > 0) {
            return (
              <Tooltip title={record.issues.join('; ')}>
                <Tag icon={<WarningOutlined />} color="warning">
                  警告
                </Tag>
              </Tooltip>
            );
          }
          return (
            <Tag icon={<CheckCircleOutlined />} color="success">
              正常
            </Tag>
          );
        },
      },
    ];

    return (
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 檔案資訊 */}
          <Alert
            type={success ? 'info' : 'error'}
            message={
              <Space>
                <FileExcelOutlined />
                <Text strong>{filename}</Text>
                <Text type="secondary">({total_rows} 筆資料)</Text>
              </Space>
            }
            description={
              errors.length > 0 ? (
                <List
                  size="small"
                  dataSource={errors}
                  renderItem={(item) => (
                    <List.Item>
                      <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                      {item}
                    </List.Item>
                  )}
                />
              ) : null
            }
          />

          {/* 統計資訊 */}
          <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center', padding: '16px 0' }}>
            <div>
              <Text type="secondary">預計新增</Text>
              <Title level={4} style={{ color: '#52c41a', margin: 0 }}>{validation.will_insert}</Title>
            </div>
            <div>
              <Text type="secondary">預計更新</Text>
              <Title level={4} style={{ color: '#1890ff', margin: 0 }}>{validation.will_update}</Title>
            </div>
            {validation.duplicate_doc_numbers.length > 0 && (
              <div>
                <Text type="secondary">檔案內重複</Text>
                <Title level={4} style={{ color: '#faad14', margin: 0 }}>{validation.duplicate_doc_numbers.length}</Title>
              </div>
            )}
            {validation.existing_in_db && validation.existing_in_db.length > 0 && (
              <div>
                <Tooltip title="這些公文字號已存在於資料庫中，新增時會被跳過">
                  <Text type="secondary">資料庫已存在</Text>
                  <Title level={4} style={{ color: '#ff4d4f', margin: 0 }}>{validation.existing_in_db.length}</Title>
                </Tooltip>
              </div>
            )}
          </div>

          {/* 預覽表格 */}
          {preview_rows.length > 0 && (
            <>
              <Divider orientation="left">資料預覽（前 {preview_rows.length} 筆）</Divider>
              <Table
                dataSource={preview_rows}
                columns={previewColumns}
                rowKey="row"
                size="small"
                pagination={false}
                scroll={{ y: 200 }}
              />
            </>
          )}

          {/* 操作按鈕 */}
          <Divider />
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={handleReset}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={handleExcelImport}
              loading={importing}
              disabled={!success || errors.length > 0}
            >
              確認匯入
            </Button>
          </Space>
        </Space>
      </Card>
    );
  };

  // 渲染匯入結果
  const renderImportResult = () => {
    if (!importResult) return null;

    const { success, filename, total_rows, inserted, updated, skipped, errors, details } = importResult;

    return (
      <Card style={{ marginTop: 16 }}>
        <Result
          status={success ? 'success' : 'warning'}
          title={success ? '匯入完成' : '匯入完成（有警告）'}
          subTitle={`檔案: ${filename}`}
          extra={[
            <Button key="close" onClick={handleClose}>
              關閉
            </Button>,
            <Button key="reset" type="primary" onClick={handleReset}>
              繼續匯入
            </Button>,
          ]}
        />

        <Divider />

        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 統計資訊 */}
          <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
            <div>
              <Text type="secondary">總筆數</Text>
              <Title level={3}>{total_rows}</Title>
            </div>
            <div>
              <Text type="success">新增</Text>
              <Title level={3} style={{ color: '#52c41a' }}>{inserted}</Title>
            </div>
            <div>
              <Text type="warning">更新</Text>
              <Title level={3} style={{ color: '#faad14' }}>{updated}</Title>
            </div>
            <div>
              <Text type="secondary">跳過</Text>
              <Title level={3} style={{ color: '#8c8c8c' }}>{skipped}</Title>
            </div>
          </div>

          {/* 錯誤訊息 */}
          {errors && errors.length > 0 && (
            <>
              <Divider />
              <Alert
                type="error"
                message={`${errors.length} 個錯誤`}
                description={
                  <List
                    size="small"
                    dataSource={errors.slice(0, 10)}
                    renderItem={(item) => (
                      <List.Item>
                        <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                        {item}
                      </List.Item>
                    )}
                  />
                }
              />
            </>
          )}

          {/* 詳細結果（前 20 筆） */}
          {details && details.length > 0 && (
            <>
              <Divider />
              <Text strong>處理明細（前 20 筆）</Text>
              <List
                size="small"
                dataSource={details.slice(0, 20)}
                renderItem={(item) => (
                  <List.Item>
                    <Space>
                      <Tag>{`第 ${item.row} 列`}</Tag>
                      <Tag color={
                        item.status === 'inserted' ? 'green' :
                        item.status === 'updated' ? 'blue' :
                        item.status === 'skipped' ? 'default' : 'red'
                      }>
                        {item.status === 'inserted' ? '新增' :
                         item.status === 'updated' ? '更新' :
                         item.status === 'skipped' ? '跳過' : '錯誤'}
                      </Tag>
                      <Text ellipsis style={{ maxWidth: 300 }}>{item.message}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </>
          )}
        </Space>
      </Card>
    );
  };

  // Excel 匯入面板
  const ExcelImportPanel = () => (
    <div>
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="手動公文匯入"
        description={
          <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
            <li>適用於紙本郵寄紀錄、手動輸入的公文資料</li>
            <li>使用本系統匯出的 Excel 格式</li>
            <li>公文ID 有值 = 更新現有資料</li>
            <li>公文ID 空白 = 新增（自動產生流水號）</li>
            <li><Text type="success">支援匯入前預覽確認</Text></li>
          </ul>
        }
        style={{ marginBottom: 16 }}
      />

      <Space style={{ marginBottom: 16 }}>
        <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
          下載匯入範本
        </Button>
      </Space>

      {step === 'upload' && (
        <Dragger
          accept=".xlsx,.xls"
          showUploadList={false}
          beforeUpload={handleExcelPreview}
          disabled={uploading}
        >
          <div className="ant-upload-drag-icon">
            {uploading ? (
              <Progress type="circle" percent={-1} size={48} />
            ) : (
              <EyeOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            )}
          </div>
          <p className="ant-upload-text">
            {uploading ? '載入中...' : '點擊或拖曳 Excel 檔案預覽'}
          </p>
          <p className="ant-upload-hint">
            支援 .xlsx, .xls 格式，上傳後可預覽確認再匯入
          </p>
        </Dragger>
      )}

      {step === 'preview' && renderPreviewResult()}
      {step === 'result' && renderImportResult()}
    </div>
  );

  // CSV 匯入面板
  const CsvImportPanel = () => (
    <div>
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="電子公文檔匯入"
        description={
          <ul style={{ margin: '8px 0 0 0', paddingLeft: 20 }}>
            <li>適用於電子公文系統匯出的 CSV 檔案</li>
            <li>receiveList.csv (收文清單)</li>
            <li>sendList.csv (發文清單)</li>
            <li>自動偵測標頭、組合公文字號</li>
          </ul>
        }
        style={{ marginBottom: 16 }}
      />

      {step === 'upload' && (
        <Dragger
          accept=".csv"
          showUploadList={false}
          beforeUpload={handleCsvUpload}
          disabled={uploading}
        >
          <div className="ant-upload-drag-icon">
            {uploading ? (
              <Progress type="circle" percent={-1} size={48} />
            ) : (
              <FileTextOutlined style={{ fontSize: 48, color: '#1890ff' }} />
            )}
          </div>
          <p className="ant-upload-text">
            {uploading ? '匯入中...' : '點擊或拖曳 CSV 檔案到此處'}
          </p>
          <p className="ant-upload-hint">
            支援 receiveList.csv, sendList.csv 格式
          </p>
        </Dragger>
      )}

      {step === 'result' && renderImportResult()}
    </div>
  );

  const tabItems = [
    {
      key: 'excel',
      label: (
        <span>
          <FileExcelOutlined />
          手動公文匯入
        </span>
      ),
      children: <ExcelImportPanel />,
    },
    {
      key: 'csv',
      label: (
        <span>
          <FileTextOutlined />
          電子公文檔匯入
        </span>
      ),
      children: <CsvImportPanel />,
    },
  ];

  return (
    <Modal
      title="公文匯入"
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={800}
      destroyOnHidden
    >
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key);
          handleReset();
        }}
        items={tabItems}
      />
    </Modal>
  );
};

export default DocumentImport;
