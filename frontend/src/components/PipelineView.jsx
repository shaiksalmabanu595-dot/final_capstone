import { useState, useEffect } from 'react';
import { fetchPipelineSchema, validateGuardrail } from './api';

const NODE_COLORS = {
  guardrail: { bg: '#fef3c7', border: '#d97706', icon: '🛡️', label: 'GPT-4o mini' },
  retrieval: { bg: '#eff6ff', border: '#2563eb', icon: '🔍', label: 'FAISS+BM25' },
  agent:     { bg: '#f0fdf4', border: '#16a34a', icon: '🤖', label: 'AI Agent' },
  terminal:  { bg: '#fce7f3', border: '#be185d', icon: '🚫', label: 'Terminal' },
};

function NodeBox({ node, isActive, timing }) {
  const c = NODE_COLORS[node.type] || NODE_COLORS.agent;
  return (
    <div style={{
      border: `2px solid ${c.border}`,
      borderRadius: 10,
      padding: '10px 14px',
      background: isActive ? c.bg : '#fff',
      minWidth: 180,
      maxWidth: 220,
      boxShadow: isActive ? `0 0 0 3px ${c.border}44` : '0 1px 3px rgba(0,0,0,0.06)',
      transition: 'all 0.3s',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: '1.1rem' }}>{c.icon}</span>
        <strong style={{ fontSize: '0.82rem', color: '#1a202c' }}>{node.label}</strong>
      </div>
      <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: 4 }}>
        <span style={{ background: c.bg, border: `1px solid ${c.border}`, padding: '1px 6px', borderRadius: 99, color: c.border, fontWeight: 600 }}>
          {node.model}
        </span>
      </div>
      <div style={{ fontSize: '0.72rem', color: '#64748b', lineHeight: 1.4 }}>{node.description}</div>
      {timing && (
        <div style={{ fontSize: '0.68rem', color: c.border, fontWeight: 600, marginTop: 4 }}>
          ⏱ {timing}ms
        </div>
      )}
    </div>
  );
}

function Arrow({ condition, horizontal }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: horizontal ? 'row' : 'column',
      alignItems: 'center',
      gap: 2,
      color: condition === 'INVALID' ? '#ef4444' : condition === 'VALID' ? '#16a34a' : '#94a3b8',
    }}>
      {condition && (
        <span style={{ fontSize: '0.68rem', fontWeight: 700, padding: '1px 6px', borderRadius: 99,
          background: condition === 'INVALID' ? '#fee2e2' : condition === 'VALID' ? '#dcfce7' : '#f1f5f9',
          color: condition === 'INVALID' ? '#b91c1c' : condition === 'VALID' ? '#166534' : '#64748b',
        }}>{condition}</span>
      )}
      <span style={{ fontSize: horizontal ? '1.1rem' : '1rem' }}>
        {horizontal ? '→' : '↓'}
      </span>
    </div>
  );
}

