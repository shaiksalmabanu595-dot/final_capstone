import os
import sys
import time
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd

from data_generation import load_dataset
from rag_system import get_rag_system
from agents import run_multi_agent_pipeline
from langgraph_pipeline import run_langgraph_pipeline, GRAPH_SCHEMA, get_pipeline
from guardrails import run_input_guardrail, run_output_guardrail, _openai_key
from evaluation import evaluate_recommendation, build_eval_test_suite
from llm_judge import run_llm_judge

# ─── Startup ──────────────────────────────────────────────────────────────────
df: pd.DataFrame = None
rag = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global df, rag
    print("Initializing Medical Equipment Reliability Assistant...")
    df = load_dataset()
    print(f"Dataset loaded: {len(df)} records")
    rag = get_rag_system()
    rag.build_index(df)
    # Pre-compile LangGraph pipeline at startup
    get_pipeline()
    print("LangGraph pipeline compiled.")
    print("System ready.")
    yield
    print("Shutting down...")


app = FastAPI(
    title="AI-Powered Medical Equipment Reliability Intelligence Assistant",
    description="Biomedical engineering intelligence system for equipment reliability analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Natural language maintenance query")
    k: int = Field(5, ge=1, le=20, description="Number of incidents to retrieve")
    equipment_type: Optional[str] = None
    hospital_unit: Optional[str] = None
    severity: Optional[str] = None
    failure_only: bool = False
    alpha: float = Field(0.6, ge=0.0, le=1.0, description="Weight for vector search vs BM25")


class IncidentResponse(BaseModel):
    record_id: str
    equipment_id: str
    equipment_type: str
    equipment_model: str
    hospital_unit: str
    timestamp: str
    air_temperature_k: float
    process_temperature_k: float
    rotational_speed_rpm: int
    torque_nm: float
    tool_wear_min: int
    machine_failure: int
    failure_type: str
    severity: str
    downtime_hours: float
    maintenance_cost_usd: int
    days_since_last_pm: int
    technician_notes: str
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    refined_query: str
    retrieved_incidents: List[Dict]
    agent_analysis: Dict
    guardrails: Dict
    pipeline_log: List[str]
    node_timings: Dict
    total_analyzed: int
    processing_time_ms: float
    pipeline_mode: str


class GuardrailRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)


class EvaluationRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    k: int = Field(5, ge=1, le=20)
    equipment_type: Optional[str] = None
    hospital_unit: Optional[str] = None
    include_judge: bool = Field(True, description="Also run LLM-as-judge scoring")


class JudgeRequest(BaseModel):
    query: str
    recommendation: Dict[str, Any]
    retrieved_docs: Optional[List[Dict]] = []


class AnomalyRequest(BaseModel):
    equipment_id: Optional[str] = None
    equipment_type: Optional[str] = None
    threshold_temp_k: float = Field(305.0, description="Temperature anomaly threshold")
    threshold_wear_min: int = Field(200, description="Tool wear anomaly threshold")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _validate_query(query: str) -> str:
    query = query.strip()
    medical_keywords = [
        "equipment", "machine", "device", "failure", "maintenance", "error", "alert",
        "mri", "ct", "ventilator", "pump", "monitor", "sensor", "calibrat", "wear",
        "temperature", "speed", "torque", "unit", "icu", "hospital", "downtime",
        "reliability", "anomaly", "malfunction", "repair", "inspect", "diagnos",
        "infusion", "ultrasound", "lab", "scanner", "patient",
    ]
    lower = query.lower()
    if not any(kw in lower for kw in medical_keywords):
        raise HTTPException(
            status_code=400,
            detail="Query must relate to medical equipment maintenance. Please describe an equipment issue or ask about specific devices."
        )
    return query


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    from agents import _api_key_available as _claude_available
    return {
        "status": "healthy",
        "dataset_records": len(df) if df is not None else 0,
        "rag_ready": rag is not None and rag.is_built,
        "claude_api": _claude_available(),
        "openai_api": bool(_openai_key()),
        "pipeline": "LangGraph + GPT-4o mini Guardrails",
    }


