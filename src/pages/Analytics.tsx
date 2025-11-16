import React from 'react';
import { BarChart3, LineChart, PieChart, TrendingUp } from 'lucide-react';
import '../styles/Analytics.css';

const Analytics: React.FC = () => {
  const metrics = [
    { label: 'Total Data Points', value: '125.4K', change: '+12.5%', icon: BarChart3 },
    { label: 'Avg Processing Time', value: '2.3s', change: '-8.2%', icon: TrendingUp },
    { label: 'Success Rate', value: '99.8%', change: '+0.3%', icon: PieChart },
    { label: 'Active Projects', value: '12', change: '+2', icon: LineChart },
  ];

  return (
    <div className="analytics">
      <div className="analytics-header">
        <h2>Analytics & Statistics</h2>
        <div className="date-range">
          <input type="date" defaultValue="2024-11-01" />
          <span>to</span>
          <input type="date" defaultValue="2024-11-11" />
        </div>
      </div>

      <div className="metrics-grid">
        {metrics.map((metric) => (
          <div key={metric.label} className="metric-card">
            <div className="metric-header">
              <h3>{metric.label}</h3>
              <metric.icon size={24} className="metric-icon" />
            </div>
            <p className="metric-value">{metric.value}</p>
            <p className="metric-change positive">{metric.change} from last month</p>
          </div>
        ))}
      </div>

      <div className="charts-section">
        <div className="chart-placeholder">
          <h3>Processing Trends</h3>
          <div className="placeholder-chart">
            <LineChart size={100} opacity={0.3} />
            <p>Chart visualization will be displayed here</p>
          </div>
        </div>

        <div className="chart-placeholder">
          <h3>Project Distribution</h3>
          <div className="placeholder-chart">
            <PieChart size={100} opacity={0.3} />
            <p>Chart visualization will be displayed here</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
