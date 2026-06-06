"""
GPT-4o mini Guardrail System
Input guardrail: validates query relevance, intent, safety
Output guardrail: validates recommendation quality and clinical safety
Falls back to intelligent rule-based checks when OPENAI_API_KEY is absent.
"""

import os
import json
import re
from typing import Dict, Optional

# ─── OpenAI client ────────────────────────────────────────────────────────────
def _openai_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key if key and key != "your_openai_api_key_here" else None


def _get_openai() -> Optional[object]:
    key = _openai_key()
    if not key:
        return None
    try:
        from openai import OpenAI
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
        return OpenAI(api_key=key, base_url=base_url)
    except Exception:
        return None


# ─── Domain vocabulary ────────────────────────────────────────────────────────
MEDICAL_EQUIPMENT = {
    "mri", "ct", "scanner", "ventilator", "infusion", "pump", "monitor",
    "ultrasound", "icu", "device", "equipment", "machine", "sensor",
    "defibrillator", "ecg", "ekg", "x-ray", "radiolog", "imaging",
    "diagnostic", "biomedical", "clinical", "hospital", "patient",
    "sterilizer", "autoclave", "endoscope", "catheter", "pacemaker",
    "anesthesia", "respirator", "nebulizer", "incubator",
}
MAINTENANCE_KEYWORDS = {
    "maintenance", "failure", "repair", "calibration", "alert", "anomaly",
    "reliability", "downtime", "malfunction", "error", "fault", "breakdown",
    "wear", "thermal", "temperature", "overheating", "vibration", "noise",
    "preventive", "scheduled", "inspect", "service", "replacement",
    "warranty", "incident", "issue", "problem", "concern", "pattern",
    "trend", "recurring", "intermittent", "degradation", "drift",
}
HARMFUL_PATTERNS = [
    r"\b(hack|exploit|bypass|disable|sabotage|damage|destroy)\b",
    r"\b(kill|harm|hurt|injure|death|poison)\b",
    r"ignore\s+(safety|protocol|alarm|alert)",
    r"override\s+(safety|limit|threshold)",
]
INTENT_MAP = {
    "failure": "equipment_failure",
    "anomaly": "anomaly_detection",
    "alert": "anomaly_detection",
    "preventive": "maintenance_planning",
    "scheduled": "maintenance_planning",
    "reliability": "reliability_analysis",
    "trend": "reliability_analysis",
    "pattern": "reliability_analysis",
}


# ─── Rule-based fallbacks ──────────────────────────────────────────────────────
def _rule_input_guardrail(query: str) -> Dict:
    q = query.lower()

    # Harmful check
    for pat in HARMFUL_PATTERNS:
        if re.search(pat, q, re.IGNORECASE):
            return {
                "is_valid": False,
                "reason": "Query contains potentially harmful intent and cannot be processed.",
                "refined_query": query,
                "intent": "harmful",
                "equipment_type": None,
                "urgency": "low",
                "guardrail_mode": "rule_based",
            }

    # Relevance check
    eq_match = any(kw in q for kw in MEDICAL_EQUIPMENT)
    maint_match = any(kw in q for kw in MAINTENANCE_KEYWORDS)

    if not (eq_match or maint_match):
        return {
            "is_valid": False,
            "reason": "Query does not appear to relate to medical equipment or maintenance topics.",
            "refined_query": query,
            "intent": "off_topic",
            "equipment_type": None,
            "urgency": "low",
            "guardrail_mode": "rule_based",
        }

    # Determine intent
    intent = "general_inquiry"
    for kw, intent_label in INTENT_MAP.items():
        if kw in q:
            intent = intent_label
            break

    # Detect equipment type
    eq_type = None
    for eq in ["mri", "ct scanner", "ct", "ventilator", "infusion pump", "patient monitor",
               "ultrasound", "icu device", "lab analyzer", "monitor"]:
        if eq in q:
            eq_type = eq.title()
            break

    # Urgency
    urgency = "routine"
    if any(w in q for w in ["critical", "urgent", "emergency", "down", "failure", "immediate"]):
        urgency = "immediate"
    elif any(w in q for w in ["low", "minor", "slight"]):
        urgency = "low"

    # Query refinement - append context for specificity
    refined = query.strip()
    if eq_type and eq_type.lower() not in refined.lower():
        pass  # query already specific enough
    if not any(w in q for w in ["maintenance", "reliability", "analysis"]):
        refined = f"{refined} - equipment maintenance and reliability analysis"

    return {
        "is_valid": True,
        "reason": "Query is relevant to medical equipment maintenance.",
        "refined_query": refined,
        "intent": intent,
        "equipment_type": eq_type,
        "urgency": urgency,
        "guardrail_mode": "rule_based",
    }


