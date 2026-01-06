import React, { useState, useEffect } from 'react';
import {
  Input,
  Select,
  Space,
  Button,
  Typography,
  Tooltip,
  Modal,
  Form,
  Card,
  Row,
  Col,
  Divider,
  App
} from 'antd';
import {
  NumberOutlined,
  ReloadOutlined,
  SettingOutlined,
  CopyOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;
const { Option } = Select;

export interface SequenceConfig {
  prefix?: string;           // 前綴，如 "DOC", "PRJ"
  dateFormat?: string;       // 日期格式，如 "YYYYMMDD", "YYYY-MM"
  separator?: string;        // 分隔符，如 "-", "_"
  numberLength?: number;     // 流水號長度，用0補齊
  suffix?: string;          // 後綴
}

export interface SequenceNumberGeneratorProps {
  value?: string;
  onChange?: (value: string) => void;
  config?: SequenceConfig;
  category?: string;        // 分類，用於區分不同類型的流水號
  disabled?: boolean;
  placeholder?: string;
  allowManualEdit?: boolean; // 是否允許手動編輯
  showPreview?: boolean;    // 是否顯示預覽
  autoGenerate?: boolean;   // 是否自動生成
}

// 預設配置
const DEFAULT_CONFIGS: Record<string, SequenceConfig> = {
  document: {
    prefix: 'DOC',
    dateFormat: 'YYYYMMDD',
    separator: '-',
    numberLength: 4,
    suffix: ''
  },
  project: {
    prefix: 'PRJ',
    dateFormat: 'YYYY',
    separator: '-',
    numberLength: 3,
    suffix: ''
  },
  vendor: {
    prefix: 'VEN',
    dateFormat: 'YYYYMM',
    separator: '',
    numberLength: 3,
    suffix: ''
  },
  agency: {
    prefix: 'AGY',
    dateFormat: 'YYYY',
    separator: '-',
    numberLength: 2,
    suffix: ''
  }
};

const SequenceNumberGenerator: React.FC<SequenceNumberGeneratorProps> = ({
  value,
  onChange,
  config,
  category = 'document',
  disabled = false,
  placeholder = '點擊生成流水號',
  allowManualEdit = true,
  showPreview = true,
  autoGenerate = false
}) => {
  const { message } = App.useApp();
  const [currentNumber, setCurrentNumber] = useState<string>(value || '');
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const getInitialConfig = (): SequenceConfig => {
    if (config) return config;
    if (category && DEFAULT_CONFIGS[category]) return DEFAULT_CONFIGS[category]!;
    return DEFAULT_CONFIGS.document!;
  };
  const [currentConfig, setCurrentConfig] = useState<SequenceConfig>(getInitialConfig);
  const [form] = Form.useForm();

  useEffect(() => {
    if (autoGenerate && !value) {
      generateSequenceNumber();
    }
  }, [autoGenerate, value]);

  useEffect(() => {
    setCurrentNumber(value || '');
  }, [value]);

  // 生成流水號
  const generateSequenceNumber = () => {
    const now = dayjs();
    const parts: string[] = [];

    // 前綴
    if (currentConfig.prefix) {
      parts.push(currentConfig.prefix);
    }

    // 日期部分
    if (currentConfig.dateFormat) {
      parts.push(now.format(currentConfig.dateFormat));
    }

    // 流水號部分
    const sequenceNum = getNextSequenceNumber();
    if (currentConfig.numberLength) {
      parts.push(String(sequenceNum).padStart(currentConfig.numberLength, '0'));
    } else {
      parts.push(String(sequenceNum));
    }

    // 後綴
    if (currentConfig.suffix) {
      parts.push(currentConfig.suffix);
    }

    // 用分隔符連接
    const separator = currentConfig.separator || '';
    const newSequenceNumber = parts.join(separator);

    setCurrentNumber(newSequenceNumber);
    onChange?.(newSequenceNumber);
    
    message.success('流水號已生成');
  };

  // 獲取下一個流水號（模擬邏輯）
  const getNextSequenceNumber = (): number => {
    // 這裡應該從後端獲取當前類別的最新流水號
    // 暫時使用隨機數模擬
    const today = dayjs().format('YYYYMMDD');
    const storageKey = `sequence_${category}_${today}`;
    const lastNumber = parseInt(localStorage.getItem(storageKey) || '0', 10);
    const nextNumber = lastNumber + 1;
    localStorage.setItem(storageKey, String(nextNumber));
    return nextNumber;
  };

  // 手動編輯
  const handleManualChange = (newValue: string) => {
    setCurrentNumber(newValue);
    onChange?.(newValue);
  };

  // 複製到剪貼板
  const copyToClipboard = () => {
    if (currentNumber) {
      navigator.clipboard.writeText(currentNumber);
      message.success('已複製到剪貼板');
    }
  };

  // 保存配置
  const saveConfig = (values: SequenceConfig) => {
    setCurrentConfig(values);
    setConfigModalVisible(false);
    message.success('配置已更新');
  };

  // 預覽格式
  const getPreviewText = () => {
    const now = dayjs();
    const parts: string[] = [];

    if (currentConfig.prefix) {
      parts.push(`[前綴:${currentConfig.prefix}]`);
    }
    if (currentConfig.dateFormat) {
      parts.push(`[日期:${now.format(currentConfig.dateFormat)}]`);
    }
    parts.push(`[流水號:${'0'.repeat(currentConfig.numberLength || 1)}1]`);
    if (currentConfig.suffix) {
      parts.push(`[後綴:${currentConfig.suffix}]`);
    }

    return parts.join(currentConfig.separator || '');
  };

  return (
    <Space.Compact style={{ width: '100%' }}>
      <Input
        value={currentNumber}
        onChange={(e) => handleManualChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled || !allowManualEdit}
        prefix={<NumberOutlined />}
        suffix={
          currentNumber && (
            <Tooltip title="複製">
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={copyToClipboard}
                style={{ padding: 0 }}
              />
            </Tooltip>
          )
        }
      />
      
      <Tooltip title="生成新流水號">
        <Button
          icon={<ReloadOutlined />}
          onClick={generateSequenceNumber}
          disabled={disabled}
        />
      </Tooltip>

      <Tooltip title="流水號配置">
        <Button
          icon={<SettingOutlined />}
          onClick={() => {
            form.setFieldsValue(currentConfig);
            setConfigModalVisible(true);
          }}
          disabled={disabled}
        />
      </Tooltip>

      {/* 配置 Modal */}
      <Modal
        title="流水號格式配置"
        open={configModalVisible}
        onCancel={() => setConfigModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={saveConfig}
          initialValues={currentConfig}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="prefix"
                label="前綴"
                extra="例如: DOC, PRJ, VEN"
              >
                <Input placeholder="輸入前綴" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="suffix"
                label="後綴"
              >
                <Input placeholder="輸入後綴" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="dateFormat"
                label="日期格式"
                extra="支援 dayjs 格式"
              >
                <Select placeholder="選擇日期格式">
                  <Option value="">無日期</Option>
                  <Option value="YYYY">年份 (2024)</Option>
                  <Option value="YYYY-MM">年月 (2024-01)</Option>
                  <Option value="YYYYMM">年月 (202401)</Option>
                  <Option value="YYYY-MM-DD">年月日 (2024-01-01)</Option>
                  <Option value="YYYYMMDD">年月日 (20240101)</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="separator"
                label="分隔符"
              >
                <Select placeholder="選擇分隔符">
                  <Option value="">無分隔符</Option>
                  <Option value="-">連字號 (-)</Option>
                  <Option value="_">底線 (_)</Option>
                  <Option value=".">點 (.)</Option>
                  <Option value="/">斜線 (/)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="numberLength"
            label="流水號長度"
            extra="指定流水號的位數，不足時用0補齊"
          >
            <Select placeholder="選擇位數">
              <Option value={1}>1位</Option>
              <Option value={2}>2位</Option>
              <Option value={3}>3位</Option>
              <Option value={4}>4位</Option>
              <Option value={5}>5位</Option>
              <Option value={6}>6位</Option>
            </Select>
          </Form.Item>

          <Divider />

          <Card size="small" style={{ backgroundColor: '#f0f2f5' }}>
            <Row align="middle">
              <Col flex={1}>
                <Space>
                  <InfoCircleOutlined style={{ color: '#1890ff' }} />
                  <Text strong>預覽格式:</Text>
                  <Text code>{getPreviewText()}</Text>
                </Space>
              </Col>
            </Row>
          </Card>

          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setConfigModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                保存配置
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>

      {/* 預覽提示 */}
      {showPreview && !currentNumber && (
        <div style={{ marginTop: 4 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            格式預覽: {getPreviewText()}
          </Text>
        </div>
      )}
    </Space.Compact>
  );
};

export default SequenceNumberGenerator;