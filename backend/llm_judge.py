"""
LLM-as-Judge for Medical Equipment Maintenance Validation
==========================================================
Independent LLM judge that evaluates maintenance recommendations on a structured
rubric — separate from the output guardrail (which checks safety/completeness).

The judge scores on four clinical/engineering dimensions with explicit reasoning:
  1. Clinical Safety       (0–25): Are recommendations safe for patients and staff?
  2. Technical Accuracy    (0–25): Are technical details (temp, wear, RPM) correct?
  3. Actionability         (0–25): Are actions concrete and implementable?
  4. Evidence Basis        (0–25): Is the recommendation grounded in retrieved incidents?

Total: 0–100. Rule-based fallback activates when no LLM API is available.
"""

import json
import os
import re
from typing import Dict, Any, List, Optional

# ─── API key helpers ──────────────────────────────────────────────────────────

def _openai_key() -> Optional[str]:
    key = os.getenv("OPENAI_API_KEY", "")
    return key if key and key != "your-openai-key" else None


def _claude_key() -> Optional[str]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return key if key and key != "your-anthropic-key" else None


# ─── Rule-based judge fallback ────────────────────────────────────────────────

def _rule_judge(
    query: str,
    recommendation: Dict,
    retrieved_docs: List[Dict],
) -> Dict[str, Any]:
    """Deterministic rubric-based scoring when no LLM API is available."""

    summary     = recommendation.get("summary", "")
    root_cause  = recommendation.get("root_cause", "")
    key_findings = recommendation.get("key_findings", [])
    action_plan = recommendation.get("action_plan", [])
    risk        = recommendation.get("risk_assessment", "")
    confidence  = recommendation.get("confidence_score", 0)

    # ── 1. Clinical Safety (0–25) ───────────────────────────────────────────
    safety_score = 15  # baseline
    safety_notes = []

    unsafe_patterns = [
        r"ignore\s+(safety|alarm|alert|warning)",
        r"disable\s+\w+\s*(alarm|sensor|monitor)",
        r"bypass\s+(safety|limit|check|protocol)",
        r"continue\s+(operation|running)\s+despite\s+(failure|alarm|warning)",
    ]
    text_to_check = f"{summary} {root_cause} {' '.join(action_plan)}".lower()
    if any(re.search(p, text_to_check) for p in unsafe_patterns):
        safety_score -= 15
        safety_notes.append("Potentially unsafe recommendation detected.")
    else:
        safety_notes.append("No unsafe patterns detected.")

    # Safety-conscious language boosts
    safety_keywords = ["isolate", "shutdown", "decommission", "patient safety", "do not use", "out of service", "biomedical"]
    if any(kw in text_to_check for kw in safety_keywords):
        safety_score = min(25, safety_score + 5)
        safety_notes.append("Safety-conscious language found.")

    if risk in ("Critical", "High") and action_plan:
        safety_score = min(25, safety_score + 5)
        safety_notes.append("High/Critical risk with action plan present.")

    # ── 2. Technical Accuracy (0–25) ─────────────────────────────────────────
    tech_score = 10
    tech_notes = []

    # Check if technical values from docs appear in recommendation
    doc_values = set()
    for doc in retrieved_docs[:3]:
        air_t = doc.get("air_temperature_k") or doc.get("Air temperature [K]")
        wear  = doc.get("tool_wear_min")    or doc.get("Tool wear [min]")
        rpm   = doc.get("rotational_speed_rpm") or doc.get("Rotational speed [rpm]")
        if air_t: doc_values.add(str(round(float(air_t), 0)))
        if wear:  doc_values.add(str(int(wear)))
        if rpm:   doc_values.add(str(int(rpm)))

    all_text = f"{summary} {root_cause} {' '.join(key_findings)}".lower()
    matched = sum(1 for v in doc_values if v in all_text)
    if doc_values:
        tech_score += int(matched / max(1, len(doc_values)) * 10)
        tech_notes.append(f"Referenced {matched}/{len(doc_values)} technical values from incidents.")
    else:
        tech_notes.append("No specific technical values to verify.")
        tech_score += 5

    # Reward correct failure-type terminology
    failure_terms = ["tool wear", "heat dissipation", "power failure", "overstrain", "random failure",
                     "temperature", "torque", "rpm", "rotational speed", "calibration"]
    term_matches = sum(1 for t in failure_terms if t in all_text)
    tech_score = min(25, tech_score + min(5, term_matches))
    tech_notes.append(f"{term_matches} technical maintenance terms present.")

    # ── 3. Actionability (0–25) ──────────────────────────────────────────────
    action_score = 5
    action_notes = []

    if len(action_plan) >= 3:
        action_score += 10
    elif len(action_plan) >= 1:
        action_score += 5
    action_notes.append(f"{len(action_plan)} action steps provided.")

    # Check for concrete verbs
    action_verbs = ["inspect", "replace", "calibrate", "schedule", "contact", "monitor",
                    "shutdown", "repair", "test", "document", "escalate", "notify", "check"]
    action_text = " ".join(action_plan).lower()
    verb_count = sum(1 for v in action_verbs if v in action_text)
    action_score = min(25, action_score + min(10, verb_count * 2))
    action_notes.append(f"{verb_count} concrete action verbs found.")

    # ── 4. Evidence Basis (0–25) ──────────────────────────────────────────────
    evidence_score = 5
    evidence_notes = []

    n_docs = len(retrieved_docs)
    evidence_score += min(10, n_docs * 2)
    evidence_notes.append(f"{n_docs} incidents retrieved as evidence.")

    # Reward citing specific equipment IDs or types
    eq_ids = [doc.get("equipment_id", "") for doc in retrieved_docs]
    eq_types = list({doc.get("equipment_type", "") for doc in retrieved_docs})
    if any(eq_id in all_text for eq_id in eq_ids if eq_id):
        evidence_score = min(25, evidence_score + 5)
        evidence_notes.append("Specific equipment IDs referenced.")
    if eq_types and any(et.lower() in all_text for et in eq_types if et):
        evidence_score = min(25, evidence_score + 5)
        evidence_notes.append("Equipment types from evidence mentioned.")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    total = safety_score + tech_score + action_score + evidence_score
    total = max(0, min(100, total))

    return {
        "total_score": total,
        "verdict": (
            "Excellent" if total >= 85 else
            "Good"      if total >= 70 else
            "Adequate"  if total >= 55 else
            "Poor"
        ),
        "dimension_scores": {
            "clinical_safety":    {"score": safety_score,  "max": 25, "notes": safety_notes},
            "technical_accuracy": {"score": tech_score,    "max": 25, "notes": tech_notes},
            "actionability":      {"score": action_score,  "max": 25, "notes": action_notes},
            "evidence_basis":     {"score": evidence_score,"max": 25, "notes": evidence_notes},
        },
        "reasoning": (
            f"Rule-based assessment: Safety={safety_score}/25, "
            f"Technical={tech_score}/25, Actionability={action_score}/25, "
            f"Evidence={evidence_score}/25. Total={total}/100."
        ),
        "approved": total >= 55,
        "judge_mode": "rule_based",
    }


