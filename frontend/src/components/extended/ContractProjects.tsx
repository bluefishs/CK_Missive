import React, { useState, useEffect } from 'react';

interface Project {
  id: number;
  project_name: string;
  project_code: string;
  year: number;
  category: string;
  status: string;
  client_agency: string;
  contract_amount: number;
}

export const ContractProjects: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/extended/projects');
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>載入中...</div>;
  }

  return (
    <div className="contract-projects">
      <h1>承攬案件管理</h1>
      <div className="projects-grid">
        {projects.map(project => (
          <div key={project.id} className="project-card">
            <h3>{project.project_name}</h3>
            <p>案件編號: {project.project_code}</p>
            <p>年度: {project.year}</p>
            <p>類別: {project.category}</p>
            <p>狀態: {project.status}</p>
            <p>委辦機關: {project.client_agency}</p>
            {project.contract_amount && (
              <p>契約金額: NT${project.contract_amount.toLocaleString()}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};