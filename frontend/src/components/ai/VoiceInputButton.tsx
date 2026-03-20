/**
 * VoiceInputButton - 按住說話語音輸入按鈕
 *
 * 使用 MediaRecorder API 錄音，鬆開後上傳至後端 Groq Whisper 轉文字。
 *
 * @version 1.0.0
 * @created 2026-03-20
 */

import React, { useRef, useState, useCallback } from 'react';
import { Button, Tooltip, message } from 'antd';
import { AudioOutlined, LoadingOutlined } from '@ant-design/icons';
import { transcribeVoice } from '../../api/ai/adminManagement';

interface VoiceInputButtonProps {
  /** 語音辨識完成後回傳文字 */
  onTranscribed: (text: string) => void;
  /** 是否禁用 */
  disabled?: boolean;
}

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onTranscribed,
  disabled = false,
}) => {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });

      chunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });

        if (blob.size < 1000) {
          message.warning('錄音時間太短，請按住按鈕說話');
          return;
        }

        setTranscribing(true);
        try {
          const result = await transcribeVoice(blob);
          if (result.text) {
            onTranscribed(result.text);
          }
        } catch {
          message.error('語音辨識失敗，請改用文字輸入');
        } finally {
          setTranscribing(false);
        }
      };

      mediaRecorder.start(100); // 每 100ms 收集一次
      mediaRecorderRef.current = mediaRecorder;
      setRecording(true);
    } catch {
      message.error('無法存取麥克風，請確認瀏覽器權限');
    }
  }, [onTranscribed]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    setRecording(false);
  }, []);

  if (transcribing) {
    return (
      <Button
        shape="circle"
        icon={<LoadingOutlined />}
        disabled
        title="辨識中..."
      />
    );
  }

  return (
    <Tooltip title="按住說話" placement="top">
      <Button
        shape="circle"
        icon={<AudioOutlined />}
        type={recording ? 'primary' : 'default'}
        danger={recording}
        disabled={disabled}
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onMouseLeave={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        style={recording ? { animation: 'pulse 1s infinite' } : undefined}
      />
    </Tooltip>
  );
};

export default VoiceInputButton;
