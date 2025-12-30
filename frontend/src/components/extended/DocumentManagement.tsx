import React, { useState, useEffect } from 'react';

interface Document {
  id: number;
  doc_number: string;
  doc_type: string;
  subject: string;
  sender_agency: string;
  receiver_agency: string;
  doc_date: string;
  status: string;
}

export const DocumentManagement: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/extended/documents');
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>載入中...</div>;
  }

  return (
    <div className="document-management">
      <h1>公文管理系統</h1>
      <div className="documents-list">
        {documents.map(document => (
          <div key={document.id} className="document-item">
            <h3>{document.subject}</h3>
            <p>公文字號: {document.doc_number}</p>
            <p>類型: {document.doc_type}</p>
            <p>發文機關: {document.sender_agency}</p>
            <p>收文機關: {document.receiver_agency}</p>
            <p>日期: {document.doc_date}</p>
            <p>狀態: {document.status}</p>
          </div>
        ))}
      </div>
    </div>
  );
};