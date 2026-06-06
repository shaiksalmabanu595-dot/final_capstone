"""
LangGraph Multi-Agent Pipeline for Medical Equipment Reliability Analysis

Graph topology:
  START
    └─► input_guardrail (GPT-4o mini)
          ├─ INVALID ─► rejection ─► END
          └─ VALID   ─► rag_retrieval
                          └─► retrieval_agent
                                └─► reliability_agent
                                      └─► maintenance_agent
                                            └─► recommendation_agent
                                                  └─► output_guardrail (GPT-4o mini)
                                                        └─► END
"""

import time
from typing import TypedDict, List, Optional, Dict, Any

from langgraph.graph import StateGraph, END

from guardrails import run_input_guardrail, run_output_guardrail
from agents import (
    equipment_retrieval_agent,
    reliability_analysis_agent,
    maintenance_agent,
    recommendation_agent,
    _get_client,
)
from rag_system import get_rag_system


# ─── State schema ─────────────────────────────────────────────────────────────
class MedEquipState(TypedDict):
    # Original + refined query
    query: str
    refined_query: str

    # RAG search config
    filters: Dict
    k: int
    alpha: float

    # Guardrail: input
    input_guardrail_result: Dict
    is_valid: bool

    # RAG retrieval output
    retrieved_docs: List[Dict]

    # Agent outputs
    retrieval_result: Dict
    reliability_result: Dict
    maintenance_result: Dict
    recommendation_result: Dict

    # Guardrail: output
    output_guardrail_result: Dict

    # Execution metadata
    error: Optional[str]
    analysis_mode: str
    execution_log: List[str]
    node_timings: Dict   # node_name -> elapsed_ms


# ─── Helper ───────────────────────────────────────────────────────────────────
def _log(state: MedEquipState, msg: str) -> List[str]:
    return state.get("execution_log", []) + [msg]


def _time_ms(t0: float) -> float:
    return round((time.time() - t0) * 1000, 1)


