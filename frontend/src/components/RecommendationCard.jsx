import React from 'react';

const PRIORITY_STYLES = {
  high:   { accent: '#ef4444', icon: '🔴', label: 'High Priority'   },
  medium: { accent: '#f59e0b', icon: '🟡', label: 'Medium Priority' },
  low:    { accent: '#6366f1', icon: '🔵', label: 'Low Priority'    },
};

const TYPE_ICONS = {
  saving:   '💰',
  budget:   '📊',
  alert:    '⚠️',
  behavior: '🧠',
};

/**
 * RecommendationCard — displays a single AI-generated recommendation.
 * Props:
 *   rec — { type, title, description, impact, confidence, supporting_data, priority }
 *   index — card index (1-based)
 */
const RecommendationCard = ({ rec, index }) => {
  const priority = PRIORITY_STYLES[rec.priority] || PRIORITY_STYLES.low;
  const typeIcon = TYPE_ICONS[rec.type] || '💡';
  const confidence = Math.round((rec.confidence ?? 0.5) * 100);

  return (
    <div className="rec-card" style={{ borderLeft: `3px solid ${priority.accent}` }}>
      <div className="rec-header">
        <div className="rec-meta">
          <span className="rec-type-icon">{typeIcon}</span>
          <span className="rec-priority" style={{ color: priority.accent }}>
            {priority.icon} {priority.label}
          </span>
        </div>
        <div className="rec-confidence">
          <div className="confidence-bar-track">
            <div
              className="confidence-bar-fill"
              style={{ width: `${confidence}%`, background: priority.accent }}
            />
          </div>
          <span className="confidence-text">{confidence}% confidence</span>
        </div>
      </div>

      <h4 className="rec-title">{rec.title ?? 'AI Recommendation'}</h4>
      <p className="rec-description">{rec.description ?? ''}</p>

      {rec.impact && (
        <div className="rec-impact">
          <span className="impact-label">📈 Expected Impact:</span>
          <span className="impact-text"> {rec.impact}</span>
        </div>
      )}

      {rec.supporting_data && Object.keys(rec.supporting_data).length > 0 && (
        <div className="rec-supporting">
          {Object.entries(rec.supporting_data).slice(0, 3).map(([key, val]) => (
            <div key={key} className="supporting-item">
              <span className="supporting-key">{key.replace(/_/g, ' ')}:</span>
              <span className="supporting-val"> {String(val)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecommendationCard;
