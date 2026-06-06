"""
DeepEval-based RAG Evaluation Module
=====================================
Evaluates maintenance recommendation quality using four standard RAG metrics:

  1. Answer Relevancy   — is the recommendation relevant to the query?
  2. Faithfulness       — does the recommendation stay grounded in retrieved context?
  3. Contextual Precision — are retrieved incidents ranked precisely by relevance?
  4. Contextual Recall  — does the retrieved context cover all facts in the answer?

Falls back to rule-based implementations when LLM APIs are unavailable (no API keys).
Also provides an LLM-as-judge evaluation independent of DeepEval.
"""

import os
import re
from typing import List, Dict, Any, Optional

# ─── DeepEval imports (graceful fallback) ────────────────────────────────────
try:
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        ContextualPrecisionMetric,
        ContextualRecallMetric,
    )
    from deepeval.test_case import LLMTestCase
    DEEPEVAL_AVAILABLE = True
except Exception:
    DEEPEVAL_AVAILABLE = False


def _openai_key() -> Optional[str]:
    key = os.getenv("OPENAI_API_KEY", "")
    return key if key and key != "your-openai-key" else None


# ─── Rule-based metric implementations ───────────────────────────────────────

def _rule_answer_relevancy(query: str, answer: str) -> Dict:
    """Measures how relevant the answer is to the query by keyword overlap."""
    q_tokens = set(re.findall(r'\b\w{4,}\b', query.lower()))
    a_tokens = set(re.findall(r'\b\w{4,}\b', answer.lower()))
    if not q_tokens:
        return {"score": 0.5, "reason": "Could not extract query keywords.", "passed": True}
    overlap = len(q_tokens & a_tokens)
    score = min(1.0, overlap / len(q_tokens) * 1.5)
    return {
        "score": round(score, 3),
        "reason": f"{overlap}/{len(q_tokens)} query keywords found in answer.",
        "passed": score >= 0.5,
    }


def _rule_faithfulness(contexts: List[str], answer: str) -> Dict:
    """Measures if answer statements are supported by retrieved context."""
    if not contexts:
        return {"score": 0.0, "reason": "No context provided.", "passed": False}

    # Extract key entities from answer
    answer_entities = set(re.findall(r'\b[A-Z][a-z]+\b|\b\d+[.]\d+\b|\b\d{3,}\b', answer))
    if not answer_entities:
        return {"score": 0.8, "reason": "No specific claims detected in answer.", "passed": True}

    combined_context = " ".join(contexts).lower()
    supported = sum(1 for e in answer_entities if e.lower() in combined_context)
    score = supported / len(answer_entities)
    return {
        "score": round(score, 3),
        "reason": f"{supported}/{len(answer_entities)} answer entities found in context.",
        "passed": score >= 0.5,
    }


def _rule_contextual_precision(query: str, contexts: List[str]) -> Dict:
    """Measures whether the top-ranked contexts are more relevant than lower ones."""
    if not contexts:
        return {"score": 0.0, "reason": "No context.", "passed": False}

    q_tokens = set(re.findall(r'\b\w{4,}\b', query.lower()))
    scores = []
    for ctx in contexts:
        ctx_tokens = set(re.findall(r'\b\w{4,}\b', ctx.lower()))
        overlap = len(q_tokens & ctx_tokens) / max(1, len(q_tokens))
        scores.append(overlap)

    # Precision@k: are top-ranked docs more relevant? (monotone decreasing ideal)
    if len(scores) < 2:
        return {"score": scores[0] if scores else 0, "reason": "Single context.", "passed": scores[0] >= 0.3 if scores else False}

    # Check if relevance is generally decreasing (i.e. top docs most precise)
    descending_pairs = sum(1 for i in range(len(scores) - 1) if scores[i] >= scores[i + 1])
    precision_order = descending_pairs / (len(scores) - 1)
    avg_score = sum(scores) / len(scores)
    final = 0.6 * avg_score + 0.4 * precision_order
    return {
        "score": round(final, 3),
        "reason": f"Avg relevance {avg_score:.2f}, ranked in decreasing order {precision_order:.2f}.",
        "passed": final >= 0.4,
    }


def _rule_contextual_recall(contexts: List[str], answer: str) -> Dict:
    """Measures whether context covers the facts referenced in the answer."""
    if not contexts:
        return {"score": 0.0, "reason": "No context.", "passed": False}

    # Key claims: numbers, equipment names, failure types in answer
    answer_facts = set(re.findall(
        r'\b(?:MRI|CT Scanner|Ventilator|Infusion Pump|Patient Monitor|Ultrasound|ICU Device|Lab Analyzer|'
        r'Tool Wear|Heat Dissipation|Power Failure|Overstrain|Random Failure|ICU|Emergency|Radiology|'
        r'Cardiology|Neurology|Oncology|Laboratory)\b|\b\d+\.?\d*\s*(?:%|hours?|min|rpm|Nm|K)\b',
        answer, re.IGNORECASE
    ))

    if not answer_facts:
        return {"score": 0.75, "reason": "No specific facts to verify in answer.", "passed": True}

    combined_ctx = " ".join(contexts)
    recalled = sum(1 for f in answer_facts if re.search(re.escape(f), combined_ctx, re.IGNORECASE))
    score = recalled / len(answer_facts)
    return {
        "score": round(score, 3),
        "reason": f"{recalled}/{len(answer_facts)} answer facts found in retrieved context.",
        "passed": score >= 0.5,
    }


