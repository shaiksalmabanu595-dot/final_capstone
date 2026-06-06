import axios from 'axios';

const BASE = 'http://localhost:8000';

export const api = axios.create({ baseURL: BASE, timeout: 120000 });

export const fetchHealth = () => api.get('/api/health').then(r => r.data);
export const fetchStats = () => api.get('/api/equipment/stats').then(r => r.data);
export const fetchTypes = () => api.get('/api/equipment/types').then(r => r.data);
export const fetchIncidents = (params) => api.get('/api/maintenance/incidents', { params }).then(r => r.data);
export const submitQuery = (payload) => api.post('/api/query', payload).then(r => r.data);
export const detectAnomalies = (payload) => api.post('/api/analyze/anomaly', payload).then(r => r.data);
export const fetchEquipment = (id) => api.get(`/api/equipment/${id}`).then(r => r.data);
export const fetchPipelineSchema = () => api.get('/api/pipeline/schema').then(r => r.data);
export const validateGuardrail = (query) => api.post('/api/guardrail/validate', { query }).then(r => r.data);
export const fetchTestSuite = (n = 8) => api.get(`/api/evaluate/test-suite?sample_size=${n}`).then(r => r.data);
export const runEvaluation = (query, k = 5) => api.post('/api/evaluate', { query, k, include_judge: true }).then(r => r.data);
