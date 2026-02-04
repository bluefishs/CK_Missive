/**
 * AI 回饋按鈕組件
 *
 * 讓使用者對 AI 助理的回應提供快速回饋，
 * 用於改進 AI 服務品質。
 *
 * @version 1.0.0
 * @created 2026-02-05
 * @reference CK_lvrland_Webmap/frontend/src/components/AI/AIFeedbackButton.tsx
 */

import React, { useState, useCallback } from 'react';
import {
  Button,
  Tooltip,
  Popover,
  Space,
  Rate,
  Input,
  message,
  Typography,
} from 'antd';
import {
  LikeOutlined,
  DislikeOutlined,
  QuestionCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { logger } from '../../services/logger';

const { TextArea } = Input;
const { Text } = Typography;

interface AIFeedbackButtonProps {
  /** AI 功能類型 */
  featureType: 'summary' | 'classify' | 'keywords' | 'agency_match';
  /** 原始輸入 */
  input?: string;
  /** AI 回應結果 */
  result?: string;
  /** 按鈕大小 */
  size?: 'small' | 'middle' | 'large';
  /** 回饋成功回調 */
  onFeedbackSuccess?: () => void;
}

// 功能類型中文名稱
const FEATURE_NAMES: Record<string, string> = {
  summary: '摘要生成',
  classify: '分類建議',
  keywords: '關鍵字提取',
  agency_match: '機關匹配',
};

const AIFeedbackButton: React.FC<AIFeedbackButtonProps> = ({
  featureType,
  input,
  result,
  size = 'small',
  onFeedbackSuccess,
}) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'correct' | 'incorrect' | null>(null);
  const [score, setScore] = useState(3);
  const [comment, setComment] = useState('');

  // 快速回饋 (讚/倒讚)
  const handleQuickFeedback = useCallback(
    async (type: 'correct' | 'incorrect') => {
      setLoading(true);
      try {
        // 記錄回饋到日誌（未來可擴展為 API 呼叫）
        logger.log('AI 回饋:', {
          feature_type: featureType,
          feedback_type: type,
          feedback_score: type === 'correct' ? 5 : 2,
          input_preview: input?.substring(0, 50),
          result_preview: result?.substring(0, 50),
        });

        message.success(type === 'correct' ? '感謝您的回饋！' : '感謝回報，我們會持續改進');
        setFeedbackType(type);
        onFeedbackSuccess?.();
      } catch (error) {
        logger.error('回饋提交失敗:', error);
        message.error('回饋提交失敗，請稍後再試');
      } finally {
        setLoading(false);
      }
    },
    [featureType, input, result, onFeedbackSuccess]
  );

  // 詳細回饋提交
  const handleDetailedFeedback = useCallback(async () => {
    setLoading(true);
    try {
      // 記錄詳細回饋到日誌（未來可擴展為 API 呼叫）
      logger.log('AI 詳細回饋:', {
        feature_type: featureType,
        feedback_score: score,
        feedback_comment: comment,
        input_preview: input?.substring(0, 50),
        result_preview: result?.substring(0, 50),
      });

      message.success('詳細回饋已提交，感謝您的協助！');
      setOpen(false);
      setFeedbackType('correct');
      onFeedbackSuccess?.();
    } catch (error) {
      logger.error('回饋提交失敗:', error);
      message.error('回饋提交失敗，請稍後再試');
    } finally {
      setLoading(false);
    }
  }, [featureType, score, comment, input, result, onFeedbackSuccess]);

  // 已提交回饋後顯示確認圖示
  if (feedbackType) {
    return (
      <Tooltip title="已收到回饋">
        <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />
      </Tooltip>
    );
  }

  // 詳細回饋彈出內容
  const detailedFeedbackContent = (
    <div style={{ width: 260 }}>
      <Text strong style={{ display: 'block', marginBottom: 12 }}>
        {FEATURE_NAMES[featureType] || featureType} 回饋
      </Text>

      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          滿意度評分
        </Text>
        <Rate value={score} onChange={setScore} style={{ display: 'block', marginTop: 4 }} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          補充說明 (選填)
        </Text>
        <TextArea
          placeholder="您的建議..."
          rows={2}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          style={{ marginTop: 4 }}
          maxLength={200}
        />
      </div>

      <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
        <Button size="small" onClick={() => setOpen(false)}>
          取消
        </Button>
        <Button type="primary" size="small" loading={loading} onClick={handleDetailedFeedback}>
          提交
        </Button>
      </Space>
    </div>
  );

  return (
    <Space size={4}>
      <Tooltip title="結果正確">
        <Button
          type="text"
          size={size}
          icon={<LikeOutlined />}
          loading={loading}
          onClick={() => handleQuickFeedback('correct')}
          style={{ color: '#8c8c8c' }}
        />
      </Tooltip>

      <Tooltip title="結果有誤">
        <Button
          type="text"
          size={size}
          icon={<DislikeOutlined />}
          loading={loading}
          onClick={() => handleQuickFeedback('incorrect')}
          style={{ color: '#8c8c8c' }}
        />
      </Tooltip>

      <Popover
        content={detailedFeedbackContent}
        title={null}
        trigger="click"
        open={open}
        onOpenChange={setOpen}
        placement="topRight"
      >
        <Tooltip title="詳細回饋">
          <Button
            type="text"
            size={size}
            icon={<QuestionCircleOutlined />}
            style={{ color: '#8c8c8c' }}
          />
        </Tooltip>
      </Popover>
    </Space>
  );
};

export default AIFeedbackButton;
