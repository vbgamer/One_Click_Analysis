import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../api';
import AnomalyTable from '../components/AnomalyTable';
import RecommendationCard from '../components/RecommendationCard';

/* ── Plotly (full build via factory) ─────────────────────────────────────
   Using createPlotlyComponent so we can inject plotly.js-dist-min directly,
   avoiding the “Plotly not installed” error from the default bundle.          */
let _PlotComponent = null;
const _getPlot = () =>
  _PlotComponent
    ? Promise.resolve(_PlotComponent)
    : Promise.all([
        import('react-plotly.js/factory'),
        import('plotly.js-dist-min'),
      ]).then(([{ default: createPlotlyComponent }, Plotly]) => {
        _PlotComponent = createPlotlyComponent(Plotly.default ?? Plotly);
        return _PlotComponent;
      }).catch(() => null);

const LazyPlot = ({ figure, style }) => {
  const [Plot, setPlot] = useState(null);
  useEffect(() => { _getPlot().then(P => P && setPlot(() => P)); }, []);

  if (!figure?.data?.length)
    return <div className="chart-loading">No chart data available.</div>;
  if (!Plot)
    return <div className="chart-loading">Loading chart…</div>;

  return (
    <Plot
      data={figure.data}
      layout={{
        paper_bgcolor: 'transparent',
        plot_bgcolor:  'transparent',
        font: { family: 'Inter, sans-serif', color: '#cbd5e1', size: 11 },
        margin: { t: 36, r: 16, b: 40, l: 50 },
        ...figure.layout,
      }}
      config={{
        displaylogo: false,
        responsive: true,
        toImageButtonOptions: { format: 'png', scale: 2 },
        modeBarButtonsToRemove: ['pan2d', 'lasso2d'],
      }}
      style={{ width: '100%', minHeight: 300, ...style }}
      useResizeHandler
    />
  );
};

/* ── PDF Download Helper ───────────────────────────────────────────────
   Cycles through every tab, captures each with html2canvas, and stitches     
   all pages into a single downloadable PDF via jsPDF.                        */
const TABS_FOR_PDF = ['overview','forecast','anomalies','recommendations','settlement','behavioral'];

async function downloadIntelligencePDF(setActiveTab, jobId) {
  const { default: html2canvas } = await import('html2canvas');
  const { default: jsPDF }       = await import('jspdf');

  const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  const PW  = pdf.internal.pageSize.getWidth();
  const PH  = pdf.internal.pageSize.getHeight();
  const PADDING = 8;

  for (let i = 0; i < TABS_FOR_PDF.length; i++) {
    const tabId = TABS_FOR_PDF[i];
    setActiveTab(tabId);
    await new Promise(r => setTimeout(r, 900)); // allow charts to render

    const el = document.querySelector('.intelligence-page');
    if (!el) continue;

    const canvas = await html2canvas(el, {
      scale: 1.5,
      useCORS: true,
      backgroundColor: '#0f172a',
      logging: false,
      windowWidth: 1400,
    });

    const imgData = canvas.toDataURL('image/jpeg', 0.85);
    const imgW    = PW - PADDING * 2;
    const imgH    = (canvas.height * imgW) / canvas.width;

    if (i > 0) pdf.addPage();

    // Tab label header
    pdf.setFillColor(15, 23, 42);
    pdf.rect(0, 0, PW, PH, 'F');
    pdf.setTextColor(200, 200, 255);
    pdf.setFontSize(9);
    pdf.text(`AI Expense Intelligence – ${tabId.toUpperCase()} | Job: ${jobId?.slice(0,8)}`, PADDING, 6);
    pdf.text(`Page ${i + 1} / ${TABS_FOR_PDF.length}`, PW - PADDING - 20, 6);

    // Clip image to remaining height
    const availH = PH - 10;
    const drawH  = Math.min(imgH, availH);
    pdf.addImage(imgData, 'JPEG', PADDING, 9, imgW, drawH);
  }

  pdf.save(`AI_Intelligence_${jobId?.slice(0,8)}_${new Date().toISOString().slice(0,10)}.pdf`);
}

/* ── KPI Card ─────────────────────────────────────────────────────────────── */
const KpiCard = ({ icon, label, value, sub, accent = '#6366f1' }) => (
  <div className="intel-kpi-card" style={{ borderTop: `3px solid ${accent}` }}>
    <span className="intel-kpi-icon">{icon}</span>
    <div className="intel-kpi-body">
      <div className="intel-kpi-value">{value ?? '—'}</div>
      <div className="intel-kpi-label">{label}</div>
      {sub && <div className="intel-kpi-sub">{sub}</div>}
    </div>
  </div>
);