# ─── LLM judge (GPT-4o mini) ──────────────────────────────────────────────────

def _llm_judge_openai(
    query: str,
    recommendation: Dict,
    retrieved_docs: List[Dict],
) -> Dict[str, Any]:
    import openai

    client = openai.OpenAI(api_key=_openai_key())

    # Build context summary from top docs
    context_lines = []
    for i, doc in enumerate(retrieved_docs[:5]):
        context_lines.append(
            f"Incident {i+1}: {doc.get('equipment_type','?')} | "
            f"{doc.get('failure_type','No Failure')} | "
            f"Severity: {doc.get('severity','?')} | "
            f"Air Temp: {doc.get('air_temperature_k','?')}K | "
            f"Tool Wear: {doc.get('tool_wear_min','?')}min"
        )
    context_summary = "\n".join(context_lines) if context_lines else "No incidents retrieved."

    rec_text = json.dumps({
        "summary":      recommendation.get("summary", "")[:400],
        "root_cause":   recommendation.get("root_cause", "")[:200],
        "risk":         recommendation.get("risk_assessment", ""),
        "confidence":   recommendation.get("confidence_score", 0),
        "key_findings": recommendation.get("key_findings", [])[:5],
        "action_plan":  recommendation.get("action_plan", [])[:6],
    }, indent=2)

    system_prompt = """You are an expert biomedical engineer and LLM judge evaluating AI-generated medical equipment maintenance recommendations.

Score the recommendation on FOUR dimensions (0-25 each), total 0-100:

1. CLINICAL_SAFETY (0-25): Are the recommendations safe for patients and hospital staff?
   - 25: All recommendations are clinically safe; hazardous operations are flagged appropriately
   - 0: Recommendation could endanger patients (e.g. continue using failed equipment)

2. TECHNICAL_ACCURACY (0-25): Are technical details correct and evidence-based?
   - 25: Technical values (temperatures, torque, wear) are correctly interpreted and cited
   - 0: Technical claims are fabricated or contradict the retrieved incident data

3. ACTIONABILITY (0-25): Are the recommended actions concrete and implementable?
   - 25: Actions are specific, prioritized, and can be immediately acted upon
   - 0: Vague or contradictory actions that cannot be implemented

4. EVIDENCE_BASIS (0-25): Is the recommendation grounded in retrieved incidents?
   - 25: All claims are traceable to specific incidents; no hallucinated data
   - 0: Ignores retrieved incidents entirely or contradicts them

Respond ONLY with valid JSON, no extra text."""

    user_prompt = f"""QUERY: {query}

RETRIEVED INCIDENTS:
{context_summary}

RECOMMENDATION TO JUDGE:
{rec_text}

Return JSON:
{{
  "clinical_safety":    {{"score": <0-25>, "reasoning": "<1-2 sentences>"}},
  "technical_accuracy": {{"score": <0-25>, "reasoning": "<1-2 sentences>"}},
  "actionability":      {{"score": <0-25>, "reasoning": "<1-2 sentences>"}},
  "evidence_basis":     {{"score": <0-25>, "reasoning": "<1-2 sentences>"}},
  "total_score":        <0-100>,
  "verdict":            "<Excellent|Good|Adequate|Poor>",
  "approved":           <true|false>,
  "overall_reasoning":  "<2-3 sentences>"
}}"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=600,
        temperature=0.1,
    )

    raw = json.loads(resp.choices[0].message.content)

    # Normalise into canonical structure
    total = raw.get("total_score", 0)
    return {
        "total_score": int(total),
        "verdict": raw.get("verdict", "Adequate"),
        "dimension_scores": {
            "clinical_safety":    {"score": raw.get("clinical_safety",    {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("clinical_safety",    {}).get("reasoning", "")]},
            "technical_accuracy": {"score": raw.get("technical_accuracy", {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("technical_accuracy", {}).get("reasoning", "")]},
            "actionability":      {"score": raw.get("actionability",      {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("actionability",      {}).get("reasoning", "")]},
            "evidence_basis":     {"score": raw.get("evidence_basis",     {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("evidence_basis",     {}).get("reasoning", "")]},
        },
        "reasoning": raw.get("overall_reasoning", ""),
        "approved": raw.get("approved", total >= 55),
        "judge_mode": "gpt-4o-mini",
    }


# ─── Claude-based judge (fallback if no OpenAI but Claude available) ──────────

def _llm_judge_claude(
    query: str,
    recommendation: Dict,
    retrieved_docs: List[Dict],
) -> Dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=_claude_key())

    context_lines = []
    for i, doc in enumerate(retrieved_docs[:5]):
        context_lines.append(
            f"Incident {i+1}: {doc.get('equipment_type','?')} | "
            f"{doc.get('failure_type','No Failure')} | Severity: {doc.get('severity','?')}"
        )
    context_summary = "\n".join(context_lines) or "No incidents retrieved."

    rec_text = (
        f"Summary: {recommendation.get('summary','')[:300]}\n"
        f"Root cause: {recommendation.get('root_cause','')[:150]}\n"
        f"Risk: {recommendation.get('risk_assessment','')}\n"
        f"Actions: {'; '.join(recommendation.get('action_plan',[])[:4])}"
    )

    prompt = f"""<query>{query}</query>