// ─── Guardrail Tester Widget ──────────────────────────────────────────────────
function GuardrailTester() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const test = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await validateGuardrail(query);
      setResult(data.guardrail);
    } catch {
      setResult({ is_valid: false, reason: 'Backend error', intent: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: 24 }}>
      <div className="card-title">GPT-4o mini Guardrail Tester</div>
      <p style={{ fontSize: '0.83rem', color: '#64748b', marginBottom: 12 }}>
        Test the input guardrail independently to see how it classifies queries.
      </p>
      <div style={{ display: 'flex', gap: 10 }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && test()}
          placeholder="Type any query to test the guardrail..."
          style={{ flex: 1, padding: '10px 14px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: '0.87rem', outline: 'none' }}
        />
        <button className="btn btn-primary" onClick={test} disabled={loading || !query.trim()}>
          {loading ? <span className="spinner"></span> : '🛡️'} Test
        </button>
      </div>

      {result && (
        <div style={{
          marginTop: 16,
          padding: 16,
          borderRadius: 10,
          background: result.is_valid ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${result.is_valid ? '#86efac' : '#fca5a5'}`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <span style={{ fontSize: '1.5rem' }}>{result.is_valid ? '✅' : '❌'}</span>
            <div>
              <div style={{ fontWeight: 700, color: result.is_valid ? '#166534' : '#991b1b', fontSize: '0.95rem' }}>
                {result.is_valid ? 'VALID — Query Accepted' : 'INVALID — Query Rejected'}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Mode: {result.guardrail_mode}</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px,1fr))', gap: 10, fontSize: '0.82rem' }}>
            <div><strong>Reason:</strong> {result.reason}</div>
            <div><strong>Intent:</strong> <span style={{ padding: '1px 8px', background: '#e0f2fe', borderRadius: 99, color: '#0369a1' }}>{result.intent}</span></div>
            {result.equipment_type && <div><strong>Equipment:</strong> {result.equipment_type}</div>}
            <div><strong>Urgency:</strong> <span style={{
              padding: '1px 8px', borderRadius: 99, fontWeight: 600,
              background: result.urgency === 'immediate' ? '#fee2e2' : result.urgency === 'routine' ? '#fef9c3' : '#f0fdf4',
              color: result.urgency === 'immediate' ? '#b91c1c' : result.urgency === 'routine' ? '#854d0e' : '#166534',
            }}>{result.urgency}</span></div>
          </div>

          {result.refined_query && result.refined_query !== query && (
            <div style={{ marginTop: 10, padding: '8px 12px', background: '#fff', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: '0.82rem' }}>
              <strong>Refined query:</strong> <em>{result.refined_query}</em>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main PipelineView ────────────────────────────────────────────────────────
export default function PipelineView() {
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPipelineSchema()
      .then(setSchema)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-state"><div className="spinner-dark"></div><p>Loading pipeline schema...</p></div>;
  if (error) return <div className="alert alert-error">Failed to load pipeline schema: {error}</div>;
  if (!schema) return null;

  const { runtime_info } = schema;
  const nodes = schema.schema?.nodes || [];

  // Build node map for quick lookup
  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.id] = n; });

  // Main pipeline (ordered sequence ignoring rejection branch)
  const mainFlow = ['input_guardrail','rag_retrieval','retrieval_agent','reliability_agent','maintenance_agent','recommendation_agent','output_guardrail'];

  return (
    <div>
      {/* Runtime status */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="label">Guardrail Model</div>
          <div className="value" style={{ fontSize: '1.1rem' }}>{runtime_info?.guardrail_model || 'rule_based'}</div>
          <div className="sub" style={{ color: runtime_info?.openai_guardrails ? '#10b981' : '#f59e0b' }}>
            {runtime_info?.openai_guardrails ? '✅ OpenAI key active' : '⚠️ Rule-based fallback'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">Agent Model</div>
          <div className="value" style={{ fontSize: '1.1rem' }}>{runtime_info?.agent_model || 'rule_based'}</div>
          <div className="sub" style={{ color: runtime_info?.claude_agents ? '#10b981' : '#f59e0b' }}>
            {runtime_info?.claude_agents ? '✅ Claude API active' : '⚠️ Rule-based fallback'}
          </div>
        </div>
        <div className="stat-card">
          <div className="label">RAG Mode</div>
          <div className="value" style={{ fontSize: '1rem', marginTop: 6 }}>{runtime_info?.rag_mode}</div>
          <div className="sub">{runtime_info?.embedding_model}</div>
        </div>
        <div className="stat-card">
          <div className="label">Pipeline</div>
          <div className="value" style={{ fontSize: '1rem', marginTop: 6, color: '#2563eb' }}>LangGraph</div>
          <div className="sub">{mainFlow.length} nodes + rejection branch</div>
        </div>
      </div>

      {/* Pipeline Diagram */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">LangGraph Pipeline — State Machine Topology</div>
        <div style={{ marginTop: 16, overflowX: 'auto', paddingBottom: 8 }}>
          {/* Main flow */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', minWidth: 800 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{ padding: '4px 12px', background: '#1e3a5f', color: '#fff', borderRadius: 6, fontSize: '0.72rem', fontWeight: 700 }}>START</div>
              <Arrow horizontal={false} />
            </div>

            {mainFlow.map((nodeId, i) => {
              const node = nodeMap[nodeId];
              if (!node) return null;
              return (
                <div key={nodeId} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {/* Branching from input guardrail */}
                  {nodeId === 'input_guardrail' ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                      <NodeBox node={node} isActive={false} />
                      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', marginTop: 4 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                          <Arrow horizontal={false} condition="VALID" />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                          <Arrow horizontal={false} condition="INVALID" />
                          <div style={{ border: '2px solid #be185d', borderRadius: 10, padding: '8px 12px', background: '#fce7f3', textAlign: 'center', minWidth: 120 }}>
                            <div style={{ fontSize: '1rem' }}>🚫</div>
                            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#be185d' }}>Rejection</div>
                            <div style={{ fontSize: '0.68rem', color: '#64748b' }}>Returns reason</div>
                          </div>
                          <Arrow horizontal={false} />
                          <div style={{ padding: '4px 12px', background: '#be185d', color: '#fff', borderRadius: 6, fontSize: '0.72rem', fontWeight: 700 }}>END</div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {i > 0 && <Arrow horizontal={true} />}
                      <NodeBox node={node} isActive={false} />
                    </div>
                  )}
                </div>
              );
            })}

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Arrow horizontal={true} />
              <div style={{ padding: '4px 12px', background: '#1e3a5f', color: '#fff', borderRadius: 6, fontSize: '0.72rem', fontWeight: 700 }}>END</div>
            </div>
          </div>
        </div>
      </div>

      {/* Node Details Table */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">Node Details</div>
        <div className="table-container" style={{ marginTop: 12 }}>
          <table>
            <thead>
              <tr>
                <th>Node</th>
                <th>Type</th>
                <th>Model / Engine</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {nodes.map((node, i) => {
                const c = NODE_COLORS[node.type] || NODE_COLORS.agent;
                return (
                  <tr key={i}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>{c.icon}</span>
                        <strong style={{ fontSize: '0.85rem' }}>{node.label}</strong>
                      </div>
                    </td>
                    <td>
                      <span style={{ padding: '2px 8px', background: c.bg, border: `1px solid ${c.border}`, borderRadius: 99, fontSize: '0.75rem', color: c.border, fontWeight: 600 }}>
                        {node.type}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.82rem', color: '#64748b' }}>{node.model}</td>
                    <td style={{ fontSize: '0.82rem' }}>{node.description}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* State Schema */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">LangGraph State Schema (TypedDict)</div>
        <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: 20, borderRadius: 8, fontSize: '0.78rem', overflowX: 'auto', marginTop: 12, lineHeight: 1.6 }}>
{`class MedEquipState(TypedDict):
    # Input
    query: str                      # Original user query
    refined_query: str              # GPT-4o mini refined query
    filters: Dict                   # Metadata filters (equipment_type, unit, etc.)
    k: int                          # Number of RAG results
    alpha: float                    # Hybrid search weight (vector vs BM25)

    # Guardrail: input
    input_guardrail_result: Dict    # {is_valid, reason, intent, urgency, ...}
    is_valid: bool                  # Routes to rag_retrieval OR rejection

    # RAG retrieval
    retrieved_docs: List[Dict]      # Top-k maintenance incidents

    # Agent outputs
    retrieval_result: Dict          # Equipment focus, relevant incidents
    reliability_result: Dict        # Failure rate, score, anomalies
    maintenance_result: Dict        # Action plan, immediate actions
    recommendation_result: Dict     # Final synthesised recommendation

    # Guardrail: output
    output_guardrail_result: Dict   # {quality_score, safety_rating, issues, ...}

    # Metadata
    error: Optional[str]            # Set on rejection
    analysis_mode: str              # "LangGraph + GPT-4o mini Guardrails"
    execution_log: List[str]        # Per-node trace log
    node_timings: Dict              # node_name -> elapsed_ms`}
        </pre>
      </div>

      {/* Guardrail Tester */}
      <GuardrailTester />
    </div>
  );
}