# ─── Node: Input Guardrail ────────────────────────────────────────────────────
def node_input_guardrail(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    result = run_input_guardrail(state["query"])
    is_valid = result.get("is_valid", False)
    mode = result.get("guardrail_mode", "rule_based")

    timings = dict(state.get("node_timings", {}))
    timings["input_guardrail"] = _time_ms(t0)

    return {
        **state,
        "input_guardrail_result": result,
        "is_valid": is_valid,
        "refined_query": result.get("refined_query", state["query"]) if is_valid else state["query"],
        "execution_log": _log(state, f"[input_guardrail] {'✅ VALID' if is_valid else '❌ INVALID'} via {mode} — {result.get('reason', '')}"),
        "node_timings": timings,
    }


# ─── Routing from input guardrail ─────────────────────────────────────────────
def route_after_input(state: MedEquipState) -> str:
    return "valid" if state.get("is_valid", False) else "invalid"


# ─── Node: Rejection ──────────────────────────────────────────────────────────
def node_rejection(state: MedEquipState) -> MedEquipState:
    guardrail = state.get("input_guardrail_result", {})
    reason = guardrail.get("reason", "Query not relevant to medical equipment maintenance.")
    return {
        **state,
        "error": reason,
        "retrieved_docs": [],
        "retrieval_result": {},
        "reliability_result": {},
        "maintenance_result": {},
        "recommendation_result": {
            "summary": f"Query rejected by input guardrail: {reason}",
            "root_cause": "N/A — query was not about medical equipment maintenance.",
            "risk_assessment": "N/A",
            "confidence_score": 0,
            "key_findings": ["Query did not pass input validation guardrail."],
            "action_plan": ["Please rephrase your query to describe a medical equipment issue."],
        },
        "output_guardrail_result": {
            "is_safe": True,
            "quality_score": 0,
            "issues": ["Query rejected at input guardrail"],
            "safety_rating": "N/A",
            "approved_recommendation": reason,
            "guardrail_mode": "rejected",
        },
        "execution_log": _log(state, f"[rejection] Query rejected: {reason}"),
    }


# ─── Node: RAG Retrieval ──────────────────────────────────────────────────────
def node_rag_retrieval(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    rag = get_rag_system()

    # Auto-initialize index if not built (e.g., when running outside FastAPI)
    if not rag.is_built:
        from data_generation import load_dataset
        df = load_dataset()
        rag.build_index(df)

    query = state.get("refined_query") or state["query"]
    docs = rag.hybrid_search(
        query=query,
        k=state.get("k", 5),
        alpha=state.get("alpha", 0.6),
        filters=state.get("filters", {}),
    )

    timings = dict(state.get("node_timings", {}))
    timings["rag_retrieval"] = _time_ms(t0)

    return {
        **state,
        "retrieved_docs": docs,
        "execution_log": _log(state, f"[rag_retrieval] Retrieved {len(docs)} documents via hybrid search (α={state.get('alpha', 0.6)})"),
        "node_timings": timings,
    }


# ─── Node: Equipment Retrieval Agent ─────────────────────────────────────────
def node_retrieval_agent(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    client = _get_client()
    query = state.get("refined_query") or state["query"]
    result = equipment_retrieval_agent(query, state.get("retrieved_docs", []), client)

    timings = dict(state.get("node_timings", {}))
    timings["retrieval_agent"] = _time_ms(t0)

    eq_focus = result.get("equipment_focus", [])
    return {
        **state,
        "retrieval_result": result,
        "execution_log": _log(state, f"[retrieval_agent] Focus: {eq_focus} — Intent: {result.get('query_intent','')[:60]}"),
        "node_timings": timings,
    }


# ─── Node: Reliability Analysis Agent ────────────────────────────────────────
def node_reliability_agent(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    client = _get_client()
    query = state.get("refined_query") or state["query"]
    result = reliability_analysis_agent(
        query,
        state.get("retrieved_docs", []),
        state.get("retrieval_result", {}),
        client,
    )

    timings = dict(state.get("node_timings", {}))
    timings["reliability_agent"] = _time_ms(t0)

    return {
        **state,
        "reliability_result": result,
        "execution_log": _log(state, f"[reliability_agent] Score: {result.get('reliability_score', 0)}/100 — Failure rate: {result.get('failure_rate', 0)}%"),
        "node_timings": timings,
    }


# ─── Node: Maintenance Agent ──────────────────────────────────────────────────
def node_maintenance_agent(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    client = _get_client()
    query = state.get("refined_query") or state["query"]
    result = maintenance_agent(
        query,
        state.get("retrieved_docs", []),
        state.get("reliability_result", {}),
        client,
    )

    timings = dict(state.get("node_timings", {}))
    timings["maintenance_agent"] = _time_ms(t0)

    immediate = result.get("immediate_actions", [])
    return {
        **state,
        "maintenance_result": result,
        "execution_log": _log(state, f"[maintenance_agent] {len(immediate)} immediate action(s) — Urgency: {result.get('maintenance_urgency','N/A')}"),
        "node_timings": timings,
    }


# ─── Node: Recommendation Agent ──────────────────────────────────────────────
def node_recommendation_agent(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    client = _get_client()
    query = state.get("refined_query") or state["query"]
    result = recommendation_agent(
        query,
        state.get("retrieved_docs", []),
        state.get("retrieval_result", {}),
        state.get("reliability_result", {}),
        state.get("maintenance_result", {}),
        client,
    )

    timings = dict(state.get("node_timings", {}))
    timings["recommendation_agent"] = _time_ms(t0)

    return {
        **state,
        "recommendation_result": result,
        "execution_log": _log(state, f"[recommendation_agent] Risk: {result.get('risk_assessment','?')} — Confidence: {result.get('confidence_score', 0)}%"),
        "node_timings": timings,
    }


# ─── Node: Output Guardrail ───────────────────────────────────────────────────
def node_output_guardrail(state: MedEquipState) -> MedEquipState:
    t0 = time.time()
    query = state.get("refined_query") or state["query"]
    recommendation = state.get("recommendation_result", {})
    result = run_output_guardrail(query, recommendation)

    timings = dict(state.get("node_timings", {}))
    timings["output_guardrail"] = _time_ms(t0)
    mode = result.get("guardrail_mode", "rule_based")

    return {
        **state,
        "output_guardrail_result": result,
        "execution_log": _log(state, f"[output_guardrail] Quality: {result.get('quality_score', 0)}/100 — Safety: {result.get('safety_rating', '?')} via {mode}"),
        "node_timings": timings,
    }


# ─── Build & compile graph ────────────────────────────────────────────────────
def _build_graph() -> StateGraph:
    g = StateGraph(MedEquipState)

    g.add_node("input_guardrail", node_input_guardrail)
    g.add_node("rag_retrieval", node_rag_retrieval)
    g.add_node("retrieval_agent", node_retrieval_agent)
    g.add_node("reliability_agent", node_reliability_agent)
    g.add_node("maintenance_agent", node_maintenance_agent)
    g.add_node("recommendation_agent", node_recommendation_agent)
    g.add_node("output_guardrail", node_output_guardrail)
    g.add_node("rejection", node_rejection)

    g.set_entry_point("input_guardrail")

    g.add_conditional_edges(
        "input_guardrail",
        route_after_input,
        {"valid": "rag_retrieval", "invalid": "rejection"},
    )

    g.add_edge("rag_retrieval", "retrieval_agent")
    g.add_edge("retrieval_agent", "reliability_agent")
    g.add_edge("reliability_agent", "maintenance_agent")
    g.add_edge("maintenance_agent", "recommendation_agent")
    g.add_edge("recommendation_agent", "output_guardrail")
    g.add_edge("output_guardrail", END)
    g.add_edge("rejection", END)

    return g


# Singleton compiled pipeline
_compiled = None


def get_pipeline():
    global _compiled
    if _compiled is None:
        _compiled = _build_graph().compile()
    return _compiled


# ─── Pipeline graph metadata (for frontend visualization) ─────────────────────
GRAPH_SCHEMA = {
    "nodes": [
        {"id": "input_guardrail",     "label": "Input Guardrail",        "type": "guardrail", "model": "GPT-4o mini",  "description": "Validates query relevance, intent & safety"},
        {"id": "rag_retrieval",        "label": "RAG Retrieval",           "type": "retrieval", "model": "FAISS+BM25",  "description": "Hybrid vector + keyword search (α=0.6)"},
        {"id": "retrieval_agent",      "label": "Equipment Retrieval Agent","type": "agent",    "model": "Rule-Based/Claude","description": "Identifies relevant incidents & equipment focus"},
        {"id": "reliability_agent",    "label": "Reliability Analysis Agent","type": "agent",   "model": "Rule-Based/Claude","description": "Detects anomalies & failure patterns"},
        {"id": "maintenance_agent",    "label": "Maintenance Planning Agent","type": "agent",   "model": "Rule-Based/Claude","description": "Generates prioritised maintenance actions"},
        {"id": "recommendation_agent", "label": "Recommendation Agent",    "type": "agent",    "model": "Rule-Based/Claude","description": "Synthesises final recommendations"},
        {"id": "output_guardrail",     "label": "Output Guardrail",        "type": "guardrail", "model": "GPT-4o mini",  "description": "Validates recommendation quality & clinical safety"},
        {"id": "rejection",            "label": "Rejection",               "type": "terminal",  "model": "N/A",          "description": "Returns rejection with reason"},
    ],
    "edges": [
        {"from": "input_guardrail",     "to": "rag_retrieval",        "condition": "VALID"},
        {"from": "input_guardrail",     "to": "rejection",            "condition": "INVALID"},
        {"from": "rag_retrieval",        "to": "retrieval_agent",      "condition": None},
        {"from": "retrieval_agent",      "to": "reliability_agent",    "condition": None},
        {"from": "reliability_agent",    "to": "maintenance_agent",    "condition": None},
        {"from": "maintenance_agent",    "to": "recommendation_agent", "condition": None},
        {"from": "recommendation_agent", "to": "output_guardrail",     "condition": None},
        {"from": "output_guardrail",     "to": "END",                  "condition": None},
        {"from": "rejection",            "to": "END",                  "condition": None},
    ],
}


# ─── Public runner ────────────────────────────────────────────────────────────
def run_langgraph_pipeline(
    query: str,
    filters: Dict = None,
    k: int = 5,
    alpha: float = 0.6,
) -> Dict[str, Any]:
    pipeline = get_pipeline()

    initial: MedEquipState = {
        "query": query,
        "refined_query": query,
        "filters": filters or {},
        "k": k,
        "alpha": alpha,
        "input_guardrail_result": {},
        "is_valid": False,
        "retrieved_docs": [],
        "retrieval_result": {},
        "reliability_result": {},
        "maintenance_result": {},
        "recommendation_result": {},
        "output_guardrail_result": {},
        "error": None,
        "analysis_mode": "LangGraph + GPT-4o mini Guardrails",
        "execution_log": [],
        "node_timings": {},
    }

    final: MedEquipState = pipeline.invoke(initial)
    return dict(final)
