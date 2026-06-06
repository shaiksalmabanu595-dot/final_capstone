import { useState, useEffect } from 'react';
import { fetchIncidents, fetchTypes } from './api';

const PAGE_SIZE = 20;

export default function MaintenanceIncidents() {
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [types, setTypes] = useState({});
  const [filters, setFilters] = useState({
    equipment_type: '',
    hospital_unit: '',
    severity: '',
    failure_only: false,
  });

  useEffect(() => {
    fetchTypes().then(setTypes).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setPage(0);
    const params = { limit: PAGE_SIZE, offset: 0 };
    if (filters.equipment_type) params.equipment_type = filters.equipment_type;
    if (filters.hospital_unit) params.hospital_unit = filters.hospital_unit;
    if (filters.severity) params.severity = filters.severity;
    if (filters.failure_only) params.failure_only = true;

    fetchIncidents(params)
      .then(data => { setIncidents(data.incidents); setTotal(data.total); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  const loadPage = (p) => {
    setLoading(true);
    const params = { limit: PAGE_SIZE, offset: p * PAGE_SIZE };
    if (filters.equipment_type) params.equipment_type = filters.equipment_type;
    if (filters.hospital_unit) params.hospital_unit = filters.hospital_unit;
    if (filters.severity) params.severity = filters.severity;
    if (filters.failure_only) params.failure_only = true;

    fetchIncidents(params)
      .then(data => { setIncidents(data.incidents); setPage(p); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const badgeClass = (severity) => {
    const s = severity?.toLowerCase();
    if (s === 'critical') return 'badge-critical';
    if (s === 'high') return 'badge-high';
    if (s === 'medium') return 'badge-medium';
    return 'badge-low';
  };

  return (
    <div>
      {/* Filters */}
      <div className="card" style={{ marginBottom: 16, padding: '16px 20px' }}>
        <div className="filters-row">
          <select className="filter-select" value={filters.equipment_type} onChange={e => setFilters(f => ({ ...f, equipment_type: e.target.value }))}>
            <option value="">All Equipment Types</option>
            {(types.equipment_types || []).map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <select className="filter-select" value={filters.hospital_unit} onChange={e => setFilters(f => ({ ...f, hospital_unit: e.target.value }))}>
            <option value="">All Hospital Units</option>
            {(types.hospital_units || []).map(u => <option key={u} value={u}>{u}</option>)}
          </select>
          <select className="filter-select" value={filters.severity} onChange={e => setFilters(f => ({ ...f, severity: e.target.value }))}>
            <option value="">All Severities</option>
            {['Critical','High','Medium','Low'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={filters.failure_only} onChange={e => setFilters(f => ({ ...f, failure_only: e.target.checked }))} />
            Failures only
          </label>
          <button className="btn btn-secondary" style={{ padding: '7px 14px', fontSize: '0.82rem' }} onClick={() => setFilters({ equipment_type: '', hospital_unit: '', severity: '', failure_only: false })}>
            Reset Filters
          </button>
        </div>
        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
          Showing {incidents.length} of <strong>{total.toLocaleString()}</strong> records
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="loading-state">
          <div className="spinner-dark"></div>
          <p>Loading incidents...</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Equipment</th>
                  <th>Type</th>
                  <th>Unit</th>
                  <th>Date</th>
                  <th>Failure Type</th>
                  <th>Severity</th>
                  <th>Downtime (h)</th>
                  <th>Cost ($)</th>
                  <th>Tool Wear</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: '#64748b' }}>{inc.record_id}</td>
                    <td><strong>{inc.equipment_id}</strong></td>
                    <td>{inc.equipment_type}</td>
                    <td>{inc.hospital_unit}</td>
                    <td style={{ fontSize: '0.78rem', color: '#64748b' }}>{inc.timestamp?.slice(0, 10)}</td>
                    <td>
                      {inc.machine_failure === 1 ? (
                        <span className="badge badge-failure">{inc.failure_type}</span>
                      ) : (
                        <span className="badge badge-ok">No Failure</span>
                      )}
                    </td>
                    <td><span className={`badge ${badgeClass(inc.severity)}`}>{inc.severity}</span></td>
                    <td>{inc.downtime_hours > 0 ? <span style={{ color: '#ef4444', fontWeight: 600 }}>{inc.downtime_hours}</span> : '—'}</td>
                    <td>{inc.maintenance_cost_usd > 0 ? `$${inc.maintenance_cost_usd.toLocaleString()}` : '—'}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 60, height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(100, (inc.tool_wear_min / 250) * 100)}%`, height: '100%', background: inc.tool_wear_min > 200 ? '#ef4444' : inc.tool_wear_min > 150 ? '#f59e0b' : '#10b981', borderRadius: 3 }} />
                        </div>
                        <span style={{ fontSize: '0.78rem' }}>{inc.tool_wear_min}m</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination" style={{ padding: '12px 16px' }}>
            <button className="page-btn" onClick={() => loadPage(0)} disabled={page === 0}>«</button>
            <button className="page-btn" onClick={() => loadPage(page - 1)} disabled={page === 0}>‹</button>
            <span style={{ fontSize: '0.83rem', color: '#64748b', padding: '0 8px' }}>
              Page {page + 1} of {totalPages}
            </span>
            <button className="page-btn" onClick={() => loadPage(page + 1)} disabled={page >= totalPages - 1}>›</button>
            <button className="page-btn" onClick={() => loadPage(totalPages - 1)} disabled={page >= totalPages - 1}>»</button>
          </div>
        </div>
      )}
    </div>
  );
}
