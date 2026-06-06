import os
import json
from typing import List, Dict, Any, Optional
from collections import Counter

MODEL = "claude-sonnet-4-6"


def _api_key_available() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(key) and key not in ("your_anthropic_api_key_here", "")


def _get_client():
    if not _api_key_available():
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    except Exception:
        return None


def _call_claude(client, system: str, user: str, max_tokens: int = 1024) -> Optional[str]:
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    return None


# ─── Intelligent Rule-Based Fallbacks ─────────────────────────────────────────

def _rule_retrieval(query: str, docs: List[Dict]) -> Dict:
    query_lower = query.lower()
    equipment_types = list({d.get("equipment_type", "") for d in docs})
    units = list({d.get("hospital_unit", "") for d in docs})

    relevant = []
    for d in docs[:5]:
        reason = f"Relevance score {d.get('relevance_score', 0):.3f}"
        if d.get("machine_failure") == 1:
            reason = f"FAILURE detected ({d.get('failure_type')}) - {reason}"
        relevant.append({"id": d.get("equipment_id"), "type": d.get("equipment_type"), "reason": reason})

    intent = "Investigating equipment reliability and maintenance patterns"
    if any(w in query_lower for w in ["fail", "break", "down", "error"]):
        intent = "Identifying equipment failures and root causes"
    elif any(w in query_lower for w in ["warn", "alert", "anomal"]):
        intent = "Analyzing equipment anomalies and warning signals"
    elif any(w in query_lower for w in ["preventiv", "schedul", "maintain"]):
        intent = "Planning preventive maintenance activities"

    return {
        "relevant_incidents": relevant,
        "query_intent": intent,
        "equipment_focus": equipment_types,
        "hospital_units_affected": units,
        "time_period": "Historical maintenance records",
    }


def _rule_reliability(docs: List[Dict]) -> Dict:
    total = len(docs)
    failures = [d for d in docs if d.get("machine_failure") == 1]
    failure_rate = round(len(failures) / total * 100, 1) if total > 0 else 0
    reliability_score = max(0, round(100 - failure_rate * 1.8, 1))

    wear_vals = [d.get("tool_wear_min", 0) for d in docs]
    avg_wear = round(sum(wear_vals) / max(len(wear_vals), 1), 1)
    max_wear = max(wear_vals) if wear_vals else 0

    temps = [d.get("air_temperature_k", 298) for d in docs]
    avg_temp = round(sum(temps) / max(len(temps), 1), 2)

    failure_types = Counter(d.get("failure_type", "") for d in failures)
    severity_counts = Counter(d.get("severity", "") for d in docs)

    anomalies = []
    if avg_wear > 180:
        anomalies.append(f"High average tool wear: {avg_wear} min (threshold: 180 min)")
    if max_wear > 240:
        anomalies.append(f"Critical tool wear detected: {max_wear} min on some equipment")
    if avg_temp > 302:
        anomalies.append(f"Elevated operating temperature: {avg_temp}K (normal: <302K)")
    if failure_rate > 20:
        anomalies.append(f"High failure rate: {failure_rate}% (threshold: 20%)")
    if severity_counts.get("Critical", 0) > 0:
        anomalies.append(f"{severity_counts['Critical']} Critical severity incidents detected")
    if not anomalies:
        anomalies.append("No critical anomalies detected in retrieved incidents")

    patterns = []
    for ft, cnt in failure_types.most_common():
        if ft and ft != "No Failure":
            pct = round(cnt / max(len(failures), 1) * 100, 0)
            patterns.append(f"{ft}: {cnt} occurrences ({pct}% of failures)")

    high_risk = [d.get("equipment_id") for d in docs
                 if d.get("machine_failure") == 1 and d.get("severity") in ("Critical", "High")][:5]

    downtime_total = sum(d.get("downtime_hours", 0) for d in failures)
    cost_total = sum(d.get("maintenance_cost_usd", 0) for d in failures)

    return {
        "failure_rate": failure_rate,
        "reliability_score": reliability_score,
        "anomalies": anomalies,
        "failure_patterns": patterns if patterns else ["No failure patterns detected"],
        "high_risk_equipment": high_risk,
        "temperature_analysis": f"Average operating temperature: {avg_temp}K (normal range: 296-302K)",
        "wear_analysis": f"Average tool wear: {avg_wear} min, Max: {max_wear} min (threshold: 200 min)",
        "severity_breakdown": dict(severity_counts),
        "total_downtime_hours": round(downtime_total, 1),
        "total_cost_usd": cost_total,
    }