# ─── DeepEval-based evaluation ────────────────────────────────────────────────

def _run_deepeval_metrics(
    query: str,
    answer: str,
    contexts: List[str],
    expected_output: Optional[str] = None,
) -> Dict[str, Any]:
    """Run DeepEval metrics with GPT-4o mini as judge."""
    test_case = LLMTestCase(
        input=query,
        actual_output=answer,
        retrieval_context=contexts,
        expected_output=expected_output or answer,
    )

    metrics = {
        "answer_relevancy": AnswerRelevancyMetric(threshold=0.6, verbose_mode=False),
        "faithfulness":     FaithfulnessMetric(threshold=0.6, verbose_mode=False),
        "contextual_precision": ContextualPrecisionMetric(threshold=0.5, verbose_mode=False),
        "contextual_recall":    ContextualRecallMetric(threshold=0.5, verbose_mode=False),
    }

    results = {}
    for name, metric in metrics.items():
        try:
            metric.measure(test_case)
            results[name] = {
                "score": round(metric.score, 3),
                "reason": metric.reason or "",
                "passed": metric.passed,
                "threshold": metric.threshold,
                "mode": "deepeval_llm",
            }
        except Exception as e:
            results[name] = {
                "score": 0.0,
                "reason": f"DeepEval metric error: {e}",
                "passed": False,
                "mode": "error",
            }

    return results


# ─── Public evaluation API ────────────────────────────────────────────────────

def evaluate_recommendation(
    query: str,
    retrieved_docs: List[Dict],
    recommendation: Dict,
) -> Dict[str, Any]:
    """
    Evaluate a maintenance recommendation using RAG quality metrics.

    Uses DeepEval (LLM-powered) when OPENAI_API_KEY is set, otherwise
    falls back to rule-based implementations of the same four metrics.

    Returns a structured evaluation report.
    """
    # Build answer string from recommendation
    answer_parts = [recommendation.get("summary", "")]
    for finding in recommendation.get("key_findings", [])[:5]:
        answer_parts.append(str(finding))
    for action in recommendation.get("action_plan", [])[:5]:
        answer_parts.append(str(action))
    answer = " ".join(p for p in answer_parts if p)

    # Build context strings from retrieved docs
    contexts = [doc.get("document_text", "") for doc in retrieved_docs if doc.get("document_text")]

    if not answer or not contexts:
        return {
            "error": "Insufficient data for evaluation (empty answer or no retrieved context)",
            "metrics": {},
            "overall_score": 0,
            "mode": "skipped",
        }

    # Choose evaluation backend
    mode = "deepeval_llm" if (DEEPEVAL_AVAILABLE and _openai_key()) else "rule_based"

    if mode == "deepeval_llm":
        try:
            metrics = _run_deepeval_metrics(query, answer, contexts)
        except Exception as e:
            mode = "rule_based"
            metrics = {}

    if mode == "rule_based":
        metrics = {
            "answer_relevancy": {**_rule_answer_relevancy(query, answer), "threshold": 0.5, "mode": "rule_based"},
            "faithfulness":     {**_rule_faithfulness(contexts, answer),   "threshold": 0.5, "mode": "rule_based"},
            "contextual_precision": {**_rule_contextual_precision(query, contexts), "threshold": 0.4, "mode": "rule_based"},
            "contextual_recall":    {**_rule_contextual_recall(contexts, answer),   "threshold": 0.5, "mode": "rule_based"},
        }

    # Overall score = average of passed metric scores
    scores = [m["score"] for m in metrics.values() if isinstance(m.get("score"), (int, float))]
    overall = round(sum(scores) / len(scores) * 100, 1) if scores else 0.0
    passed_count = sum(1 for m in metrics.values() if m.get("passed", False))

    return {
        "query": query,
        "metrics": metrics,
        "overall_score": overall,
        "passed_metrics": passed_count,
        "total_metrics": len(metrics),
        "recommendation_confidence": recommendation.get("confidence_score", 0),
        "mode": mode,
        "deepeval_available": DEEPEVAL_AVAILABLE,
        "context_count": len(contexts),
        "answer_length": len(answer.split()),
    }


def build_eval_test_suite(df, sample_size: int = 10) -> List[Dict]:
    """
    Build a test suite of representative maintenance scenarios for offline evaluation.
    Returns a list of {query, expected_equipment, expected_failure_type} dicts.
    """
    import random
    random.seed(42)
    failures = df[df["machine_failure"] == 1].to_dict(orient="records")
    sample = random.sample(failures, min(sample_size, len(failures)))
    suite = []
    for rec in sample:
        eq = rec.get("equipment_type", "equipment")
        ft = rec.get("failure_type", "failure")
        unit = rec.get("hospital_unit", "unit")
        severity = rec.get("severity", "")
        suite.append({
            "query": f"{severity} {ft.lower()} detected in {eq} at {unit}",
            "expected_equipment": eq,
            "expected_failure_type": ft,
            "expected_unit": unit,
            "ground_truth_record_id": rec.get("record_id"),
        })
    return suite
