import { useNavigate } from 'react-router-dom';
import { useCallback } from 'react';

export const useAppNavigation = () => {
  const navigate = useNavigate();

  const goBack = useCallback(() => {
    navigate(-1);
  }, [navigate]);

  const goTo = useCallback((path: string) => {
    navigate(path);
  }, [navigate]);

  const goToDocument = useCallback((id: number) => {
    navigate(`/documents/${id}`);
  }, [navigate]);

  const goToDocumentEdit = useCallback((id: number) => {
    navigate(`/documents/${id}/edit`);
  }, [navigate]);

  const goToDocumentCreate = useCallback(() => {
    navigate('/documents/create');
  }, [navigate]);

  const goToDocuments = useCallback(() => {
    navigate('/documents');
  }, [navigate]);

  const goToDashboard = useCallback(() => {
    navigate('/');
  }, [navigate]);

  return {
    goBack,
    goTo,
    goToDocument,
    goToDocumentEdit,
    goToDocumentCreate,
    goToDocuments,
    goToDashboard,
  };
};