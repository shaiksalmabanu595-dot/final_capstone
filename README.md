# AI-Powered Medical Equipment Reliability Intelligence Assistant

A full-stack AI system for biomedical engineering teams to analyze equipment reliability using natural language queries, RAG (Retrieval-Augmented Generation), and a multi-agent intelligence pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 3000)                    │
│  Dashboard | AI Chat | Maintenance Records | Anomaly Detection   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST
┌───────────────────────────▼─────────────────────────────────────┐
│                   FastAPI Backend (Port 8000)                    │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   RAG Layer  │  │ Multi-Agent  │  │   Data Processing      │  │
│  │ ─────────── │  │ ─────────── │  │ ─────────────────────  │  │
│  │ FAISS Index │  │ Retrieval    │  │ Synthetic AI4I Dataset │  │
│  │ BM25 Index  │  │ Reliability  │  │ 1000+ maintenance recs │  │
│  │ Hybrid      │  │ Maintenance  │  │ 8 equipment types      │  │
│  │ Search      │  │ Recommend.   │  │ 8 hospital units       │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Anthropic Claude API (optional)              │   │
│  │         Falls back to intelligent rule-based engine       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
capstone med/
├── backend/
│   ├── main.py              # FastAPI application & all API endpoints
│   ├── agents.py            # Multi-agent system (4 AI agents)
│   ├── rag_system.py        # RAG pipeline (FAISS + BM25 hybrid search)
│   ├── data_generation.py   # Synthetic medical equipment data generation
│   ├── data/                # Generated CSV dataset + FAISS cache
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── src/
    │   ├── App.jsx           # Main app with sidebar navigation
    │   ├── index.css         # Global styles
    │   └── components/
    │       ├── api.js              # Axios API client
    │       ├── Dashboard.jsx       # Analytics dashboard with charts
    │       ├── ChatInterface.jsx   # Natural language query interface
    │       ├── MaintenanceIncidents.jsx # Filterable incidents table
    │       └── AnomalyDetection.jsx     # Equipment anomaly detector
    └── package.json
```

## Setup & Run

### Backend

```bash
cd "capstone med/backend"

# Install dependencies
pip3 install -r requirements.txt

# (Optional) Set Anthropic API key for enhanced AI analysis
export ANTHROPIC_API_KEY=your_key_here

# Start the server (auto-generates dataset + builds RAG index on first run)
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd "capstone med/frontend"
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| POST | `/api/query` | Natural language equipment query with AI analysis |
| GET | `/api/equipment/stats` | Dashboard statistics |
| GET | `/api/maintenance/incidents` | List incidents (with filters) |
| GET | `/api/equipment/types` | Available equipment types & units |
| POST | `/api/analyze/anomaly` | Equipment anomaly detection |
| GET | `/api/equipment/{id}` | Equipment history by ID |

### Sample Query Request

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MRI machine downtime increasing after preventive maintenance",
    "k": 8,
    "equipment_type": "MRI",
    "failure_only": false,
    "alpha": 0.6
  }'
```

### Sample Query Response

```json
{
  "query": "MRI machine downtime increasing after preventive maintenance",
  "retrieved_incidents": [...],
  "agent_analysis": {
    "retrieval_analysis": { "relevant_incidents": [...], "query_intent": "..." },
    "reliability_analysis": { "failure_rate": 22.2, "reliability_score": 60.0, ... },
    "maintenance_plan": { "immediate_actions": [...], "scheduled_maintenance": [...] },
    "final_recommendation": {
      "summary": "...",
      "root_cause": "...",
      "confidence_score": 85,
      "risk_assessment": "High",
      "action_plan": [...]
    }
  },
  "processing_time_ms": 45.6
}
```

## Features Implemented

### Requirement 1 (Basic)
- [x] RAG for maintenance incident retrieval (FAISS vector store)
- [x] Hybrid search (BM25 keyword + vector semantic search)
- [x] Equipment maintenance semantic search
- [x] Metadata filtering (equipment type, hospital unit, severity)
- [x] Input validation guardrails
- [x] Incident similarity ranking with scores
- [x] REST API endpoints for all core functionality

### Requirement 2 (Advanced)
- [x] Multi-Agent Equipment Intelligence System:
  - Agent 1: Equipment Retrieval Agent
  - Agent 2: Reliability Analysis Agent
  - Agent 3: Maintenance Planning Agent
  - Agent 4: Chief Recommendation Agent
- [x] Equipment anomaly correlation analysis
- [x] LLM-as-judge validation (with Claude API)
- [x] Token optimization (fallback to rule-based when needed)
- [x] React frontend interface

### Optional Features
- [x] Real-time equipment analytics dashboard
- [x] Equipment utilization analysis
- [x] Maintenance prioritization recommendations
- [x] Anomaly detection with configurable thresholds

## Dataset

Synthetic dataset based on AI4I Predictive Maintenance schema with medical equipment context:
- **1000 maintenance records** across 8 equipment types
- **Equipment Types**: MRI, CT Scanner, Ventilator, Infusion Pump, Patient Monitor, Ultrasound, ICU Device, Lab Analyzer
- **Hospital Units**: ICU, Emergency, Radiology, Cardiology, Neurology, General Ward, Laboratory, Oncology
- **Failure Types**: Tool Wear, Heat Dissipation, Power, Overstrain, Random
- **Key Fields**: equipment_id, air_temperature_k, process_temperature_k, rotational_speed_rpm, tool_wear_min, failure_type

## Sample Queries to Try

- "MRI machine downtime increasing after preventive maintenance"
- "Ventilator maintenance failures recurring in ICU units"
- "Infusion pump alerts increasing across multiple wards"
- "CT scanner overheating issues in Radiology"
- "High tool wear on patient monitoring devices"
- "Equipment with power supply failures"
