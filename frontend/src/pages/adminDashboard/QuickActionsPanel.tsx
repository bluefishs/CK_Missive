import React from 'react';
import { Card, Row, Col, Tag, Button, Space, Typography } from 'antd';

const { Text } = Typography;

interface QuickAction {
  title: string;
  description: string;
  tags: Array<{ label: string; color: string }>;
  buttonLabel: string;
  buttonKey: string;
  onNavigate: () => void;
}

interface QuickActionsPanelProps {
  actions: QuickAction[];
}

const QuickActionsPanel: React.FC<QuickActionsPanelProps> = ({ actions }) => (
  <Row gutter={16}>
    {actions.map((action) => (
      <Col xs={24} md={8} key={action.buttonKey}>
        <Card
          title={action.title}
          actions={[
            <Button key={action.buttonKey} type="link" onClick={action.onNavigate}>
              {action.buttonLabel}
            </Button>
          ]}
        >
          <Space vertical style={{ width: '100%' }}>
            <Text>{action.description}</Text>
            <div>
              {action.tags.map((tag) => (
                <Tag key={tag.label} color={tag.color}>
                  {tag.label}
                </Tag>
              ))}
            </div>
          </Space>
        </Card>
      </Col>
    ))}
  </Row>
);

export default QuickActionsPanel;
