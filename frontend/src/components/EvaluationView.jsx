import { useState, useEffect } from 'react';
import { fetchTestSuite, runEvaluation } from './api';

// ─── Gauge circle ─────────────────────────────────────────────────────────────
function ScoreGauge({ score, max = 100, label, color = '#2563eb' }) {
  const pct = Math.round((score / max) * 100);
  const radius = 28;
  const circ = 2 * Math.PI * radius;
  const dash = circ * (pct / 100);

  return (
    <div style={{ textAlign: 'center', padding: '4px 8px' }}>
      <svg width="72" height="72" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="36" cy="36" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="6" />
        <circle cx="36" cy="36" r={radius} fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round" style={{ transition: 'stroke-dasharray 0.6s ease' }} />
      </svg>
      <div style={{ marginTop: -54, fontSize: '1rem', fontWeight: 700, color }}>{score}</div>
      <div style={{ marginTop: 22, fontSize: '0.72rem', color: '#64748b', fontWeight: 500 }}>{label}</div>
    </div>
  );
}

// ─── Metric row ───────────────────────────────────────────────────────────────
function MetricRow({ name, metric }) {
  const pct = Math.round((metric.score || 0) * 100);
  const passed = metric.passed;
  return (
    <tr>
      <td style={{ fontSize: '0.83rem', fontWeight: 600, textTransform: 'capitalize' }}>
        {name.replace(/_/g, ' ')}
      </td>
      <td>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ flex: 1, height: 8, background: '#e2e8f0', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${pct}%`, height: '100%', background: pct >= 60 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#ef4444', borderRadius: 99, transition: 'width 0.5s' }} />
          </div>
          <span style={{ fontSize: '0.82rem', fontWeight: 700, minWidth: 36 }}>{pct}%</span>
        </div>
      </td>
      <td>
        <span style={{
          padding: '2px 8px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 700,
          background: passed ? '#dcfce7' : '#fee2e2',
          color: passed ? '#166534' : '#b91c1c',
        }}>{passed ? '✓ Pass' : '✗ Fail'}</span>
      </td>
      <td style={{ fontSize: '0.75rem', color: '#64748b', maxWidth: 280 }}>{metric.reason}</td>
      <td style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{metric.mode}</td>
    </tr>
  );
}

// ─── Judge dimension card ─────────────────────────────────────────────────────
function DimensionCard({ name, dim }) {
  const pct = Math.round((dim.score / dim.max) * 100);
  const color = pct >= 80 ? '#10b981' : pct >= 60 ? '#2563eb' : pct >= 40 ? '#f59e0b' : '#ef4444';
  return (
    <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 16, background: '#fff' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#1a202c', textTransform: 'capitalize' }}>
          {name.replace(/_/g, ' ')}
        </div>
        <div style={{ fontSize: '1rem', fontWeight: 800, color }}>{dim.score}/{dim.max}</div>
      </div>
      <div style={{ height: 6, background: '#e2e8f0', borderRadius: 99, overflow: 'hidden', marginBottom: 8 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99 }} />
      </div>
      {dim.notes?.map((note, i) => (
        <div key={i} style={{ fontSize: '0.72rem', color: '#64748b', lineHeight: 1.5 }}>• {note}</div>
      ))}
    </div>
  );
}

// ─── Main EvaluationView ──────────────────────────────────────────────────────
export default function EvaluationView() {
  const [testSuite, setTestSuite] = useState([]);
  const [selectedCase, setSelectedCase] = useState(null);
  const [customQuery, setCustomQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTestSuite(8).then(d => {
      setTestSuite(d.test_cases || []);
      if (d.test_cases?.length) setSelectedCase(d.test_cases[0]);
    }).catch(() => {});
  }, []);

  const runEval = async () => {
    const query = customQuery.trim() || selectedCase?.query;
    if (!query) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await runEvaluation(query);
      setResult(data);
    } catch (e) {
      setError(e.message || 'Evaluation failed');
    } finally {
      setLoading(false);
    }
  };

  const judge = result?.llm_judge;
  const ev = result?.deepeval_evaluation;
  const verdictColor = { Excellent: '#10b981', Good: '#2563eb', Adequate: '#f59e0b', Poor: '#ef4444' };

  return (
    <div>
      {/* Info banner */}
      <div style={{ background: 'linear-gradient(135deg,#1e3a5f,#2563eb)', borderRadius: 12, padding: '16px 20px', marginBottom: 24, color: '#fff' }}>
        <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 6 }}>
          DeepEval RAG Quality Evaluation + LLM-as-Judge
        </div>
        <div style={{ fontSize: '0.82rem', opacity: 0.85, lineHeight: 1.6 }}>
          Evaluates recommendation quality on four RAG metrics (Answer Relevancy, Faithfulness, Contextual Precision, Contextual Recall)
          and scores on four engineering dimensions via an independent LLM judge (Clinical Safety, Technical Accuracy, Actionability, Evidence Basis).
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24, alignItems: 'start' }}>
        {/* Left: test case selector */}
        <div>
          <div className="card">
            <div className="card-title">Test Cases</div>
            <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: 12 }}>
              Representative failure scenarios from the dataset.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {testSuite.map((tc, i) => (
                <div
                  key={i}
                  onClick={() => { setSelectedCase(tc); setCustomQuery(''); }}
                  style={{
                    padding: '10px 12px', borderRadius: 8, cursor: 'pointer', border: '1px solid',
                    borderColor: selectedCase === tc && !customQuery ? '#2563eb' : '#e2e8f0',
                    background: selectedCase === tc && !customQuery ? '#eff6ff' : '#fff',
                    fontSize: '0.78rem', lineHeight: 1.5,
                  }}>
                  <div style={{ fontWeight: 600, color: '#1a202c', marginBottom: 3 }}>{tc.expected_equipment}</div>
                  <div style={{ color: '#64748b' }}>{tc.expected_failure_type} — {tc.expected_unit}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 16, borderTop: '1px solid #e2e8f0', paddingTop: 12 }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: 6 }}>Custom Query</div>
              <textarea
                value={customQuery}
                onChange={e => { setCustomQuery(e.target.value); setSelectedCase(null); }}
                placeholder="Type a custom maintenance query..."
                rows={3}
                style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: '0.78rem', resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            <button
              className="btn btn-primary"
              onClick={runEval}
              disabled={loading || (!selectedCase && !customQuery.trim())}
              style={{ width: '100%', marginTop: 12 }}>
              {loading ? <><span className="spinner"></span> Evaluating...</> : '▶ Run Evaluation'}
            </button>

            {error && <div className="alert alert-error" style={{ marginTop: 12 }}>{error}</div>}
          </div>
        </div>

        {/* Right: results */}
        <div>
          {!result && !loading && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#94a3b8' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>📊</div>
              <div style={{ fontWeight: 600, fontSize: '1rem' }}>Select a test case and run evaluation</div>
              <div style={{ fontSize: '0.83rem', marginTop: 6 }}>Results include DeepEval metrics and LLM-as-judge scores</div>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', padding: '60px 0', color: '#64748b' }}>
              <div className="spinner-dark" style={{ margin: '0 auto 16px' }}></div>
              <div style={{ fontWeight: 600 }}>Running pipeline + evaluation...</div>
              <div style={{ fontSize: '0.82rem', marginTop: 6, color: '#94a3b8' }}>
                LangGraph → DeepEval metrics → LLM-as-judge
              </div>
            </div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Top summary */}
              <div className="card">
                <div className="card-title">Evaluation Summary</div>
                <div style={{ marginTop: 4, fontSize: '0.82rem', color: '#64748b', marginBottom: 16, background: '#f8fafc', padding: '8px 12px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
                  <strong>Query:</strong> {result.query}
                </div>
                <div style={{ display: 'flex', gap: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <ScoreGauge score={ev?.overall_score ?? 0} label="DeepEval Score" color="#2563eb" />
                  <ScoreGauge score={judge?.total_score ?? 0} label="LLM Judge Score" color="#7c3aed" />
                  <ScoreGauge score={result.recommendation_confidence ?? 0} label="Agent Confidence" color="#16a34a" />
                  <div style={{ textAlign: 'center', padding: '4px 8px' }}>
                    <div style={{
                      display: 'inline-block', padding: '8px 16px', borderRadius: 10,
                      background: verdictColor[judge?.verdict] + '22',
                      border: `2px solid ${verdictColor[judge?.verdict] || '#94a3b8'}`,
                      marginTop: 8,
                    }}>
                      <div style={{ fontSize: '1.3rem', fontWeight: 800, color: verdictColor[judge?.verdict] }}>
                        {judge?.verdict || '—'}
                      </div>
                    </div>
                    <div style={{ marginTop: 6, fontSize: '0.72rem', color: '#64748b' }}>Judge Verdict</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
                  <div style={{ fontSize: '0.78rem', padding: '4px 12px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 99, color: '#1d4ed8' }}>
                    {ev?.passed_metrics}/{ev?.total_metrics} RAG metrics passed
                  </div>
                  <div style={{ fontSize: '0.78rem', padding: '4px 12px', background: '#f3e8ff', border: '1px solid #d8b4fe', borderRadius: 99, color: '#6d28d9' }}>
                    Judge mode: {judge?.judge_mode}
                  </div>
                  <div style={{ fontSize: '0.78rem', padding: '4px 12px', background: '#ecfdf5', border: '1px solid #86efac', borderRadius: 99, color: '#15803d' }}>
                    {result.retrieved_count} incidents retrieved
                  </div>
                  <div style={{ fontSize: '0.78rem', padding: '4px 12px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 99, color: '#64748b' }}>
                    {result.pipeline_mode}
                  </div>
                </div>
              </div>

              {/* DeepEval Metrics */}
              <div className="card">
                <div className="card-title">DeepEval RAG Metrics</div>
                <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: 12 }}>
                  Mode: <strong>{ev?.mode}</strong> · DeepEval available: <strong>{ev?.deepeval_available ? 'Yes' : 'No'}</strong> · Context docs: <strong>{ev?.context_count}</strong>
                </p>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th style={{ minWidth: 160 }}>Score</th>
                        <th>Status</th>
                        <th>Reason</th>
                        <th>Engine</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(ev?.metrics || {}).map(([name, m]) => (
                        <MetricRow key={name} name={name} metric={m} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* LLM Judge Dimensions */}
              {judge && (
                <div className="card">
                  <div className="card-title">LLM-as-Judge — Dimension Scores</div>
                  <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: 14 }}>
                    Independent judge scoring on four biomedical engineering criteria (0–25 each, total 0–100).
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px,1fr))', gap: 12 }}>
                    {Object.entries(judge.dimension_scores || {}).map(([name, dim]) => (
                      <DimensionCard key={name} name={name} dim={dim} />
                    ))}
                  </div>
                  {judge.reasoning && (
                    <div style={{ marginTop: 14, padding: '10px 14px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: '0.82rem', color: '#475569', lineHeight: 1.6 }}>
                      <strong>Judge reasoning:</strong> {judge.reasoning}
                    </div>
                  )}
                </div>
              )}

              {/* Timing */}
              {result.node_timings && Object.keys(result.node_timings).length > 0 && (
                <div className="card">
                  <div className="card-title">Pipeline Node Timings</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginTop: 10 }}>
                    {Object.entries(result.node_timings).map(([node, ms]) => (
                      <div key={node} style={{ padding: '6px 12px', background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, fontSize: '0.78rem' }}>
                        <strong>{node.replace(/_/g, ' ')}</strong>: {ms}ms
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
