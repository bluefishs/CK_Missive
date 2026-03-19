import React from 'react';
import {
  Modal,
  Select,
  Space,
  Typography,
  Row,
  Col,
  Divider,
  Button,
  Card,
  Tag,
} from 'antd';
import { SwapOutlined } from '@ant-design/icons';
import type {
  PromptVersionItem,
  PromptCompareResponse,
} from '../../../types/ai';

const { Text, Paragraph } = Typography;

const FEATURE_LABELS: Record<string, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  search_intent: '搜尋意圖解析',
  match_agency: '機關匹配',
};

interface PromptCompareModalProps {
  visible: boolean;
  items: PromptVersionItem[];
  compareIds: { a: number | null; b: number | null };
  compareResult: PromptCompareResponse | null;
  comparing: boolean;
  onCompareIdsChange: (ids: { a: number | null; b: number | null }) => void;
  onCompare: () => void;
  onClose: () => void;
}

export const PromptCompareModal: React.FC<PromptCompareModalProps> = ({
  visible,
  items,
  compareIds,
  compareResult,
  comparing,
  onCompareIdsChange,
  onCompare,
  onClose,
}) => {
  return (
    <Modal
      title="版本比較"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={900}
    >
      <Space vertical size="middle" style={{ width: '100%' }}>
        <Row gutter={16}>
          <Col span={10}>
            <Select
              style={{ width: '100%' }}
              placeholder="選擇版本 A"
              value={compareIds.a}
              onChange={(v) => onCompareIdsChange({ ...compareIds, a: v })}
              options={items.map((item) => ({
                value: item.id,
                label: `[${FEATURE_LABELS[item.feature] || item.feature}] v${item.version}${item.is_active ? ' (啟用中)' : ''}`,
              }))}
            />
          </Col>
          <Col span={4} style={{ textAlign: 'center', lineHeight: '32px' }}>
            <SwapOutlined style={{ fontSize: 20 }} />
          </Col>
          <Col span={10}>
            <Select
              style={{ width: '100%' }}
              placeholder="選擇版本 B"
              value={compareIds.b}
              onChange={(v) => onCompareIdsChange({ ...compareIds, b: v })}
              options={items.map((item) => ({
                value: item.id,
                label: `[${FEATURE_LABELS[item.feature] || item.feature}] v${item.version}${item.is_active ? ' (啟用中)' : ''}`,
              }))}
            />
          </Col>
        </Row>

        <Button
          type="primary"
          onClick={onCompare}
          loading={comparing}
          disabled={!compareIds.a || !compareIds.b}
          block
        >
          比較
        </Button>

        {compareResult && (
          <div>
            <Divider />
            {compareResult.diffs.map((diff) => (
              <Card
                key={diff.field}
                size="small"
                title={
                  <Space>
                    <Text strong>{diff.field}</Text>
                    {diff.changed ? (
                      <Tag color="orange">有差異</Tag>
                    ) : (
                      <Tag color="green">相同</Tag>
                    )}
                  </Space>
                }
                style={{ marginBottom: 12 }}
              >
                {diff.changed ? (
                  <Row gutter={16}>
                    <Col span={12}>
                      <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                        版本 A (v{compareResult.version_a.version})
                      </Text>
                      <div
                        style={{
                          background: '#fff2f0',
                          padding: 8,
                          borderRadius: 4,
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          maxHeight: 200,
                          overflow: 'auto',
                        }}
                      >
                        {diff.value_a || '(空)'}
                      </div>
                    </Col>
                    <Col span={12}>
                      <Text type="secondary" style={{ display: 'block', marginBottom: 4 }}>
                        版本 B (v{compareResult.version_b.version})
                      </Text>
                      <div
                        style={{
                          background: '#f6ffed',
                          padding: 8,
                          borderRadius: 4,
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          fontSize: 12,
                          maxHeight: 200,
                          overflow: 'auto',
                        }}
                      >
                        {diff.value_b || '(空)'}
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Paragraph
                    style={{
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace',
                      fontSize: 12,
                      maxHeight: 200,
                      overflow: 'auto',
                      margin: 0,
                    }}
                  >
                    {diff.value_a || '(空)'}
                  </Paragraph>
                )}
              </Card>
            ))}
          </div>
        )}
      </Space>
    </Modal>
  );
};