def _rule_maintenance(docs: List[Dict], reliability: Dict) -> Dict:
    failures = [d for d in docs if d.get("machine_failure") == 1]
    failure_rate = reliability.get("failure_rate", 0)
    reliability_score = reliability.get("reliability_score", 0)
    high_risk = reliability.get("high_risk_equipment", [])
    anomalies = reliability.get("anomalies", [])

    immediate = []
    scheduled = []
    preventive = []

    if high_risk:
        immediate.append(f"Immediately inspect high-risk equipment: {', '.join(high_risk[:3])}")
    if reliability.get("wear_analysis", "").find("Max:") != -1:
        max_wear = reliability["wear_analysis"].split("Max:")[1].split("min")[0].strip()
        try:
            if float(max_wear) > 200:
                immediate.append(f"Replace components with tool wear > 200 min (max detected: {max_wear} min)")
        except ValueError:
            pass
    if "Elevated operating temperature" in str(anomalies):
        immediate.append("Service cooling systems on overheating equipment - thermal management failure risk")
    if failure_rate > 15:
        immediate.append(f"Conduct emergency audit across all affected equipment (failure rate: {failure_rate}%)")

    scheduled.append("Schedule full diagnostic cycle for equipment with >150 min tool wear")
    scheduled.append("Calibrate sensors and monitoring systems on all affected units")
    scheduled.append("Inspect power supply units for equipment with Power Failure history")
    scheduled.append("Review and update preventive maintenance intervals based on failure patterns")

    preventive.append("Implement real-time tool wear monitoring with automated alerts at 150-min threshold")
    preventive.append("Install temperature sensors to trigger alerts above 302K operating temperature")
    preventive.append("Establish predictive maintenance schedule based on MTBF analysis")
    preventive.append("Create equipment reliability database for trend analysis and early warning")
    preventive.append("Train biomedical technicians on early failure identification protocols")

    downtime_reduction = "15-25%" if reliability_score > 60 else "30-45%"

    return {
        "immediate_actions": immediate if immediate else ["Conduct baseline inspection of all retrieved equipment"],
        "scheduled_maintenance": scheduled,
        "preventive_measures": preventive,
        "priority_order": ["Critical/High severity failures", "Wear-based preventive replacement", "Thermal management", "Predictive maintenance setup"],
        "estimated_downtime_reduction": downtime_reduction,
        "maintenance_urgency": "Critical" if failure_rate > 25 else "High" if failure_rate > 15 else "Medium",
    }