def _rule_output_guardrail(query: str, recommendation: Dict) -> Dict:
    summary = str(recommendation.get("summary", ""))
    action_plan = recommendation.get("action_plan", [])
    key_findings = recommendation.get("key_findings", [])
    risk = recommendation.get("risk_assessment", "Unknown")

    issues = []
    quality_score = 60  # baseline

    # Check completeness
    if not action_plan:
        issues.append("No action plan provided")
        quality_score -= 15
    elif len(action_plan) >= 3:
        quality_score += 10

    if not key_findings:
        issues.append("No key findings listed")
        quality_score -= 10
    elif len(key_findings) >= 3:
        quality_score += 10

    if not summary or len(summary) < 50:
        issues.append("Summary is too brief")
        quality_score -= 10
    else:
        quality_score += 10

    if recommendation.get("confidence_score", 0) >= 70:
        quality_score += 10

    if risk in ("High", "Critical") and not action_plan:
        issues.append("High/Critical risk identified but no urgent actions specified")
        quality_score -= 20

    # Safety check on action plan
    safety_rating = "safe"
    for action in action_plan:
        if any(re.search(p, action, re.IGNORECASE) for p in HARMFUL_PATTERNS):
            issues.append(f"Potentially unsafe recommendation: {action[:60]}")
            safety_rating = "caution"
            quality_score -= 30

    quality_score = max(0, min(100, quality_score))

    return {
        "is_safe": safety_rating != "unsafe",
        "quality_score": quality_score,
        "issues": issues if issues else ["No issues found"],
        "safety_rating": safety_rating,
        "approved_recommendation": summary[:200] if summary else "Recommendation generated.",
        "completeness_check": {
            "has_summary": bool(summary),
            "has_action_plan": bool(action_plan),
            "has_key_findings": bool(key_findings),
            "has_risk_assessment": bool(risk),
        },
        "guardrail_mode": "rule_based",
    }


# ─── GPT-4o mini guardrails ──────────────────────────────────────────────────
_INPUT_SYSTEM = """You are a medical equipment maintenance system input guardrail.
Validate if the query is appropriate for a hospital biomedical engineering intelligence system.

Return JSON only with this exact schema:
{
  "is_valid": true|false,
  "reason": "one sentence explanation",
  "refined_query": "improved/clarified version of the original query",
  "intent": "equipment_failure|maintenance_planning|anomaly_detection|reliability_analysis|general_inquiry|off_topic|harmful",
  "equipment_type": "detected equipment type or null",
  "urgency": "immediate|routine|low"
}

VALID queries: medical equipment failures, maintenance issues, anomalies, reliability trends, ICU/hospital device problems.
INVALID queries: off-topic requests, harmful/sabotage intent, non-medical content."""

_OUTPUT_SYSTEM = """You are a medical equipment recommendation quality validator and safety checker.
Review the AI-generated maintenance recommendation for appropriateness and clinical safety.

Return JSON only with this exact schema:
{
  "is_safe": true|false,
  "quality_score": 0-100,
  "issues": ["list of issues or 'No issues found'"],
  "safety_rating": "safe|caution|unsafe",
  "approved_recommendation": "brief approved summary of the recommendation",
  "completeness_check": {
    "has_summary": true|false,
    "has_action_plan": true|false,
    "has_key_findings": true|false,
    "has_risk_assessment": true|false
  }
}

Score 90-100: Excellent - comprehensive, safe, actionable
Score 70-89: Good - mostly complete with minor gaps
Score 50-69: Adequate - usable but missing some elements
Score <50: Poor - incomplete or potentially unsafe"""


def _llm_input_guardrail(client, query: str) -> Dict:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _INPUT_SYSTEM},
                {"role": "user", "content": f"Validate this query: {query}"},
            ],
        )
        result = json.loads(resp.choices[0].message.content)
        result["guardrail_mode"] = "gpt-4o-mini"
        return result
    except Exception as e:
        print(f"GPT-4o-mini input guardrail error: {e}")
        fallback = _rule_input_guardrail(query)
        fallback["guardrail_mode"] = "rule_based_fallback"
        return fallback


def _llm_output_guardrail(client, query: str, recommendation: Dict) -> Dict:
    try:
        payload = {
            "query": query,
            "summary": recommendation.get("summary", ""),
            "risk_assessment": recommendation.get("risk_assessment", ""),
            "action_plan": recommendation.get("action_plan", [])[:5],
            "key_findings": recommendation.get("key_findings", [])[:5],
            "confidence_score": recommendation.get("confidence_score", 0),
        }
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _OUTPUT_SYSTEM},
                {"role": "user", "content": f"Validate this recommendation:\n{json.dumps(payload)}"},
            ],
        )
        result = json.loads(resp.choices[0].message.content)
        result["guardrail_mode"] = "gpt-4o-mini"
        return result
    except Exception as e:
        print(f"GPT-4o-mini output guardrail error: {e}")
        fallback = _rule_output_guardrail(query, recommendation)
        fallback["guardrail_mode"] = "rule_based_fallback"
        return fallback


# ─── Public API ───────────────────────────────────────────────────────────────
def run_input_guardrail(query: str) -> Dict:
    client = _get_openai()
    if client:
        return _llm_input_guardrail(client, query)
    return _rule_input_guardrail(query)


def run_output_guardrail(query: str, recommendation: Dict) -> Dict:
    client = _get_openai()
    if client:
        return _llm_output_guardrail(client, query, recommendation)
    return _rule_output_guardrail(query, recommendation)