@app.post("/api/query", response_model=QueryResponse)
async def query_maintenance(request: QueryRequest):
    start_time = time.time()

    filters = {}
    if request.equipment_type:
        filters["equipment_type"] = request.equipment_type
    if request.hospital_unit:
        filters["hospital_unit"] = request.hospital_unit
    if request.severity:
        filters["severity"] = request.severity
    if request.failure_only:
        filters["failure_only"] = True

    # Run full LangGraph pipeline (includes guardrails + RAG + agents)
    state = run_langgraph_pipeline(
        query=request.query,
        filters=filters,
        k=request.k,
        alpha=request.alpha,
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    # If input guardrail rejected the query, return 400
    if not state.get("is_valid", True) and not state.get("retrieved_docs"):
        raise HTTPException(
            status_code=400,
            detail=state.get("error", "Query rejected by input guardrail."),
        )

    # Clean retrieved docs (remove large document_text field)
    retrieved = state.get("retrieved_docs", [])
    clean_retrieved = [{k: v for k, v in d.items() if k != "document_text"} for d in retrieved]

    # Assemble agent_analysis (same structure as before for frontend compatibility)
    agent_analysis = {
        "retrieval_analysis": state.get("retrieval_result", {}),
        "reliability_analysis": state.get("reliability_result", {}),
        "maintenance_plan": state.get("maintenance_result", {}),
        "final_recommendation": state.get("recommendation_result", {}),
        "analysis_mode": state.get("analysis_mode", "LangGraph"),
    }

    guardrails = {
        "input": state.get("input_guardrail_result", {}),
        "output": state.get("output_guardrail_result", {}),
        "query_intent": state.get("input_guardrail_result", {}).get("intent", "general_inquiry"),
        "query_urgency": state.get("input_guardrail_result", {}).get("urgency", "routine"),
        "output_quality_score": state.get("output_guardrail_result", {}).get("quality_score", 0),
        "safety_rating": state.get("output_guardrail_result", {}).get("safety_rating", "safe"),
    }

    return QueryResponse(
        query=request.query,
        refined_query=state.get("refined_query", request.query),
        retrieved_incidents=clean_retrieved,
        agent_analysis=agent_analysis,
        guardrails=guardrails,
        pipeline_log=state.get("execution_log", []),
        node_timings=state.get("node_timings", {}),
        total_analyzed=len(retrieved),
        processing_time_ms=elapsed_ms,
        pipeline_mode=state.get("analysis_mode", "LangGraph"),
    )


@app.post("/api/guardrail/validate")
async def validate_query(request: GuardrailRequest):
    """Run only the input guardrail to validate a query without full analysis."""
    result = run_input_guardrail(request.query)
    return {"query": request.query, "guardrail": result}


@app.get("/api/pipeline/schema")
async def get_pipeline_schema():
    """Return LangGraph pipeline topology for frontend visualization."""
    from agents import _api_key_available as _claude_avail
    return {
        "schema": GRAPH_SCHEMA,
        "runtime_info": {
            "openai_guardrails": bool(_openai_key()),
            "claude_agents": _claude_avail(),
            "rag_mode": "Hybrid (FAISS + BM25)",
            "embedding_model": "all-MiniLM-L6-v2",
            "guardrail_model": "gpt-4o-mini" if _openai_key() else "rule_based",
            "agent_model": "claude-sonnet-4-6" if _claude_avail() else "rule_based",
        },
    }


@app.get("/api/equipment/stats")
async def get_equipment_stats():
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")

    total = len(df)
    failures = df[df["machine_failure"] == 1]
    failure_rate = round(len(failures) / total * 100, 1)

    by_type = df.groupby("equipment_type").agg(
        total=("record_id", "count"),
        failures=("machine_failure", "sum"),
        avg_downtime=("downtime_hours", "mean"),
        total_cost=("maintenance_cost_usd", "sum"),
    ).reset_index()
    by_type["failure_rate"] = (by_type["failures"] / by_type["total"] * 100).round(1)
    by_type["avg_downtime"] = by_type["avg_downtime"].round(2)

    by_unit = df.groupby("hospital_unit").agg(
        total=("record_id", "count"),
        failures=("machine_failure", "sum"),
    ).reset_index()
    by_unit["failure_rate"] = (by_unit["failures"] / by_unit["total"] * 100).round(1)

    failure_type_counts = failures["failure_type"].value_counts().to_dict()
    severity_counts = df["severity"].value_counts().to_dict()

    monthly = df.copy()
    monthly["month"] = pd.to_datetime(monthly["timestamp"]).dt.to_period("M").astype(str)
    monthly_trend = monthly.groupby("month").agg(
        total=("record_id", "count"),
        failures=("machine_failure", "sum"),
    ).reset_index()

    return {
        "summary": {
            "total_records": total,
            "total_failures": int(len(failures)),
            "failure_rate_pct": failure_rate,
            "total_downtime_hours": round(df["downtime_hours"].sum(), 1),
            "total_maintenance_cost_usd": int(df["maintenance_cost_usd"].sum()),
            "unique_equipment": int(df["equipment_id"].nunique()),
        },
        "by_equipment_type": by_type.to_dict(orient="records"),
        "by_hospital_unit": by_unit.to_dict(orient="records"),
        "failure_types": failure_type_counts,
        "severity_distribution": severity_counts,
        "monthly_trend": monthly_trend.to_dict(orient="records"),
    }


@app.get("/api/maintenance/incidents")
async def get_incidents(
    equipment_type: Optional[str] = None,
    hospital_unit: Optional[str] = None,
    severity: Optional[str] = None,
    failure_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")

    filtered = df.copy()
    if equipment_type:
        filtered = filtered[filtered["equipment_type"].str.lower() == equipment_type.lower()]
    if hospital_unit:
        filtered = filtered[filtered["hospital_unit"].str.lower() == hospital_unit.lower()]
    if severity:
        filtered = filtered[filtered["severity"].str.lower() == severity.lower()]
    if failure_only:
        filtered = filtered[filtered["machine_failure"] == 1]

    total = len(filtered)
    page = filtered.sort_values("timestamp", ascending=False).iloc[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "incidents": page.to_dict(orient="records"),
    }


@app.get("/api/equipment/types")
async def get_equipment_types():
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")

    return {
        "equipment_types": sorted(df["equipment_type"].unique().tolist()),
        "hospital_units": sorted(df["hospital_unit"].unique().tolist()),
        "severity_levels": sorted(df["severity"].unique().tolist()),
        "failure_types": sorted(df["failure_type"].unique().tolist()),
    }


@app.post("/api/analyze/anomaly")
async def detect_anomalies(request: AnomalyRequest):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")

    data = df.copy()
    if request.equipment_id:
        data = data[data["equipment_id"] == request.equipment_id]
    if request.equipment_type:
        data = data[data["equipment_type"].str.lower() == request.equipment_type.lower()]

    if data.empty:
        raise HTTPException(status_code=404, detail="No equipment found matching criteria")

    temp_anomalies = data[data["air_temperature_k"] > request.threshold_temp_k]
    wear_anomalies = data[data["tool_wear_min"] > request.threshold_wear_min]
    speed_mean = data["rotational_speed_rpm"].mean()
    speed_std = data["rotational_speed_rpm"].std()
    speed_anomalies = data[
        (data["rotational_speed_rpm"] < speed_mean - 2 * speed_std) |
        (data["rotational_speed_rpm"] > speed_mean + 2 * speed_std)
    ]

    return {
        "total_analyzed": len(data),
        "temperature_anomalies": {
            "count": int(len(temp_anomalies)),
            "threshold_k": request.threshold_temp_k,
            "equipment_ids": temp_anomalies["equipment_id"].unique().tolist()[:10],
        },
        "wear_anomalies": {
            "count": int(len(wear_anomalies)),
            "threshold_min": request.threshold_wear_min,
            "equipment_ids": wear_anomalies["equipment_id"].unique().tolist()[:10],
        },
        "speed_anomalies": {
            "count": int(len(speed_anomalies)),
            "mean_rpm": round(speed_mean, 1),
            "std_rpm": round(speed_std, 1),
            "equipment_ids": speed_anomalies["equipment_id"].unique().tolist()[:10],
        },
        "overall_risk": (
            "Critical" if len(temp_anomalies) + len(wear_anomalies) > len(data) * 0.3 else
            "High" if len(temp_anomalies) + len(wear_anomalies) > len(data) * 0.15 else
            "Medium" if len(temp_anomalies) + len(wear_anomalies) > len(data) * 0.05 else
            "Low"
        ),
    }


@app.get("/api/equipment/{equipment_id}")
async def get_equipment_history(equipment_id: str):
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")

    history = df[df["equipment_id"] == equipment_id].sort_values("timestamp", ascending=False)
    if history.empty:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_id}' not found")

    recent = history.head(50)
    return {
        "equipment_id": equipment_id,
        "equipment_type": history["equipment_type"].iloc[0],
        "equipment_model": history["equipment_model"].iloc[0],
        "hospital_unit": history["hospital_unit"].iloc[0],
        "total_records": int(len(history)),
        "failure_count": int(history["machine_failure"].sum()),
        "failure_rate_pct": round(history["machine_failure"].mean() * 100, 1),
        "avg_tool_wear": round(history["tool_wear_min"].mean(), 1),
        "total_downtime_hours": round(history["downtime_hours"].sum(), 1),
        "total_cost_usd": int(history["maintenance_cost_usd"].sum()),
        "history": recent.to_dict(orient="records"),
    }


@app.post("/api/evaluate")
async def evaluate_query(request: EvaluationRequest):
    """
    Run a full LangGraph pipeline then evaluate the recommendation quality using:
      - DeepEval RAG metrics (Answer Relevancy, Faithfulness, Contextual Precision, Contextual Recall)
      - Optional LLM-as-judge scoring (4 dimensions: safety, accuracy, actionability, evidence)
    """
    filters = {}
    if request.equipment_type:
        filters["equipment_type"] = request.equipment_type
    if request.hospital_unit:
        filters["hospital_unit"] = request.hospital_unit

    # Run full pipeline to get recommendation + retrieved docs
    state = run_langgraph_pipeline(
        query=request.query,
        filters=filters,
        k=request.k,
        alpha=0.6,
    )

    if not state.get("is_valid", True) and not state.get("retrieved_docs"):
        raise HTTPException(status_code=400, detail=state.get("error", "Query rejected."))

    retrieved = state.get("retrieved_docs", [])
    recommendation = state.get("recommendation_result", {})

    # Run DeepEval metrics
    eval_result = evaluate_recommendation(
        query=request.query,
        retrieved_docs=retrieved,
        recommendation=recommendation,
    )

    # Optionally run LLM-as-judge
    judge_result = None
    if request.include_judge:
        judge_result = run_llm_judge(
            query=request.query,
            recommendation=recommendation,
            retrieved_docs=retrieved,
        )

    return {
        "query": request.query,
        "pipeline_mode": state.get("analysis_mode", "LangGraph"),
        "retrieved_count": len(retrieved),
        "recommendation_confidence": recommendation.get("confidence_score", 0),
        "deepeval_evaluation": eval_result,
        "llm_judge": judge_result,
        "node_timings": state.get("node_timings", {}),
    }


@app.post("/api/judge")
async def judge_recommendation(request: JudgeRequest):
    """
    Run the LLM-as-judge independently on a provided recommendation.
    Useful for re-evaluating cached recommendations or testing the judge.
    """
    result = run_llm_judge(
        query=request.query,
        recommendation=request.recommendation,
        retrieved_docs=request.retrieved_docs or [],
    )
    return {"query": request.query, "judge": result}


@app.get("/api/evaluate/test-suite")
async def get_eval_test_suite(sample_size: int = Query(10, ge=1, le=50)):
    """
    Return a set of representative test cases derived from failure records.
    Used for offline batch evaluation of the RAG + agent pipeline.
    """
    if df is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")
    suite = build_eval_test_suite(df, sample_size=sample_size)
    return {"test_cases": suite, "count": len(suite)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
