import { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import MaintenanceIncidents from './components/MaintenanceIncidents';
import AnomalyDetection from './components/AnomalyDetection';
import PipelineView from './components/PipelineView';
import EvaluationView from './components/EvaluationView';
import { fetchHealth } from './components/api';
import './index.css';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: <GridIcon /> },
  { id: 'chat', label: 'AI Assistant', icon: <ChatIcon /> },
  { id: 'incidents', label: 'Maintenance Records', icon: <TableIcon /> },
  { id: 'anomaly', label: 'Anomaly Detection', icon: <AlertIcon /> },
  { id: 'pipeline', label: 'LangGraph Pipeline', icon: <PipelineIcon /> },
  { id: 'evaluation', label: 'Evaluation & Judge', icon: <EvalIcon /> },
];

const PAGE_TITLES = {
  dashboard: 'Equipment Reliability Dashboard',
  chat: 'AI-Powered Maintenance Assistant',
  incidents: 'Maintenance Incident Records',
  anomaly: 'Equipment Anomaly Detection',
  pipeline: 'LangGraph + GPT-4o mini Guardrails',
  evaluation: 'DeepEval RAG Evaluation + LLM-as-Judge',
};

export default function App() {
  const [active, setActive] = useState('dashboard');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error' }));
  }, []);

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div style={{ width: 36, height: 36, background: '#06b6d4', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem' }}>⚕</div>
            <div>
              <h1 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', lineHeight: 1.3 }}>MedEquip AI</h1>
            </div>
          </div>
          <div className="sub">Reliability Intelligence Assistant</div>
        </div>

        <div className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <div key={item.id} className={`nav-item ${active === item.id ? 'active' : ''}`} onClick={() => setActive(item.id)}>
              {item.icon}
              <span>{item.label}</span>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div>LangGraph + GPT-4o mini</div>
          <div style={{ marginTop: 4 }}>RAG + Multi-Agent System</div>
          <div style={{ marginTop: 4, color: 'rgba(255,255,255,0.25)' }}>v2.0.0</div>
        </div>
      </nav>

      <div className="main-content">
        <div className="top-bar">
          <h2>{PAGE_TITLES[active]}</h2>
          <div className="status-badge">
            <div className="status-dot" style={{ background: health?.status === 'healthy' ? '#10b981' : '#ef4444' }}></div>
            {health?.status === 'healthy' ? (
              <span>System Online — {health.dataset_records?.toLocaleString()} records loaded</span>
            ) : (
              <span style={{ color: '#ef4444' }}>Connecting to backend...</span>
            )}
          </div>
        </div>

        <div className="page-body">
          {active === 'dashboard' && <Dashboard />}
          {active === 'chat' && <ChatInterface />}
          {active === 'incidents' && <MaintenanceIncidents />}
          {active === 'anomaly' && <AnomalyDetection />}
          {active === 'pipeline' && <PipelineView />}
          {active === 'evaluation' && <EvaluationView />}
        </div>
      </div>
    </div>
  );
}

function GridIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  );
}

function TableIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"/>
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

function PipelineIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="5" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="19" cy="19" r="2"/>
      <line x1="7" y1="11" x2="17" y2="6"/><line x1="7" y1="13" x2="17" y2="18"/>
    </svg>
  );
}

function EvalIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 11l3 3L22 4"/>
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  );
}
