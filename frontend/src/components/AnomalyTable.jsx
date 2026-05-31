import React from 'react';

const SEVERITY_COLORS = {
  high:   { bg: 'rgba(239,68,68,0.12)',  border: '#ef4444', badge: '#ef4444', text: 'High'   },
  medium: { bg: 'rgba(245,158,11,0.12)', border: '#f59e0b', badge: '#f59e0b', text: 'Medium' },
  low:    { bg: 'rgba(99,102,241,0.12)', border: '#6366f1', badge: '#6366f1', text: 'Low'    },
};

/**
 * AnomalyTable — displays flagged transactions with anomaly scores.
 * Props:
 *   anomalies — list of { row_index, amount, reason, anomaly_score, severity }
 *   currency  — currency symbol (default '₹')
 */
const AnomalyTable = ({ anomalies = [], currency = '₹' }) => {
  if (!anomalies.length) {
    return (
      <div className="anomaly-empty">
        <span>✅ No anomalies detected in this dataset.</span>
      </div>
    );
  }

  const sorted = [...anomalies].sort((a, b) => (b.anomaly_score ?? 0) - (a.anomaly_score ?? 0));

  return (
    <div className="anomaly-table-wrapper">
      <div className="anomaly-summary">
        <span className="anomaly-count">{anomalies.length} anomalies detected</span>
        <span className="anomaly-hint">Sorted by severity</span>
      </div>
      <div className="anomaly-table-scroll">
        <table className="anomaly-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Severity</th>
              <th>Amount</th>
              <th>Anomaly Score</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => {
              const sev = SEVERITY_COLORS[row.severity] || SEVERITY_COLORS.low;
              return (
                <tr key={i} style={{ background: sev.bg }}>
                  <td className="row-idx">{row.row_index ?? i + 1}</td>
                  <td>
                    <span className="severity-badge" style={{ background: sev.badge }}>
                      {sev.text}
                    </span>
                  </td>
                  <td className="amount-cell">
                    {currency}{typeof row.amount === 'number' ? row.amount.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : row.amount ?? '—'}
                  </td>
                  <td>
                    <div className="score-bar-wrapper">
                      <div className="score-bar" style={{ width: `${Math.min(100, (row.anomaly_score ?? 0) * 100)}%`, background: sev.badge }} />
                      <span className="score-text">{((row.anomaly_score ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="reason-cell">{row.reason ?? '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AnomalyTable;
