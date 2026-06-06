import { useState, useRef, useEffect } from 'react';
import { submitQuery } from './api';

const SUGGESTIONS = [
  "MRI machine downtime increasing after preventive maintenance",
  "Ventilator maintenance failures recurring in ICU units",
  "Infusion pump alerts increasing across multiple wards",
  "CT scanner overheating issues in Radiology department",
  "Patient monitoring devices showing repeated operational anomalies",
  "High tool wear on ICU devices causing failures",
  "Equipment utilization imbalance affecting hospital operations",
];

// ─── Guardrail Badge ──────────────────────────────────────────────────────────
function GuardrailBadge({ guardrails }) {
  if (!guardrails) return null;
  const input = guardrails.input || {};
  const output = guardrails.output || {};
  const isValid = input.is_valid !== false;
  const quality = guardrails.output_quality_score || 0;
  const safety = guardrails.safety_rating || 'safe';
  const mode = input.guardrail_mode || 'rule_based';

  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
      {/* Input guardrail */}
      <span style={{
        padding: '3px 10px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 700,
        background: isValid ? '#dcfce7' : '#fee2e2',
        color: isValid ? '#166534' : '#991b1b',
        border: `1px solid ${isValid ? '#86efac' : '#fca5a5'}`,
      }}>
        🛡️ Input: {isValid ? 'VALID' : 'REJECTED'} ({mode === 'gpt-4o-mini' ? 'GPT-4o mini' : 'Rule-based'})
      </span>

      {/* Intent */}
      {guardrails.query_intent && (
        <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 600, background: '#e0f2fe', color: '#0369a1', border: '1px solid #bae6fd' }}>
          Intent: {guardrails.query_intent.replace(/_/g, ' ')}
        </span>
      )}

      {/* Urgency */}
      {guardrails.query_urgency && (
        <span style={{
          padding: '3px 10px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 600,
          background: guardrails.query_urgency === 'immediate' ? '#fee2e2' : guardrails.query_urgency === 'routine' ? '#fef9c3' : '#f0fdf4',
          color: guardrails.query_urgency === 'immediate' ? '#b91c1c' : guardrails.query_urgency === 'routine' ? '#854d0e' : '#166534',
          border: '1px solid transparent',
        }}>
          ⚡ {guardrails.query_urgency}
        </span>
      )}

      {/* Output quality */}
      {quality > 0 && (
        <span style={{
          padding: '3px 10px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 600,
          background: quality >= 70 ? '#d1fae5' : quality >= 50 ? '#fef9c3' : '#fee2e2',
          color: quality >= 70 ? '#065f46' : quality >= 50 ? '#854d0e' : '#991b1b',
          border: '1px solid transparent',
        }}>
          ✅ Output quality: {quality}/100
        </span>
      )}

      {/* Safety */}
      {safety && safety !== 'N/A' && (
        <span style={{
          padding: '3px 10px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 600,
          background: safety === 'safe' ? '#d1fae5' : safety === 'caution' ? '#fef9c3' : '#fee2e2',
          color: safety === 'safe' ? '#065f46' : safety === 'caution' ? '#854d0e' : '#991b1b',
          border: '1px solid transparent',
        }}>
          🔒 {safety}
        </span>
      )}
    </div>
  );
}