/* ── Tab definitions ──────────────────────────────────────────────────────── */
const TABS = [
  { id: 'overview',         label: '📊 Overview'        },
  { id: 'ranked',           label: '🏆 Top 5 Findings'  },
  { id: 'kpis',             label: '📐 KPIs'             },
  { id: 'hypotheses',       label: '🔬 Hypotheses'       },
  { id: 'root_cause',       label: '🔍 Root Cause'       },
  { id: 'forecast',         label: '📈 Forecast'        },
  { id: 'anomalies',        label: '🚨 Anomalies'       },
  { id: 'recommendations',  label: '💡 Recommendations' },
  { id: 'settlement',       label: '💸 Settlement'      },
  { id: 'behavioral',       label: '🧠 Behavioral'      },
  { id: 'audit',            label: '🛡️ Audit'           },
  { id: 'critique',         label: '⚠️ Self-Critique'   },
  { id: 'lineage',          label: '🔗 Lineage'         },
];

const ANALYST_MODES = [
  { id: 'executive',      label: 'Executive',      icon: '👔' },
  { id: 'manager',        label: 'Manager',         icon: '📋' },
  { id: 'analyst',        label: 'Analyst',         icon: '🔬' },
  { id: 'auditor',        label: 'Auditor',         icon: '🛡️' },
  { id: 'data_scientist', label: 'Data Scientist',  icon: '🤖' },
];


