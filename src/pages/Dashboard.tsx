import React from 'react';
import { Upload, TrendingUp, FileText, Zap } from 'lucide-react';
import '../styles/Dashboard.css';

const Dashboard: React.FC = () => {
  const stats = [
    { icon: FileText, label: 'Total Projects', value: '12', color: '#3B82F6' },
    { icon: TrendingUp, label: 'Analyses Run', value: '245', color: '#10B981' },
    { icon: Zap, label: 'Processing', value: '3', color: '#F59E0B' },
  ];

  return (
    <div className="dashboard">
      <section className="welcome-section">
        <div className="welcome-content">
          <h2>Welcome to One Click Analysis</h2>
          <p>Powerful data analysis made simple. Upload your CSV or Excel files and get instant insights.</p>
          
          <div className="quick-actions">
            <button className="btn-primary">
              <Upload size={20} />
              Create New Project
            </button>
            <button className="btn-secondary">
              <FileText size={20} />
              Upload File
            </button>
          </div>
        </div>
      </section>

      <section className="stats-grid">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className="stat-icon" style={{ backgroundColor: `${stat.color}20` }}>
              <stat.icon size={32} style={{ color: stat.color }} />
            </div>
            <h3>{stat.label}</h3>
            <p className="stat-value">{stat.value}</p>
          </div>
        ))}
      </section>

      <section className="recent-section">
        <h3>Recent Projects</h3>
        <div className="projects-list">
          <div className="project-item">
            <div className="project-info">
              <h4>Sales Data Q4 2024</h4>
              <p>Updated 2 hours ago</p>
            </div>
            <span className="project-status">Completed</span>
          </div>
          <div className="project-item">
            <div className="project-info">
              <h4>Customer Analytics</h4>
              <p>Updated 1 day ago</p>
            </div>
            <span className="project-status">Completed</span>
          </div>
          <div className="project-item">
            <div className="project-info">
              <h4>Inventory Report</h4>
              <p>Updated 3 days ago</p>
            </div>
            <span className="project-status">Completed</span>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
