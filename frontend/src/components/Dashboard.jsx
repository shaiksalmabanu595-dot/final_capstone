import { useState, useEffect } from 'react';
import { fetchStats } from './api';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const COLORS = ['#2563eb','#ef4444','#f59e0b','#10b981','#8b5cf6','#06b6d4','#ec4899','#14b8a6'];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="loading-state">
      <div className="spinner-dark"></div>
      <p>Loading dashboard data...</p>
    </div>
  );

  if (error) return <div className="alert alert-error">Failed to load dashboard: {error}</div>;
  if (!stats) return null;

  const { summary, by_equipment_type, by_hospital_unit, failure_types, severity_distribution, monthly_trend } = stats;

  const failureTypeData = Object.entries(failure_types || {})
    .filter(([k]) => k !== 'No Failure')
    .map(([name, value]) => ({ name, value }));

  const severityData = Object.entries(severity_distribution || {}).map(([name, value]) => ({ name, value }));

  const trendData = (monthly_trend || []).slice(-12).map(d => ({
    month: d.month,
    Total: d.total,
    Failures: d.failures,
  }));

  const equipData = (by_equipment_type || []).map(d => ({
    name: d.equipment_type?.replace(' ', '\n'),
    'Failure Rate': d.failure_rate,
    'Avg Downtime': parseFloat(d.avg_downtime?.toFixed(1) || 0),
  }));

  return (
    <div>
      {/* Summary Stats */}
      <div className="stats-grid">
        <div className="stat-card primary">
          <div className="label">Total Records</div>
          <div className="value">{summary.total_records?.toLocaleString()}</div>
          <div className="sub">Maintenance incidents</div>
        </div>
        <div className="stat-card danger">
          <div className="label">Total Failures</div>
          <div className="value">{summary.total_failures?.toLocaleString()}</div>
          <div className="sub">{summary.failure_rate_pct}% failure rate</div>
        </div>
        <div className="stat-card warning">
          <div className="label">Total Downtime</div>
          <div className="value">{summary.total_downtime_hours?.toLocaleString()}h</div>
          <div className="sub">Across all equipment</div>
        </div>
        <div className="stat-card success">
          <div className="label">Equipment Fleet</div>
          <div className="value">{summary.unique_equipment}</div>
          <div className="sub">Unique devices tracked</div>
        </div>
        <div className="stat-card">
          <div className="label">Maintenance Cost</div>
          <div className="value">${(summary.total_maintenance_cost_usd / 1000).toFixed(0)}K</div>
          <div className="sub">Total USD spent</div>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="charts-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-title">Failure Rate by Equipment Type (%)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={equipData} margin={{ top: 5, right: 10, bottom: 40, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => [`${v}%`, 'Failure Rate']} />
              <Bar dataKey="Failure Rate" fill="#ef4444" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title">Monthly Incident Trend</div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData} margin={{ top: 5, right: 10, bottom: 20, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="Total" stroke="#2563eb" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Failures" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="charts-grid">
        <div className="card">
          <div className="card-title">Failure Type Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={failureTypeData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({ name, percent }) => `${name.split(' ')[0]} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                {failureTypeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div className="card-title">Severity Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={severityData} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[0,4,4,0]}>
                {severityData.map((d, i) => (
                  <Cell key={i} fill={
                    d.name === 'Critical' ? '#ef4444' :
                    d.name === 'High' ? '#f59e0b' :
                    d.name === 'Medium' ? '#fbbf24' : '#10b981'
                  } />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Equipment by Unit Table */}
      <div className="card" style={{ marginTop: 20 }}>
        <div className="card-title">Failure Rate by Hospital Unit</div>
        <div className="table-container" style={{ marginTop: 12 }}>
          <table>
            <thead>
              <tr>
                <th>Hospital Unit</th>
                <th>Total Incidents</th>
                <th>Failures</th>
                <th>Failure Rate</th>
              </tr>
            </thead>
            <tbody>
              {(by_hospital_unit || []).sort((a, b) => b.failure_rate - a.failure_rate).map((u, i) => (
                <tr key={i}>
                  <td><strong>{u.hospital_unit}</strong></td>
                  <td>{u.total}</td>
                  <td>{u.failures}</td>
                  <td>
                    <span className={`badge badge-${u.failure_rate > 25 ? 'critical' : u.failure_rate > 15 ? 'high' : u.failure_rate > 8 ? 'medium' : 'low'}`}>
                      {u.failure_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