// ─── Pipeline Execution Log ───────────────────────────────────────────────────
function PipelineLog({ log, timings }) {
  const [open, setOpen] = useState(false);
  if (!log || log.length === 0) return null;
  return (
    <details open={open} onToggle={e => setOpen(e.target.open)} style={{ marginTop: 8 }}>
      <summary style={{ cursor: 'pointer', fontSize: '0.78rem', color: '#2563eb', fontWeight: 600, userSelect: 'none' }}>
        📋 LangGraph Execution Log ({log.length} steps)
      </summary>
      <div style={{ marginTop: 8, padding: '10px 12px', background: '#1e293b', borderRadius: 8, fontFamily: 'monospace', fontSize: '0.72rem', lineHeight: 1.8 }}>
        {log.map((entry, i) => {
          const color = entry.includes('VALID') ? '#86efac'
            : entry.includes('INVALID') ? '#fca5a5'
            : entry.includes('guardrail') ? '#fde68a'
            : entry.includes('agent') ? '#a5f3fc'
            : '#e2e8f0';
          return (
            <div key={i} style={{ color, display: 'flex', gap: 8 }}>
              <span style={{ color: '#64748b', minWidth: 20 }}>{i + 1}.</span>
              <span>{entry}</span>
            </div>
          );
        })}
        {timings && Object.keys(timings).length > 0 && (
          <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #334155', color: '#94a3b8' }}>
            <div style={{ marginBottom: 4, color: '#cbd5e1', fontWeight: 600 }}>Node Timings:</div>
            {Object.entries(timings).map(([node, ms]) => (
              <div key={node} style={{ display: 'flex', gap: 10 }}>
                <span style={{ color: '#64748b', minWidth: 180 }}>{node}</span>
                <span style={{ color: '#fbbf24' }}>{ms}ms</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </details>
  );
}

// ─── Refined Query indicator ──────────────────────────────────────────────────
function RefinedQueryNote({ original, refined }) {
  if (!refined || refined === original) return null;
  return (
    <div style={{ padding: '6px 12px', background: '#eff6ff', borderRadius: 6, border: '1px solid #bfdbfe', fontSize: '0.78rem', marginBottom: 8 }}>
      <strong style={{ color: '#1d4ed8' }}>Query refined by GPT-4o mini guardrail:</strong>{' '}
      <em style={{ color: '#1e40af' }}>{refined}</em>
    </div>
  );
}

// ─── Full analysis result message ─────────────────────────────────────────────
function AssistantMessage({ result }) {
  const {
    agent_analysis, retrieved_incidents, total_analyzed, processing_time_ms,
    guardrails, pipeline_log, node_timings, refined_query, query, pipeline_mode,
  } = result;

  const rec = agent_analysis?.final_recommendation || {};
  const rel = agent_analysis?.reliability_analysis || {};
  const maint = agent_analysis?.maintenance_plan || {};

  const reliabilityScore = rel.reliability_score || 0;
  const scoreClass = reliabilityScore >= 70 ? 'good' : reliabilityScore >= 40 ? 'warning' : 'danger';

  return (
    <div style={{ lineHeight: 1.6 }}>
      {/* Guardrail status row */}
      <GuardrailBadge guardrails={guardrails} />

      {/* Refined query note */}
      <RefinedQueryNote original={query} refined={refined_query} />

      {/* Executive Summary */}
      {rec.summary && (
        <div style={{ marginBottom: 12, padding: '10px 14px', background: '#eff6ff', borderRadius: 8, border: '1px solid #bfdbfe', fontSize: '0.87rem' }}>
          <strong>Summary:</strong> {rec.summary}
        </div>
      )}

      {/* Key Metrics */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className={`score-circle ${scoreClass}`}>
          <div style={{ fontSize: '1.2rem' }}>{Math.round(reliabilityScore)}</div>
          <div style={{ fontSize: '0.6rem', opacity: 0.8 }}>SCORE</div>
        </div>
        <div>
          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Risk Assessment</div>
          <span className={`badge badge-${rec.risk_assessment?.toLowerCase() === 'critical' ? 'critical' : rec.risk_assessment?.toLowerCase() === 'high' ? 'high' : rec.risk_assessment?.toLowerCase() === 'medium' ? 'medium' : 'low'}`}>
            {rec.risk_assessment || 'N/A'}
          </span>
          <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: 2 }}>{total_analyzed} incidents | {processing_time_ms}ms</div>
          <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>via {pipeline_mode}</div>
        </div>
        {rec.confidence_score > 0 && (
          <div style={{ padding: '10px 16px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', textAlign: 'center' }}>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#2563eb' }}>{rec.confidence_score}%</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>CONFIDENCE</div>
          </div>
        )}
        {guardrails?.output_quality_score > 0 && (
          <div style={{ padding: '10px 16px', background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0', textAlign: 'center' }}>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#16a34a' }}>{guardrails.output_quality_score}</div>
            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>QUALITY</div>
          </div>
        )}
      </div>

      {/* Root Cause */}
      {rec.root_cause && (
        <div style={{ marginBottom: 10, fontSize: '0.85rem' }}>
          <strong>Root Cause:</strong> {rec.root_cause}
        </div>
      )}

      {/* Key Findings */}
      {rec.key_findings?.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <strong style={{ fontSize: '0.85rem' }}>Key Findings:</strong>
          <ul style={{ paddingLeft: 18, margin: '4px 0', fontSize: '0.83rem' }}>
            {rec.key_findings.map((f, i) => <li key={i} style={{ margin: '2px 0' }}>{f}</li>)}
          </ul>
        </div>
      )}

      {/* Action Plan */}
      {rec.action_plan?.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <strong style={{ fontSize: '0.85rem' }}>Action Plan:</strong>
          <ol style={{ paddingLeft: 18, margin: '4px 0', fontSize: '0.83rem' }}>
            {rec.action_plan.slice(0, 6).map((a, i) => <li key={i} style={{ margin: '2px 0' }}>{a}</li>)}
          </ol>
        </div>
      )}

      {/* Immediate Actions */}
      {maint.immediate_actions?.length > 0 && (
        <div style={{ padding: '8px 12px', background: '#fef2f2', borderRadius: 6, border: '1px solid #fecaca', marginBottom: 10, fontSize: '0.83rem' }}>
          <strong style={{ color: '#b91c1c' }}>⚠️ Immediate Actions Required:</strong>
          <ul style={{ paddingLeft: 16, margin: '4px 0' }}>
            {maint.immediate_actions.map((a, i) => <li key={i}>{a}</li>)}
          </ul>
        </div>
      )}

      {/* Output guardrail issues */}
      {guardrails?.output?.issues && !guardrails.output.issues.includes('No issues found') && (
        <div style={{ padding: '8px 12px', background: '#fef9c3', borderRadius: 6, border: '1px solid #fde68a', marginBottom: 10, fontSize: '0.78rem' }}>
          <strong style={{ color: '#854d0e' }}>⚡ Quality notes:</strong>{' '}
          {guardrails.output.issues.join(' | ')}
        </div>
      )}

      {/* Retrieved Incidents */}
      {retrieved_incidents?.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ cursor: 'pointer', fontSize: '0.78rem', color: '#2563eb', fontWeight: 500 }}>
            🗂️ View {retrieved_incidents.length} retrieved incidents
          </summary>
          <div style={{ marginTop: 8, maxHeight: 220, overflowY: 'auto' }}>
            {retrieved_incidents.map((inc, i) => (
              <div key={i} style={{ padding: '5px 10px', background: '#f8fafc', borderRadius: 6, marginBottom: 5, fontSize: '0.75rem', border: '1px solid #e2e8f0' }}>
                <strong>{inc.equipment_id}</strong> ({inc.equipment_type}) — {inc.hospital_unit} — {inc.failure_type}
                {inc.machine_failure === 1 && <span className="badge badge-failure" style={{ marginLeft: 6 }}>FAILURE</span>}
                <span style={{ color: '#94a3b8', marginLeft: 6 }}>score: {inc.relevance_score?.toFixed(3)}</span>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* LangGraph pipeline log */}
      <PipelineLog log={pipeline_log} timings={node_timings} />
    </div>
  );
}

// ─── Main ChatInterface ───────────────────────────────────────────────────────
export default function ChatInterface() {
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: null,
    text: 'Hello! I am your AI-Powered Medical Equipment Reliability Intelligence Assistant. I use a LangGraph multi-agent pipeline with GPT-4o mini guardrails to analyze equipment issues. Ask me anything about equipment failures, maintenance patterns, or reliability.',
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ equipment_type: '', hospital_unit: '', failure_only: false });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (queryText = input) => {
    const q = queryText.trim();
    if (!q || loading) return;

    setInput('');
    setError(null);
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setLoading(true);

    try {
      const payload = {
        query: q,
        k: 8,
        alpha: 0.6,
        ...(filters.equipment_type && { equipment_type: filters.equipment_type }),
        ...(filters.hospital_unit && { hospital_unit: filters.hospital_unit }),
        failure_only: filters.failure_only,
      };
      const result = await submitQuery(payload);
      setMessages(prev => [...prev, { role: 'assistant', content: result }]);
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Request failed';
      setError(msg);
      setMessages(prev => [...prev, { role: 'assistant', text: `❌ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div>
      {/* Pipeline info bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', background: '#1e293b', borderRadius: 8, marginBottom: 16, fontSize: '0.78rem', color: '#94a3b8', flexWrap: 'wrap' }}>
        <span>🔀 <strong style={{ color: '#e2e8f0' }}>LangGraph Pipeline</strong></span>
        <span>🛡️ <strong style={{ color: '#fde68a' }}>GPT-4o mini</strong> Guardrails</span>
        <span>🔍 <strong style={{ color: '#a5f3fc' }}>Hybrid RAG</strong> (FAISS + BM25)</span>
        <span>🤖 <strong style={{ color: '#86efac' }}>4 AI Agents</strong></span>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 14, padding: '14px 18px' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: 8 }}>FILTERS (Optional)</div>
        <div className="filters-row">
          <select className="filter-select" value={filters.equipment_type} onChange={e => setFilters(f => ({ ...f, equipment_type: e.target.value }))}>
            <option value="">All Equipment Types</option>
            {['MRI','CT Scanner','Ventilator','Infusion Pump','Patient Monitor','Ultrasound','ICU Device','Lab Analyzer'].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <select className="filter-select" value={filters.hospital_unit} onChange={e => setFilters(f => ({ ...f, hospital_unit: e.target.value }))}>
            <option value="">All Hospital Units</option>
            {['ICU','Emergency','Radiology','Cardiology','Neurology','General Ward','Laboratory','Oncology'].map(u => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={filters.failure_only} onChange={e => setFilters(f => ({ ...f, failure_only: e.target.checked }))} />
            Failures only
          </label>
          <button className="btn btn-secondary" style={{ padding: '7px 12px', fontSize: '0.8rem' }} onClick={() => setFilters({ equipment_type: '', hospital_unit: '', failure_only: false })}>
            Reset
          </button>
        </div>
      </div>

      {/* Sample Queries */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: 6, fontWeight: 500 }}>SAMPLE QUERIES</div>
        <div className="suggestions">
          {SUGGESTIONS.map((s, i) => (
            <span key={i} className="suggestion-chip" onClick={() => handleSend(s)}>{s}</span>
          ))}
        </div>
      </div>

      {/* Chat */}
      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-avatar">{msg.role === 'user' ? 'YOU' : 'AI'}</div>
              <div className="message-bubble">
                {msg.content ? <AssistantMessage result={msg.content} /> : <span>{msg.text}</span>}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-avatar">AI</div>
              <div className="message-bubble">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#64748b', fontSize: '0.85rem' }}>
                  <div className="spinner-dark" style={{ width: 18, height: 18, border: '2px solid #e2e8f0', borderTopColor: '#2563eb' }}></div>
                  Running LangGraph pipeline: Input Guardrail → RAG → 4 Agents → Output Guardrail...
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <textarea
            className="chat-input"
            placeholder="Describe a medical equipment issue, e.g. 'MRI machine downtime increasing after maintenance...'"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          />
          <button className="btn btn-primary" onClick={() => handleSend()} disabled={loading || !input.trim()}>
            {loading ? <span className="spinner"></span> : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            )}
            {loading ? 'Analyzing...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
