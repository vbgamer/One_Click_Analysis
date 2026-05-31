import React from 'react';
import Plot from 'react-plotly.js';

/**
 * PlotlyChart — renders a Plotly.js chart from a JSON figure object returned by the backend.
 * Props:
 *   figure  — { data: [...], layout: {...} }  (standard Plotly JSON)
 *   style   — optional inline styles
 *   config  — optional Plotly config overrides
 */
const PlotlyChart = ({ figure, style, config = {} }) => {
  if (!figure || !figure.data) {
    return (
      <div className="plotly-placeholder">
        <span>No chart data available</span>
      </div>
    );
  }

  const defaultLayout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, system-ui, sans-serif', color: '#e2e8f0' },
    margin: { t: 40, r: 20, b: 40, l: 50 },
    ...figure.layout,
  };

  const defaultConfig = {
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    responsive: true,
    ...config,
  };

  return (
    <Plot
      data={figure.data}
      layout={defaultLayout}
      config={defaultConfig}
      style={{ width: '100%', height: '100%', minHeight: 320, ...style }}
      useResizeHandler
    />
  );
};

export default PlotlyChart;