<context>{context_summary}</context>
<recommendation>{rec_text}</recommendation>

You are an LLM judge evaluating a medical equipment maintenance recommendation.
Score these four dimensions (0-25 each):
1. clinical_safety (patient/staff safety)
2. technical_accuracy (correct technical values)
3. actionability (concrete, implementable)
4. evidence_basis (grounded in retrieved incidents)

Respond ONLY with this JSON:
{{
  "clinical_safety": {{"score": 0-25, "reasoning": "..."}},
  "technical_accuracy": {{"score": 0-25, "reasoning": "..."}},
  "actionability": {{"score": 0-25, "reasoning": "..."}},
  "evidence_basis": {{"score": 0-25, "reasoning": "..."}},
  "total_score": 0-100,
  "verdict": "Excellent|Good|Adequate|Poor",
  "approved": true|false,
  "overall_reasoning": "..."
}}"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()

    # Extract JSON from response
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        raw = json.loads(match.group())
    else:
        raise ValueError("No JSON in Claude response")

    total = raw.get("total_score", 0)
    return {
        "total_score": int(total),
        "verdict": raw.get("verdict", "Adequate"),
        "dimension_scores": {
            "clinical_safety":    {"score": raw.get("clinical_safety",    {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("clinical_safety",    {}).get("reasoning", "")]},
            "technical_accuracy": {"score": raw.get("technical_accuracy", {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("technical_accuracy", {}).get("reasoning", "")]},
            "actionability":      {"score": raw.get("actionability",      {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("actionability",      {}).get("reasoning", "")]},
            "evidence_basis":     {"score": raw.get("evidence_basis",     {}).get("score", 0), "max": 25,
                                   "notes": [raw.get("evidence_basis",     {}).get("reasoning", "")]},
        },
        "reasoning": raw.get("overall_reasoning", ""),
        "approved": raw.get("approved", total >= 55),
        "judge_mode": "claude-sonnet-4-6",
    }


# ─── Public API ───────────────────────────────────────────────────────────────

def run_llm_judge(
    query: str,
    recommendation: Dict,
    retrieved_docs: List[Dict],
) -> Dict[str, Any]:
    """
    Run the LLM-as-judge evaluation on a maintenance recommendation.

    Priority order:
      1. GPT-4o mini  (if OPENAI_API_KEY set)
      2. Claude       (if ANTHROPIC_API_KEY set)
      3. Rule-based   (always available)
    """
    if _openai_key():
        try:
            return _llm_judge_openai(query, recommendation, retrieved_docs)
        except Exception as e:
            print(f"[llm_judge] OpenAI failed: {e}, trying Claude...")

    if _claude_key():
        try:
            return _llm_judge_claude(query, recommendation, retrieved_docs)
        except Exception as e:
            print(f"[llm_judge] Claude failed: {e}, falling back to rule-based...")

    return _rule_judge(query, recommendation, retrieved_docs)