def _rule_recommendation(query: str, docs: List[Dict], retrieval: Dict, reliability: Dict, maintenance: Dict) -> Dict:
    failure_rate = reliability.get("failure_rate", 0)
    reliability_score = reliability.get("reliability_score", 0)
    high_risk = reliability.get("high_risk_equipment", [])
    patterns = reliability.get("failure_patterns", [])
    failures = [d for d in docs if d.get("machine_failure") == 1]

    risk_level = "Critical" if failure_rate > 30 else "High" if failure_rate > 15 else "Medium" if failure_rate > 5 else "Low"
    confidence = min(95, 60 + len(docs) * 3 + len(failures) * 2)

    equipment_types = retrieval.get("equipment_focus", [])
    units = retrieval.get("hospital_units_affected", [])

    root_cause_parts = []
    if patterns and patterns[0] != "No failure patterns detected":
        root_cause_parts.append(f"Primary failure mode: {patterns[0]}")
    wear_info = reliability.get("wear_analysis", "")
    if "High average" in str(reliability.get("anomalies", [])):
        root_cause_parts.append("Accelerated component wear exceeding maintenance thresholds")
    temp_info = reliability.get("temperature_analysis", "")
    if "Elevated" in str(reliability.get("anomalies", [])):
        root_cause_parts.append("Thermal management issues contributing to equipment stress")

    root_cause = ". ".join(root_cause_parts) if root_cause_parts else "Mixed failure modes detected requiring comprehensive diagnostic evaluation"

    key_findings = [
        f"Analyzed {len(docs)} maintenance incidents with {len(failures)} failures ({failure_rate}% failure rate)",
        f"Equipment reliability score: {reliability_score}/100",
    ]
    if high_risk:
        key_findings.append(f"High-risk equipment identified: {', '.join(high_risk[:3])}")
    if patterns and patterns[0] != "No failure patterns detected":
        key_findings.append(f"Dominant failure pattern: {patterns[0]}")
    key_findings.append(f"Estimated downtime reduction with recommended actions: {maintenance.get('estimated_downtime_reduction','25-35%')}")

    action_plan = []
    for a in (maintenance.get("immediate_actions") or [])[:2]:
        action_plan.append(f"[Immediate] {a}")
    for a in (maintenance.get("scheduled_maintenance") or [])[:2]:
        action_plan.append(f"[7-14 days] {a}")
    for a in (maintenance.get("preventive_measures") or [])[:2]:
        action_plan.append(f"[30 days] {a}")

    eq_status = {}
    for eq_type in equipment_types:
        eq_docs = [d for d in docs if d.get("equipment_type") == eq_type]
        eq_failures = [d for d in eq_docs if d.get("machine_failure") == 1]
        if eq_docs:
            eq_rate = round(len(eq_failures) / len(eq_docs) * 100, 1)
            eq_status[eq_type] = f"{eq_rate}% failure rate ({len(eq_docs)} records)"

    downtime = reliability.get("total_downtime_hours", 0)
    cost = reliability.get("total_cost_usd", 0)

    summary = (
        f"Analysis of {len(docs)} maintenance incidents across {len(equipment_types)} equipment type(s) "
        f"in {len(units)} hospital unit(s) reveals a {failure_rate}% failure rate with {risk_level.lower()} overall risk. "
        f"Total impact: {downtime}h downtime and ${cost:,} maintenance cost. "
        f"Immediate action required for {len(high_risk)} high-risk equipment items."
    )

    return {
        "summary": summary,
        "root_cause": root_cause,
        "confidence_score": confidence,
        "key_findings": key_findings,
        "action_plan": action_plan,
        "risk_assessment": risk_level,
        "equipment_status": eq_status,
        "follow_up": maintenance.get("preventive_measures", [])[:3],
        "api_mode": "rule_based" if not _api_key_available() else "claude_ai",
    }


# ─── Agents ───────────────────────────────────────────────────────────────────

def equipment_retrieval_agent(query: str, docs: List[Dict], client) -> Dict:
    if client is None:
        return _rule_retrieval(query, docs)

    system = """You are the Equipment Retrieval Agent for a hospital biomedical engineering system.
Analyze the retrieved maintenance incidents and identify the most relevant ones.
Return valid JSON only with keys: relevant_incidents (list), query_intent, equipment_focus (list), hospital_units_affected (list), time_period."""

    context = json.dumps([{k: d.get(k) for k in ["equipment_id","equipment_type","hospital_unit","failure_type","severity","relevance_score","timestamp","technician_notes"]} for d in docs[:8]], indent=2)
    user = f'Engineer Query: "{query}"\n\nRetrieved Records:\n{context}\n\nReturn JSON analysis.'

    result = _extract_json(_call_claude(client, system, user, 800))
    return result if result else _rule_retrieval(query, docs)


def reliability_analysis_agent(query: str, docs: List[Dict], retrieval: Dict, client) -> Dict:
    fallback = _rule_reliability(docs)
    if client is None:
        return fallback

    failure_docs = [d for d in docs if d.get("machine_failure") == 1]
    total = len(docs)
    stats = {
        "total_incidents": total,
        "failures": len(failure_docs),
        "failure_rate_pct": round(len(failure_docs)/max(total,1)*100,1),
        "avg_tool_wear_min": round(sum(d.get("tool_wear_min",0) for d in docs)/max(total,1),1),
        "avg_temp_k": round(sum(d.get("air_temperature_k",298) for d in docs)/max(total,1),2),
        "failure_types": dict(Counter(d.get("failure_type","") for d in failure_docs)),
        "severity_breakdown": dict(Counter(d.get("severity","") for d in docs)),
    }

    system = """You are the Reliability Analysis Agent for a hospital biomedical engineering system.
Analyze equipment reliability patterns and return valid JSON with keys: failure_rate, reliability_score (0-100), anomalies (list), failure_patterns (list), high_risk_equipment (list), temperature_analysis, wear_analysis, severity_breakdown (object)."""

    user = f'Query: "{query}"\n\nStats:\n{json.dumps(stats,indent=2)}\n\nRelevant equipment: {json.dumps(retrieval.get("relevant_incidents",[])[:5])}\n\nReturn JSON.'
    result = _extract_json(_call_claude(client, system, user, 1000))
    return result if result else fallback


