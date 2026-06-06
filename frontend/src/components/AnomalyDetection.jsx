import { useState } from 'react';
import { detectAnomalies } from './api';

export default function AnomalyDetection() {
  const [form, setForm] = useState({ equipment_type: '', threshold_temp_k: 305, threshold_wear_min: 200 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        threshold_temp_k: parseFloat(form.threshold_temp_k),
        threshold_wear_min: parseInt(form.threshold_wear_min),
        ...(form.equipment_type && { equipment_type: form.equipment_type }),
      };
      const data = await detectAnomalies(payload);
      setResult(data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const riskColor = (risk) => {
    if (risk === 'Critical') return '#ef4444';
    if (risk === 'High') return '#f59e0b';
    if (risk === 'Medium') return '#fbbf24';
    return '#10b981';
  };

  return (
    <div>
      {/* Config Card */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title">Anomaly Detection Parameters</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginTop: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: '#64748b', marginBottom: 6 }}>Equipment Type (optional)</label>
            <select className="filter-select" style={{ width: '100%' }} value={form.equipment_type} onChange={e => setForm(f => ({ ...f, equipment_type: e.target.value }))}>
              <option value="">All Equipment</option>
              {['MRI','CT Scanner','Ventilator','Infusion Pump','Patient Monitor','Ultrasound','ICU Device','Lab Analyzer'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: '#64748b', marginBottom: 6 }}>Temperature Threshold (K)</label>
            <input
              type="number" step="0.5" min="290" max="350"
              value={form.threshold_temp_k}
              onChange={e => setForm(f => ({ ...f, threshold_temp_k: e.target.value }))}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: '0.85rem', outline: 'none' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 500, color: '#64748b', marginBottom: 6 }}>Tool Wear Threshold (min)</label>
            <input
              type="number" step="10" min="50" max="250"
              value={form.threshold_wear_min}
              onChange={e => setForm(f => ({ ...f, threshold_wear_min: e.target.value }))}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: '0.85rem', outline: 'none' }}
            />
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={loading}>
            {loading ? <><span className="spinner"></span> Analyzing...</> : 'Run Anomaly Detection'}
          </button>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {result && (
        <div>
          {/* Overall Risk */}
          <div className="card" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 20 }}>
            <div style={{ width: 100, height: 100, borderRadius: '50%', background: `${riskColor(result.overall_risk)}22`, border: `4px solid ${riskColor(result.overall_risk)}`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: riskColor(result.overall_risk) }}>{result.overall_risk}</div>
              <div style={{ fontSize: '0.62rem', color: '#64748b', textTransform: 'uppercase' }}>Risk Level</div>
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 6 }}>Anomaly Analysis Results</h3>
              <p style={{ fontSize: '0.85rem', color: '#64748b' }}>
                Analyzed <strong>{result.total_analyzed}</strong> equipment records and detected anomalies in temperature, wear, and rotational speed parameters.
              </p>
            </div>
          </div>

          {/* Anomaly Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
            {/* Temperature Anomalies */}
            <div className="card">
              <div className="card-title">Temperature Anomalies</div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: result.temperature_anomalies.count > 0 ? '#ef4444' : '#10b981', marginBottom: 4 }}>
                {result.temperature_anomalies.count}
              </div>
              <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 12 }}>
                Records above {result.temperature_anomalies.threshold_k}K threshold
              </div>
              {result.temperature_anomalies.equipment_ids?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: 6 }}>AFFECTED EQUIPMENT IDs</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.temperature_anomalies.equipment_ids.slice(0, 8).map((id, i) => (
                      <span key={i} style={{ padding: '2px 8px', background: '#fee2e2', color: '#b91c1c', borderRadius: 99, fontSize: '0.75rem', fontWeight: 500 }}>{id}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Wear Anomalies */}
            <div className="card">
              <div className="card-title">Tool Wear Anomalies</div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: result.wear_anomalies.count > 0 ? '#f59e0b' : '#10b981', marginBottom: 4 }}>
                {result.wear_anomalies.count}
              </div>
              <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 12 }}>
                Records above {result.wear_anomalies.threshold_min} minute threshold
              </div>
              {result.wear_anomalies.equipment_ids?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: 6 }}>AFFECTED EQUIPMENT IDs</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.wear_anomalies.equipment_ids.slice(0, 8).map((id, i) => (
                      <span key={i} style={{ padding: '2px 8px', background: '#ffedd5', color: '#c2410c', borderRadius: 99, fontSize: '0.75rem', fontWeight: 500 }}>{id}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Speed Anomalies */}
            <div className="card">
              <div className="card-title">Rotational Speed Anomalies</div>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: result.speed_anomalies.count > 0 ? '#8b5cf6' : '#10b981', marginBottom: 4 }}>
                {result.speed_anomalies.count}
              </div>
              <div style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 12 }}>
                Outliers (±2σ from mean {result.speed_anomalies.mean_rpm} RPM)
              </div>
              {result.speed_anomalies.equipment_ids?.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#64748b', marginBottom: 6 }}>AFFECTED EQUIPMENT IDs</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {result.speed_anomalies.equipment_ids.slice(0, 8).map((id, i) => (
                      <span key={i} style={{ padding: '2px 8px', background: '#ede9fe', color: '#6d28d9', borderRadius: 99, fontSize: '0.75rem', fontWeight: 500 }}>{id}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {!result && !loading && (
        <div className="empty-state">
          <div style={{ fontSize: '3rem', marginBottom: 12 }}>🔍</div>
          <h3 style={{ marginBottom: 8 }}>Ready for Anomaly Detection</h3>
          <p style={{ fontSize: '0.88rem', color: '#94a3b8' }}>Configure parameters above and click "Run Anomaly Detection"</p>
        </div>
      )}
    </div>
  );
}