/* ══════════════════════════════════════════════════════════════════════════ */
const Intelligence = () => {
  const { jobId } = useParams();
  const navigate  = useNavigate();

  const [activeTab, setActiveTab]   = useState('overview');
  const [analystMode, setAnalystMode] = useState('analyst');
  const [results,   setResults]     = useState(null);
  const [aiStatus,  setAiStatus]    = useState(null);   // { status, ... }
  const [loading,   setLoading]     = useState(true);
  const [running,   setRunning]     = useState(false);
  const [error,     setError]       = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);


  /* ── Fetch AI status ── */
  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get(`/analyze/${jobId}/status`);
      setAiStatus(data);
      return data.status;
    } catch {
      return 'error';
    }
  }, [jobId]);

  /* ── Fetch full results ── */
  const fetchResults = useCallback(async () => {
    try {
      const { data } = await api.get(`/analyze/${jobId}/results`);
      setResults(data);
      setError(null);
    } catch (e) {
      setError(e.response?.data?.detail || 'Results not available yet.');
    }
  }, [jobId]);

  /* ── Initial load + polling ── */
  useEffect(() => {
    let interval;
    const init = async () => {
      setLoading(true);
      const st = await fetchStatus();
      if (st === 'done') {
        await fetchResults();
      } else if (st === 'running' || st === 'pending') {
        interval = setInterval(async () => {
          const s = await fetchStatus();
          if (s === 'done') {
            clearInterval(interval);
            await fetchResults();
          } else if (s === 'failed' || s === 'error') {
            clearInterval(interval);
          }
        }, 3000);
      }
      setLoading(false);
    };
    init();
    return () => clearInterval(interval);
  }, [jobId, fetchStatus, fetchResults]);

  /* ── Trigger AI analysis ── */
  const triggerAnalysis = async () => {
    setRunning(true);
    try {
      await api.post(`/analyze/${jobId}/run`);
      setAiStatus({ status: 'pending' });
      const interval = setInterval(async () => {
        const s = await fetchStatus();
        if (s === 'done') {
          clearInterval(interval);
          await fetchResults();
          setRunning(false);
        } else if (s === 'failed') {
          clearInterval(interval);
          setRunning(false);
          setError('AI analysis failed. Check backend logs.');
        }
      }, 3000);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start AI analysis.');
      setRunning(false);
    }
  };

  /* ── Helpers ── */
  const fmt = (n, decimals = 0) =>
    n == null ? '—' : Number(n).toLocaleString('en-IN', { maximumFractionDigits: decimals });

  const fmtPct = (n) => n == null ? '—' : `${Number(n).toFixed(1)}%`;

  /* ── Not-started state ── */
  const notStarted = !loading && (!aiStatus || aiStatus.status === 'not_started');
  const isPending  = aiStatus?.status === 'pending' || aiStatus?.status === 'running';

  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  /* RENDER                                                                    */
  /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
  return (
    <div className="intelligence-page">

      {/* ── Header ── */}
      <div className="intel-header">
        <div className="intel-header-left">
          <button className="btn-back" onClick={() => navigate('/dashboard')}>← Back</button>
          <div>
            <h1 className="intel-title">🧠 AI Expense Intelligence</h1>
            <p className="intel-subtitle">Job <code>{jobId?.slice(0, 8)}…</code></p>
          </div>
        </div>
        <div className="intel-header-right">
          {/* Mode Switcher */}
          <div className="mode-switcher">
            {ANALYST_MODES.map(m => (
              <button
                key={m.id}
                className={`mode-btn${analystMode === m.id ? ' active' : ''}`}
                onClick={() => setAnalystMode(m.id)}
                title={m.label}
              >
                {m.icon} {m.label}
              </button>
            ))}
          </div>
          <Link to={`/chat/${jobId}`} className="btn btn-outline">💬 Ask AI</Link>

          {/* ── Download PDF button (only when analysis done) ── */}
          {results && (
            <button
              className="btn btn-pdf"
              disabled={pdfLoading}
              onClick={async () => {
                setPdfLoading(true);
                try {
                  await downloadIntelligencePDF(setActiveTab, jobId);
                } finally {
                  setPdfLoading(false);
                }
              }}
            >
              {pdfLoading ? '⏳ Generating PDF…' : '📥 Download PDF'}
            </button>
          )}

          {!loading && (notStarted || aiStatus?.status === 'failed') && (
            <button className="btn btn-primary" onClick={triggerAnalysis} disabled={running}>
              {running ? '⏳ Analyzing…' : '🚀 Run AI Analysis'}
            </button>
          )}
          {isPending && (
            <span className="status-pill running">⏳ Analysis Running…</span>
          )}
          {aiStatus?.status === 'done' && (
            <span className="status-pill done">✅ Analysis Complete</span>
          )}
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="intel-loading">
          <div className="spinner" />
          <p>Loading AI analysis…</p>
        </div>
      )}

      {/* ── Not started prompt ── */}
      {!loading && notStarted && !running && (
        <div className="intel-prompt-card">
          <div className="intel-prompt-icon">🤖</div>
          <h2>AI Analysis Not Yet Run</h2>
          <p>
            Click <strong>Run AI Analysis</strong> to start forecasting, anomaly detection,
            settlement optimization, and personalized recommendations.
          </p>
          <button className="btn btn-primary btn-lg" onClick={triggerAnalysis} disabled={running}>
            🚀 Start AI Analysis
          </button>
        </div>
      )}

      {/* ── Pending / running spinner ── */}
      {!loading && isPending && (
        <div className="intel-pending">
          <div className="ai-spinner">
            {['🔍', '📊', '🧠', '🤖'].map((e, i) => (
              <span key={i} className="spin-emoji" style={{ animationDelay: `${i * 0.4}s` }}>{e}</span>
            ))}
          </div>
          <h2>AI is analyzing your data…</h2>
          <p>Forecasting • Anomaly Detection • Recommendations • Settlement Optimization</p>
          <div className="progress-bar-track">
            <div className="progress-bar-fill progress-animated" />
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {error && !isPending && (
        <div className="intel-error">⚠️ {error}</div>
      )}

      {/* ── Main Content (tabs) ── */}
      {results && !isPending && (
        <>
          {/* Tab bar */}
          <div className="intel-tabs">
            {TABS.map(t => (
              <button
                key={t.id}
                className={`intel-tab${activeTab === t.id ? ' active' : ''}`}
                onClick={() => setActiveTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* ── OVERVIEW TAB ── */}
          {activeTab === 'overview' && (
            <div className="tab-content">
              <div className="kpi-grid">
                <KpiCard icon="📁" label="Total Transactions"    value={fmt(results.summary?.rows)}            accent="#6366f1" />
                <KpiCard icon="💰" label="Total Spent"           value={`₹${fmt(results.summary?.total_amount)}`} accent="#8b5cf6" />
                <KpiCard icon="🎯" label="Data Quality Score"    value={`${fmt(typeof results.data_quality_score === 'object' ? results.data_quality_score?.overall ?? results.data_quality_score?.score : results.data_quality_score)}%`} accent="#06b6d4" />
                <KpiCard icon="🔮" label="AI Confidence"         value={`${fmt(typeof results.confidence_score === 'object' ? results.confidence_score?.overall : results.confidence_score)}%`} accent="#10b981" />
                <KpiCard icon="🚨" label="Anomalies Detected"    value={results.anomalies?.anomaly_count ?? 0}   accent="#ef4444" />
                <KpiCard icon="💡" label="Recommendations"       value={results.recommendations?.length ?? 0}    accent="#f59e0b" />
                <KpiCard icon="📊" label="Categories"            value={Object.keys(results.categories?.breakdown ?? results.categories ?? {}).length} accent="#ec4899" />
                <KpiCard icon="💸" label="Settlement Transactions" value={results.settlement?.optimal_transactions?.length ?? 0} accent="#14b8a6" />
              </div>

              {/* Schema Card */}
              {results.schema && (
                <div className="intel-section">
                  <h3 className="section-title">🗂️ Auto-Detected Schema</h3>
                  <div className="schema-grid">
                    {Object.entries(results.schema).filter(([, v]) => v).map(([k, v]) => (
                      <div key={k} className="schema-chip">
                        <span className="schema-key">{k.replace(/_col$/, '').toUpperCase()}</span>
                        <span className="schema-val">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Entity changes — nested: { col_name: { old: new } } */}
              {results.entity_changes && Object.keys(results.entity_changes).length > 0 && (() => {
                // Flatten all col->corrections into a single list
                const rows = [];
                Object.entries(results.entity_changes).forEach(([col, corrections]) => {
                  if (corrections && typeof corrections === 'object') {
                    Object.entries(corrections).slice(0, 10).forEach(([oldVal, newVal]) => {
                      rows.push({ col, oldVal, newVal: typeof newVal === 'string' ? newVal : String(newVal) });
                    });
                  }
                });
                if (!rows.length) return null;
                return (
                  <div className="intel-section">
                    <h3 className="section-title">🔤 Auto-Corrected Entity Names</h3>
                    <div className="entity-changes">
                      {rows.map((r, i) => (
                        <div key={i} className="entity-row">
                          <span className="schema-key" style={{ marginRight: 8 }}>{r.col}</span>
                          <span className="entity-old">"{r.oldVal}"</span>
                          <span className="entity-arrow">→</span>
                          <span className="entity-new">"{r.newVal}"</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Overview chart */}
              {results.charts?.spending_over_time && (
                <div className="intel-section">
                  <h3 className="section-title">📈 Spending Over Time</h3>
                  <div className="chart-box">
                    <LazyPlot figure={results.charts.spending_over_time} />
                  </div>
                </div>
              )}
            </div>
          )}

      {/* ── RANKED INSIGHTS TAB ── */}
      {activeTab === 'ranked' && results && !isPending && (
        <div className="tab-content">
          <div className="intel-section">
            <h3 className="section-title">🏆 Top 5 Verified Findings</h3>
            <p className="section-desc">Ranked by business impact × confidence × actionability. Every finding is evidence-backed.</p>
            {!results.ranked_insights?.top_insights?.length ? (
              <div className="intel-unavail">No ranked insights yet — run analysis first.</div>
            ) : (
              <div className="ranked-list">
                {results.ranked_insights.top_insights.map((insight, i) => (
                  <div key={i} className={`ranked-card impact-${insight.business_impact}`}>
                    <div className="ranked-header">
                      <div className="ranked-position">#{insight.rank}</div>
                      <div className="ranked-impact-badge">{insight.business_impact?.toUpperCase()} IMPACT</div>
                      <div className={`audit-badge ${insight.audit_status?.toLowerCase()}`}>
                        {insight.audit_status === 'PASSED' ? '✅' : insight.audit_status === 'FAILED' ? '❌' : '⚠️'} {insight.audit_status}
                      </div>
                      <div className="ranked-score">Score: {insight.score?.toFixed(1)}</div>
                    </div>
                    <div className="ranked-title">{insight.title}</div>
                    <div className="ranked-summary">{insight.summary}</div>
                    <div className="ranked-footer">
                      <span className="ranked-cat">{insight.category}</span>
                      <span className="ranked-conf">🎯 {insight.confidence}% confidence</span>
                      <span className="ranked-action">→ {insight.action}</span>
                    </div>
                    {insight.evidence_summary && (
                      <div className="evidence-mini">
                        📎 <em>{insight.evidence_summary}</em>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            {results.ranked_insights?.total_considered > 0 && (
              <p className="section-meta">Ranked from {results.ranked_insights.total_considered} total findings. Method: {results.ranked_insights.ranking_method}</p>
            )}
          </div>
        </div>
      )}

      {/* ── KPIs TAB ── */}
      {activeTab === 'kpis' && results && !isPending && (
        <div className="tab-content">
          {results.kpis?.available ? (
            <>
              <div className="intel-section">
                <div className="domain-banner">
                  <span className="domain-label">🔍 Auto-Detected Domain</span>
                  <span className="domain-name">{results.kpis.domain?.toUpperCase()}</span>
                  <span className="domain-conf">{results.kpis.domain_confidence?.toFixed(0)}% confidence</span>
                </div>
              </div>
              <div className="intel-section">
                <h3 className="section-title">📐 Discovered KPIs ({results.kpis.total_kpis})</h3>
                <div className="kpi-discovery-grid">
                  {results.kpis.kpis?.map((kpi, i) => (
                    <div key={i} className={`kpi-discovery-card status-${kpi.status}`}>
                      <div className="kdi-header">
                        <span className="kdi-name">{kpi.name}</span>
                        <span className={`kdi-status-dot ${kpi.status}`} title={kpi.status}></span>
                      </div>
                      <div className="kdi-value">{kpi.value != null ? `${kpi.value} ${kpi.unit || ''}` : '—'}</div>
                      <div className="kdi-interp">{kpi.interpretation}</div>
                      <div className="kdi-formula" title={kpi.formula}>f: {kpi.formula}</div>
                      <div className="kdi-footer">
                        <span>Cols: {kpi.source_columns?.join(', ')}</span>
                        <span>🎯 {kpi.confidence?.toFixed(0)}%</span>
                      </div>
                      {kpi.benchmark && <div className="kdi-benchmark">Benchmark: {kpi.benchmark}</div>}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="intel-unavail">KPI discovery not yet available.</div>
          )}
        </div>
      )}

      {/* ── HYPOTHESES TAB ── */}
      {activeTab === 'hypotheses' && results && !isPending && (
        <div className="tab-content">
          {results.hypotheses?.available ? (
            <>
              <div className="kpi-grid kpi-grid-3">
                <KpiCard icon="✅" label="Verified"     value={results.hypotheses.verified}     accent="#10b981" />
                <KpiCard icon="❌" label="Rejected"     value={results.hypotheses.rejected}     accent="#ef4444" />
                <KpiCard icon="❓" label="Inconclusive" value={results.hypotheses.inconclusive} accent="#f59e0b" />
              </div>
              <div className="intel-section">
                <h3 className="section-title">🔬 Hypothesis Test Results</h3>
                <div className="hyp-list">
                  {results.hypotheses.hypotheses?.filter(h => h.status !== 'skipped').map((h, i) => (
                    <div key={i} className={`hyp-card status-${h.status}`}>
                      <div className="hyp-header">
                        <span className={`hyp-verdict ${h.status}`}>
                          {h.status === 'verified' ? '✅ VERIFIED' : h.status === 'rejected' ? '❌ REJECTED' : '❓ INCONCLUSIVE'}
                        </span>
                        <span className="hyp-conf">🎯 {h.confidence?.toFixed(1)}%</span>
                      </div>
                      <div className="hyp-statement">{h.statement}</div>
                      <div className="hyp-finding">{h.key_finding}</div>
                      {h.business_implication && (
                        <div className="hyp-implication">💼 {h.business_implication}</div>
                      )}
                      {h.evidence && (
                        <div className="hyp-evidence">
                          <strong>Evidence:</strong> {h.evidence.calculation} | Cols: {h.evidence.source_columns?.join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="intel-unavail">Hypothesis testing not yet available.</div>
          )}
        </div>
      )}

      {/* ── ROOT CAUSE TAB ── */}
      {activeTab === 'root_cause' && results && !isPending && (
        <div className="tab-content">
          {results.root_cause?.available ? (
            <>
              {results.root_cause.primary_finding && (
                <div className="intel-section">
                  <div className="primary-finding-card">
                    <div className="pf-icon">🔍</div>
                    <div className="pf-text">{results.root_cause.primary_finding}</div>
                  </div>
                </div>
              )}
              {results.root_cause.analyses?.map((analysis, ai) => (
                <div key={ai} className="intel-section">
                  <h3 className="section-title">{analysis.title || 'Analysis'}</h3>
                  {analysis.type === 'mom_decomposition' && (
                    <>
                      <div className="kpi-grid kpi-grid-3">
                        <KpiCard icon="📅" label="Previous Period" value={`₹${(analysis.previous_value || 0).toLocaleString('en-IN')}`} accent="#6366f1" />
                        <KpiCard icon="📅" label="Current Period"  value={`₹${(analysis.current_value || 0).toLocaleString('en-IN')}`}  accent="#8b5cf6" />
                        <KpiCard icon={analysis.change_abs >= 0 ? '📈' : '📉'} label="Change" value={`${analysis.change_abs >= 0 ? '+' : ''}${analysis.change_pct?.toFixed(1)}%`} accent={analysis.change_abs >= 0 ? '#ef4444' : '#10b981'} />
                      </div>
                      {analysis.root_causes?.length > 0 && (
                        <div className="waterfall-list">
                          <h4 className="waterfall-title">📊 Dimension Contribution (Waterfall)</h4>
                          {analysis.root_causes.map((rc, ri) => (
                            <div key={ri} className="waterfall-row">
                              <span className="wf-factor">{rc.factor}</span>
                              <div className="wf-bar-track">
                                <div
                                  className={`wf-bar ${rc.contribution_abs >= 0 ? 'wf-pos' : 'wf-neg'}`}
                                  style={{ width: `${Math.min(Math.abs(rc.contribution_pct), 100)}%` }}
                                />
                              </div>
                              <span className="wf-pct">{rc.contribution_pct >= 0 ? '+' : ''}{rc.contribution_pct?.toFixed(1)}%</span>
                              <span className="wf-conf">🎯{rc.confidence}%</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                  {analysis.type === 'spend_drivers' && analysis.drivers?.map((d, di) => (
                    <div key={di} className="driver-card">
                      <div className="driver-type">{d.driver_type?.replace(/_/g, ' ').toUpperCase()}</div>
                      <div className="driver-desc">{d.description}</div>
                      <div className="driver-impact">Impact: {d.impact_pct?.toFixed(1)}% of spend | Confidence: {d.confidence}%</div>
                    </div>
                  ))}
                </div>
              ))}
            </>
          ) : (
            <div className="intel-unavail">
              Root cause analysis requires at least 2 months of date+amount data.
              {results.root_cause?.reason && <p>{results.root_cause.reason}</p>}
            </div>
          )}
        </div>
      )}

          {/* ── FORECAST TAB ── */}
          {activeTab === 'forecast' && (
            <div className="tab-content">
              {results.forecast?.available === false ? (
                <div className="intel-unavail">
                  📅 Forecasting requires a date column in your dataset.
                  <p>{results.forecast?.reason}</p>
                </div>
              ) : (
                <>
                  <div className="kpi-grid kpi-grid-3">
                    <KpiCard icon="📅" label="Monthly Average"        value={`₹${fmt(results.forecast?.monthly_avg)}`}             accent="#6366f1" />
                    <KpiCard icon="🔮" label="Next Month Prediction"  value={`₹${fmt(results.forecast?.next_month_prediction)}`}   accent="#8b5cf6" />
                    <KpiCard icon="📉" label="Trend Direction"        value={results.forecast?.trend_direction ?? '—'}             accent={results.forecast?.trend_direction === 'increasing' ? '#ef4444' : '#10b981'} />
                    <KpiCard icon="🔥" label="Daily Burn Rate"        value={`₹${fmt(results.burn_rate?.daily_rate, 0)}/day`}      accent="#f59e0b" />
                    <KpiCard icon="📆" label="Peak Month"             value={results.burn_rate?.peak_month ?? '—'}                 accent="#ec4899" />
                    <KpiCard icon="💰" label="Peak Spending"          value={`₹${fmt(results.burn_rate?.peak_amount)}`}            accent="#14b8a6" />
                  </div>

                  {results.charts?.forecast && (
                    <div className="intel-section">
                      <h3 className="section-title">📈 Expense Forecast (Next 30 Days)</h3>
                      <div className="chart-box chart-box-tall">
                        <LazyPlot figure={results.charts.forecast} />
                      </div>
                    </div>
                  )}

                  {results.charts?.spending_over_time && (
                    <div className="intel-section">
                      <h3 className="section-title">📊 Historical Trend</h3>
                      <div className="chart-box">
                        <LazyPlot figure={results.charts.spending_over_time} />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── ANOMALIES TAB ── */}
          {activeTab === 'anomalies' && (
            <div className="tab-content">
              <div className="kpi-grid kpi-grid-3">
                <KpiCard icon="🚨" label="Total Anomalies"        value={results.anomalies?.anomaly_count ?? 0}                               accent="#ef4444" />
                <KpiCard icon="📊" label="Anomaly Rate"           value={fmtPct(results.anomalies?.anomaly_rate_pct)}                         accent="#f59e0b" />
                <KpiCard icon="💸" label="Suspicious Amount"      value={`₹${fmt(results.anomalies?.total_anomalous_amount)}`}                accent="#ec4899" />
              </div>

              {results.charts?.anomaly_heatmap && (
                <div className="intel-section">
                  <h3 className="section-title">🗓️ Anomaly Calendar</h3>
                  <div className="chart-box">
                    <LazyPlot figure={results.charts.anomaly_heatmap} />
                  </div>
                </div>
              )}

              <div className="intel-section">
                <h3 className="section-title">🚨 Flagged Transactions</h3>
                <AnomalyTable anomalies={results.anomalies?.anomalies ?? []} />
              </div>

              {results.behavioral_anomalies?.payer_anomalies?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">🧠 Behavioral Anomalies</h3>
                  <div className="behavioral-list">
                    {results.behavioral_anomalies.payer_anomalies.map((a, i) => (
                      <div key={i} className="behavioral-item">
                        <span className="behavioral-icon">👤</span>
                        <span>{a.description ?? JSON.stringify(a)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── RECOMMENDATIONS TAB ── */}
          {activeTab === 'recommendations' && (
            <div className="tab-content">
              {results.optimization_score && (
                <div className="intel-section">
                  <div className="opt-score-card">
                    <div className="opt-score-ring">
                      <svg viewBox="0 0 100 100" width="120" height="120">
                        <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(99,102,241,0.15)" strokeWidth="8" />
                        <circle
                          cx="50" cy="50" r="45" fill="none" stroke="#6366f1" strokeWidth="8"
                          strokeDasharray={`${(results.optimization_score?.score ?? results.optimization_score?.overall ?? 0) * 2.827} 282.7`}
                          strokeLinecap="round" transform="rotate(-90 50 50)"
                        />
                        <text x="50" y="54" textAnchor="middle" fill="#e2e8f0" fontSize="18" fontWeight="bold">
                          {Math.round(results.optimization_score?.score ?? results.optimization_score?.overall ?? 0)}
                        </text>
                      </svg>
                    </div>
                    <div className="opt-score-info">
                      <h3>Financial Optimization Score</h3>
                      <div className="opt-score-breakdown">
                        {[
                          ['Budget Adherence', results.optimization_score?.budget_adherence],
                          ['Spending Consistency', results.optimization_score?.spending_consistency],
                          ['Category Balance', results.optimization_score?.category_balance],
                          ['Anomaly Rate', results.optimization_score?.anomaly_rate_score],
                        ].filter(([, v]) => v != null).map(([k, v]) => (
                          <div key={k} className="opt-sub">
                            <span>{k}</span>
                            <div className="sub-bar-track">
                              <div className="sub-bar-fill" style={{ width: `${v}%` }} />
                            </div>
                            <span>{Math.round(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="intel-section">
                <h3 className="section-title">💡 AI Recommendations</h3>
                {!results.recommendations?.length ? (
                  <p className="intel-unavail">No recommendations generated.</p>
                ) : (
                  <div className="rec-grid">
                    {results.recommendations.map((rec, i) => (
                      <RecommendationCard key={i} rec={rec} index={i + 1} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── SETTLEMENT TAB ── */}
          {activeTab === 'settlement' && (
            <div className="tab-content">
              {!results.settlement || results.settlement.available === false ? (
                <div className="intel-unavail">
                  💸 Settlement optimization requires a payer column in your dataset.
                </div>
              ) : (
                <>
                  <div className="kpi-grid kpi-grid-3">
                    <KpiCard icon="💸" label="Total to Settle"   value={`₹${fmt(results.settlement?.total_to_settle)}`}                           accent="#6366f1" />
                    <KpiCard icon="✅" label="Optimal Transactions" value={results.settlement?.optimal_transactions?.length ?? 0}                  accent="#10b981" />
                    <KpiCard icon="📉" label="Transactions Saved" value={results.settlement?.transaction_count_reduction ?? 0}                    accent="#f59e0b" />
                  </div>

                  {/* Balances */}
                  <div className="intel-section">
                    <h3 className="section-title">⚖️ Net Balances</h3>
                    <div className="balance-grid">
                      {results.settlement?.balances && Object.entries(results.settlement.balances).map(([person, amount]) => (
                        <div key={person} className={`balance-card ${amount >= 0 ? 'owed' : 'owes'}`}>
                          <div className="balance-person">{person}</div>
                          <div className="balance-amount" style={{ color: amount >= 0 ? '#10b981' : '#ef4444' }}>
                            {amount >= 0 ? '+' : ''}₹{fmt(Math.abs(amount))}
                          </div>
                          <div className="balance-status">{amount >= 0 ? '← is owed' : '→ owes'}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Optimal payment plan */}
                  <div className="intel-section">
                    <h3 className="section-title">🎯 Optimal Payment Plan</h3>
                    <div className="payment-plan">
                      {results.settlement?.optimal_transactions?.map((tx, i) => (
                        <div key={i} className="payment-row">
                          <span className="payment-from">{tx.payer}</span>
                          <span className="payment-arrow">→ pays ₹{fmt(tx.amount)} →</span>
                          <span className="payment-to">{tx.payee}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Settlement chart */}
                  {results.charts?.settlement_flow && (
                    <div className="intel-section">
                      <h3 className="section-title">🌊 Payment Flow</h3>
                      <div className="chart-box chart-box-tall">
                        <LazyPlot figure={results.charts.settlement_flow} />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* ── BEHAVIORAL TAB ── */}
          {activeTab === 'behavioral' && (
            <div className="tab-content">
              {results.charts?.payer_comparison && (
                <div className="intel-section">
                  <h3 className="section-title">👥 Payer Comparison</h3>
                  <div className="chart-box">
                    <LazyPlot figure={results.charts.payer_comparison} />
                  </div>
                </div>
              )}

              {results.charts?.category_breakdown && (
                <div className="intel-section">
                  <h3 className="section-title">🗂️ Category Breakdown</h3>
                  <div className="chart-box">
                    <LazyPlot figure={results.charts.category_breakdown} />
                  </div>
                </div>
              )}

              {results.charts?.spending_heatmap && (
                <div className="intel-section">
                  <h3 className="section-title">🔥 Spending Heatmap (Day × Time)</h3>
                  <div className="chart-box chart-box-tall">
                    <LazyPlot figure={results.charts.spending_heatmap} />
                  </div>
                </div>
              )}

              {results.charts?.top_merchants && (
                <div className="intel-section">
                  <h3 className="section-title">🏪 Top Merchants</h3>
                  <div className="chart-box">
                    <LazyPlot figure={results.charts.top_merchants} />
                  </div>
                </div>
              )}

              {/* Category intelligence — backend key is category_summary */}
              {(() => {
                const catData = results.categories?.breakdown ?? results.categories?.category_summary;
                if (!catData || typeof catData !== 'object' || !Object.keys(catData).length) return null;
                const entries = Object.entries(catData)
                  .map(([cat, data]) => ({
                    cat,
                    count: typeof data === 'object' ? (data.count ?? data.transaction_count ?? '—') : '—',
                    total: typeof data === 'object' ? (data.total_amount ?? data.total ?? 0) : (typeof data === 'number' ? data : 0),
                    pct: typeof data === 'object' ? (data.percentage ?? data.pct ?? 0) : 0,
                  }))
                  .sort((a, b) => b.total - a.total);
                return (
                  <div className="intel-section">
                    <h3 className="section-title">📊 Category Intelligence</h3>
                    <div className="cat-table">
                      <table>
                        <thead>
                          <tr><th>Category</th><th>Transactions</th><th>Total Spent</th><th>Share</th></tr>
                        </thead>
                        <tbody>
                          {entries.map(({ cat, count, total, pct }) => (
                            <tr key={cat}>
                              <td>{cat}</td>
                              <td>{count}</td>
                              <td>₹{fmt(total)}</td>
                              <td>
                                <div className="cat-bar-track">
                                  <div className="cat-bar-fill" style={{ width: `${pct}%` }} />
                                </div>
                                <span>{fmtPct(pct)}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

      {/* ── AUDIT TAB ── */}
      {activeTab === 'audit' && results && !isPending && (
        <div className="tab-content">
          {results.audit_report ? (
            <>
              <div className="kpi-grid kpi-grid-3">
                <KpiCard icon={results.audit_report.overall_status === 'PASSED' ? '✅' : results.audit_report.overall_status === 'FAILED' ? '❌' : '⚠️'}
                  label="Audit Status" value={results.audit_report.overall_status} accent={results.audit_report.overall_status === 'PASSED' ? '#10b981' : '#ef4444'} />
                <KpiCard icon="📊" label="Audit Score" value={`${results.audit_report.score?.toFixed(1)}/100`} accent="#6366f1" />
                <KpiCard icon="✔️" label="Checks Passed" value={`${results.audit_report.passed_count}/${results.audit_report.total_checks}`} accent="#10b981" />
              </div>
              <div className="intel-section">
                <p className="audit-summary">{results.audit_report.audit_summary}</p>
              </div>
              {results.audit_report.failed?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">❌ Failed Checks</h3>
                  <div className="audit-list">
                    {results.audit_report.failed.map((c, i) => (
                      <div key={i} className="audit-item audit-failed">
                        <span className="audit-check">{c.check}</span>
                        <span className="audit-detail">{c.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {results.audit_report.warnings?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">⚠️ Warnings</h3>
                  <div className="audit-list">
                    {results.audit_report.warnings.map((c, i) => (
                      <div key={i} className="audit-item audit-warning">
                        <span className="audit-check">{c.check}</span>
                        <span className="audit-detail">{c.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {results.audit_report.passed?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">✅ Passed Checks</h3>
                  <div className="audit-list">
                    {results.audit_report.passed.slice(0, 10).map((c, i) => (
                      <div key={i} className="audit-item audit-passed">
                        <span className="audit-check">{c.check}</span>
                        <span className="audit-detail">{c.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="intel-unavail">Audit report not yet available.</div>
          )}
        </div>
      )}

      {/* ── SELF-CRITIQUE TAB ── */}
      {activeTab === 'critique' && results && !isPending && (
        <div className="tab-content">
          {results.self_critique?.available ? (
            <>
              <div className="kpi-grid kpi-grid-3">
                <KpiCard icon="🛡️" label="Trust Score" value={`${results.self_critique.trust_score}/100`}
                  accent={results.self_critique.trust_score >= 80 ? '#10b981' : results.self_critique.trust_score >= 55 ? '#f59e0b' : '#ef4444'} />
                <KpiCard icon="📊" label="Reliability" value={results.self_critique.overall_reliability?.toUpperCase()} accent="#6366f1" />
                <KpiCard icon="⚠️" label="Warnings" value={results.self_critique.total_warnings} accent="#f59e0b" />
              </div>
              <div className="intel-section">
                <p className="critique-summary">{results.self_critique.critique_summary}</p>
              </div>
              {results.self_critique.strengths?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">💪 Analysis Strengths</h3>
                  <div className="critique-list">
                    {results.self_critique.strengths.map((s, i) => (
                      <div key={i} className="critique-item critique-strength">✅ {s.message}</div>
                    ))}
                  </div>
                </div>
              )}
              {results.self_critique.warnings?.length > 0 && (
                <div className="intel-section">
                  <h3 className="section-title">⚠️ Limitations & Warnings</h3>
                  <div className="critique-list">
                    {results.self_critique.warnings.map((w, i) => (
                      <div key={i} className={`critique-item critique-${w.severity?.toLowerCase()}`}>
                        <div className="critique-sev">{w.severity}</div>
                        <div className="critique-msg">{w.message}</div>
                        <div className="critique-rec">→ {w.recommendation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="intel-unavail">Self-critique not yet available.</div>
          )}
        </div>
      )}

      {/* ── LINEAGE TAB ── */}
      {activeTab === 'lineage' && results && !isPending && (
        <div className="tab-content">
          {results.lineage?.available ? (
            <>
              <div className="kpi-grid kpi-grid-3">
                <KpiCard icon="🔗" label="Tracked Outputs" value={results.lineage.total_tracked} accent="#6366f1" />
                <KpiCard icon="📋" label="Source Columns" value={results.lineage.total_source_columns} accent="#8b5cf6" />
                <KpiCard icon="📝" label="Source Rows" value={results.lineage.total_rows?.toLocaleString('en-IN')} accent="#06b6d4" />
              </div>
              <div className="intel-section">
                <h3 className="section-title">🔗 Data Lineage: CSV → KPI → Insight</h3>
                <div className="lineage-list">
                  {results.lineage.lineage_entries?.map((entry, i) => (
                    <div key={i} className="lineage-card">
                      <div className="lineage-header">
                        <span className="lineage-name">{entry.output_name}</span>
                        <span className="lineage-type">{entry.output_type}</span>
                      </div>
                      <div className="lineage-trail">{entry.text_trail}</div>
                      <div className="lineage-cols">Source: {entry.source_columns?.join(', ')}</div>
                      {entry.transformations?.length > 0 && (
                        <div className="lineage-steps">
                          {entry.transformations.map((t, ti) => (
                            <div key={ti} className="lineage-step">
                              <span className="step-num">{t.step}</span>
                              <span className="step-desc">{t.description}</span>
                              <span className="step-out">→ {t.output}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {entry.reproducible_code && (
                        <code className="lineage-code">{entry.reproducible_code}</code>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="intel-unavail">Data lineage tracking not yet available.</div>
          )}
        </div>
      )}
        </>
      )}

      {/* ── Debug: show error if nothing renders ── */}
      {!loading && !isPending && !results && !notStarted && (
        <div className="intel-error">
          Could not load results. Check backend is running or try refreshing.
          {error && <span> {error}</span>}
        </div>
      )}
    </div>
  );
};

export default Intelligence;