def maintenance_agent(query: str, docs: List[Dict], reliability: Dict, client) -> Dict:
    fallback = _rule_maintenance(docs, reliability)
    if client is None:
        return fallback

    context = {
        "query": query,
        "reliability_score": reliability.get("reliability_score",0),
        "failure_rate": reliability.get("failure_rate",0),
        "anomalies": reliability.get("anomalies",[]),
        "failure_patterns": reliability.get("failure_patterns",[]),
        "high_risk_equipment": reliability.get("high_risk_equipment",[]),
        "recent_failures": [{"id":d.get("equipment_id"),"type":d.get("equipment_type"),"failure":d.get("failure_type"),"severity":d.get("severity"),"notes":d.get("technician_notes")} for d in docs if d.get("machine_failure")==1][:5],
    }

    system = """You are the Maintenance Agent for a hospital biomedical engineering system.
Suggest specific maintenance actions. Return valid JSON with keys: immediate_actions (list), scheduled_maintenance (list), preventive_measures (list), priority_order (list), estimated_downtime_reduction, maintenance_urgency."""

    user = f'Reliability Analysis:\n{json.dumps(context,indent=2)}\n\nReturn JSON maintenance recommendations.'
    result = _extract_json(_call_claude(client, system, user, 1200))
    return result if result else fallback


def recommendation_agent(query: str, docs: List[Dict], retrieval: Dict, reliability: Dict, maintenance: Dict, client) -> Dict:
    fallback = _rule_recommendation(query, docs, retrieval, reliability, maintenance)
    if client is None:
        return fallback

    synthesis = {
        "query": query,
        "total_incidents_analyzed": len(docs),
        "failures_found": sum(1 for d in docs if d.get("machine_failure")==1),
        "reliability_score": reliability.get("reliability_score",0),
        "failure_rate": reliability.get("failure_rate",0),
        "anomalies": reliability.get("anomalies",[]),
        "failure_patterns": reliability.get("failure_patterns",[]),
        "immediate_actions": maintenance.get("immediate_actions",[]),
        "high_risk_equipment": reliability.get("high_risk_equipment",[]),
        "equipment_focus": retrieval.get("equipment_focus",[]),
    }

    system = """You are the Chief Recommendation Agent for a hospital biomedical engineering intelligence system.
Synthesize all agent outputs into a final recommendation. Return valid JSON with keys: summary (string), root_cause (string), confidence_score (0-100), key_findings (list), action_plan (list), risk_assessment (Low/Medium/High/Critical), equipment_status (object), follow_up (list)."""

    user = f'Multi-Agent Synthesis:\n{json.dumps(synthesis,indent=2)}\n\nReturn final JSON recommendation.'
    result = _extract_json(_call_claude(client, system, user, 1500))
    return result if result else fallback


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def run_multi_agent_pipeline(query: str, docs: List[Dict]) -> Dict[str, Any]:
    client = _get_client()
    mode = "Claude AI" if client is not None else "Rule-Based Analysis"
    print(f"Multi-Agent Pipeline [{mode}]: {query[:60]}")

    print("  Agent 1: Equipment Retrieval...")
    retrieval = equipment_retrieval_agent(query, docs, client)

    print("  Agent 2: Reliability Analysis...")
    reliability = reliability_analysis_agent(query, docs, retrieval, client)

    print("  Agent 3: Maintenance Planning...")
    maint = maintenance_agent(query, docs, reliability, client)

    print("  Agent 4: Final Recommendations...")
    rec = recommendation_agent(query, docs, retrieval, reliability, maint, client)

    return {
        "retrieval_analysis": retrieval,
        "reliability_analysis": reliability,
        "maintenance_plan": maint,
        "final_recommendation": rec,
        "analysis_mode": mode,
    }
