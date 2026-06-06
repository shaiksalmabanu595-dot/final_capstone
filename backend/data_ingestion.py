"""
AI4I 2020 Predictive Maintenance Dataset — Generator + Medical Equipment Ingestion Pipeline

Generates ai4i2020.csv matching the exact UCI schema:
  UDI, Product ID, Type, Air temperature [K], Process temperature [K],
  Rotational speed [rpm], Torque [Nm], Tool wear [min],
  Machine failure, TWF, HDF, PWF, OSF, RNF

Then enriches it with medical-equipment context columns for the RAG system:
  equipment_id, equipment_type, equipment_model, hospital_unit, severity,
  failure_type (human-readable), downtime_hours, maintenance_cost_usd,
  days_since_last_pm, technician_notes, timestamp
"""

import os
import random
import numpy as np
import pandas as pd

# ─── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
AI4I_CSV = os.path.join(DATA_DIR, "ai4i2020.csv")
ENRICHED_CSV = os.path.join(DATA_DIR, "medical_equipment_maintenance.csv")

# ─── Medical equipment mapping (UCI Type → hospital equipment) ─────────────────
# Type L (low precision) → high-volume bedside equipment
# Type M (medium)        → mid-tier diagnostic equipment
# Type H (high precision)→ advanced imaging / lab systems
TYPE_TO_EQUIPMENT = {
    "L": [
        ("Ventilator",     ["Drager Evita V500", "Medtronic PB980", "Hamilton-C6"]),
        ("Infusion Pump",  ["BD Alaris System", "Baxter Sigma Spectrum", "ICU Medical Plum 360"]),
        ("Patient Monitor",["Philips IntelliVue MX750", "GE Carescape B650", "Mindray N22"]),
    ],
    "M": [
        ("Ultrasound",     ["GE LOGIQ E10", "Philips EPIQ Elite", "Siemens ACUSON S3000"]),
        ("ICU Device",     ["Spacelabs Monitor", "Nellcor PM1000N", "Masimo Radical-7"]),
        ("Lab Analyzer",   ["Abbott ARCHITECT i2000SR", "Roche cobas 8000", "Beckman AU5800"]),
    ],
    "H": [
        ("MRI",            ["Siemens MAGNETOM Vida", "GE SIGNA Premier", "Philips Ingenia 3T"]),
        ("CT Scanner",     ["Siemens SOMATOM Drive", "GE Revolution CT", "Canon Aquilion Prime"]),
    ],
}

HOSPITAL_UNITS = {
    "MRI":            ["Radiology", "Neurology", "Oncology"],
    "CT Scanner":     ["Radiology", "Emergency", "Oncology"],
    "Ventilator":     ["ICU", "Emergency", "General Ward"],
    "Infusion Pump":  ["ICU", "Oncology", "General Ward", "Cardiology"],
    "Patient Monitor":["ICU", "Cardiology", "General Ward", "Emergency"],
    "Ultrasound":     ["Radiology", "Cardiology", "General Ward", "Emergency"],
    "ICU Device":     ["ICU", "Emergency", "Cardiology"],
    "Lab Analyzer":   ["Laboratory", "Oncology", "General Ward"],
}

# Map UCI binary failure columns → human-readable failure_type
FAILURE_COL_TO_TYPE = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
    "RNF": "Random Failure",
}

TECHNICIAN_NOTES = {
    "No Failure": [
        "Routine inspection completed. All parameters normal.",
        "Preventive maintenance performed. Equipment functioning within specifications.",
        "Scheduled check completed. No anomalies detected.",
        "Calibration verified. Sensor readings within tolerance.",
    ],
    "Tool Wear Failure": [
        "Component wear detected. Replacement scheduled per protocol.",
        "Excessive tool wear causing performance degradation. Component replaced.",
        "Wear-induced failure. Component replaced and system tested.",
        "Wear threshold exceeded. Immediate replacement performed.",
    ],
    "Heat Dissipation Failure": [
        "Thermal management issue. Cooling system serviced.",
        "Overheating observed. Fan replaced and airflow restored.",
        "Heat dissipation failure. Thermal paste replaced, heat sinks cleaned.",
        "Thermal anomaly detected. Temperature sensors recalibrated.",
    ],
    "Power Failure": [
        "Power supply unit failure. PSU replaced. UPS checked.",
        "Electrical fault detected. Power board inspected and replaced.",
        "Intermittent power issues. Wiring inspected, faulty components replaced.",
        "Power fluctuation caused shutdown. Surge protector and PSU replaced.",
    ],
    "Overstrain Failure": [
        "Mechanical overstrain. Load limits recalibrated.",
        "Motor overstrain failure. Drive belt replaced and torque adjusted.",
        "Excessive load caused failure. Safety limits updated.",
        "Overstrain detected. Mechanical components inspected and replaced.",
    ],
    "Random Failure": [
        "Unexpected failure. Full diagnostic performed.",
        "Sporadic failure. Firmware updated and sensors recalibrated.",
        "Intermittent fault. All connections tested, sensor replaced.",
        "Unclassified failure. Complete system diagnostic performed.",
    ],
}


# ─── Step 1: Generate ai4i2020.csv (UCI exact schema) ────────────────────────
def generate_ai4i2020(n: int = 10000, seed: int = 42) -> pd.DataFrame:
    """
    Generate a synthetic ai4i2020.csv matching the UCI AI4I 2020 dataset schema
    and statistical distributions of the real dataset.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Product types with UCI proportions: L=50%, M=30%, H=20%
    types = rng.choice(["L", "M", "H"], size=n, p=[0.50, 0.30, 0.20])

    # Product IDs (letter prefix + 5-digit number, matches real dataset format)
    counters = {"L": 0, "M": 0, "H": 0}
    product_ids = []
    for t in types:
        counters[t] += 1
        product_ids.append(f"{t}{counters[t]:05d}")

    # Sensor readings (matched to real UCI distributions)
    air_temp   = rng.normal(300.0, 2.0, n).clip(295, 304)              # K
    proc_temp  = air_temp + rng.normal(10.0, 1.0, n).clip(8, 12)       # K (always ~10 above air)
    rot_speed  = rng.normal(1500, 200, n).clip(1168, 2886).astype(int)  # rpm
    torque     = rng.normal(40.0, 10.0, n).clip(3.8, 76.7).round(1)    # Nm
    tool_wear  = (rng.uniform(0, 253, n)).astype(int)                   # min

    # Failure logic (matches real UCI failure rates ~3.4%)
    machine_failure = np.zeros(n, dtype=int)
    twf = np.zeros(n, dtype=int)
    hdf = np.zeros(n, dtype=int)
    pwf = np.zeros(n, dtype=int)
    osf = np.zeros(n, dtype=int)
    rnf = np.zeros(n, dtype=int)

    for i in range(n):
        # Tool Wear Failure: tool_wear > 200 AND (type L or M with higher chance)
        if tool_wear[i] > 200 and rng.random() < 0.04:
            twf[i] = 1

        # Heat Dissipation Failure: temp diff < 8.6K AND rotational speed < 1380 rpm
        temp_diff = proc_temp[i] - air_temp[i]
        if temp_diff < 8.6 and rot_speed[i] < 1380 and rng.random() < 0.15:
            hdf[i] = 1

        # Power Failure: torque × rpm out of bounds (power window 3500–9000)
        power = torque[i] * rot_speed[i] * (2 * np.pi / 60)
        if (power < 3500 or power > 9000) and rng.random() < 0.05:
            pwf[i] = 1

        # Overstrain Failure: tool_wear × torque > threshold based on type
        threshold = {"L": 11000, "M": 12000, "H": 13000}[types[i]]
        if tool_wear[i] * torque[i] > threshold and rng.random() < 0.03:
            osf[i] = 1

        # Random Failure: rare, 0.1% of all
        if rng.random() < 0.001:
            rnf[i] = 1

        # Machine failure = OR of all failure modes
        if twf[i] or hdf[i] or pwf[i] or osf[i] or rnf[i]:
            machine_failure[i] = 1

    df = pd.DataFrame({
        "UDI":                      range(1, n + 1),
        "Product ID":               product_ids,
        "Type":                     types,
        "Air temperature [K]":      air_temp.round(1),
        "Process temperature [K]":  proc_temp.round(1),
        "Rotational speed [rpm]":   rot_speed,
        "Torque [Nm]":              torque,
        "Tool wear [min]":          tool_wear,
        "Machine failure":          machine_failure,
        "TWF":                      twf,
        "HDF":                      hdf,
        "PWF":                      pwf,
        "OSF":                      osf,
        "RNF":                      rnf,
    })

    return df


# ─── Step 2: Enrich ai4i2020 with medical equipment context ───────────────────
def enrich_with_medical_context(ai4i_df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Maps UCI columns to hospital/medical-equipment context columns.
    Adds: equipment_id, equipment_type, equipment_model, hospital_unit,
          failure_type, severity, downtime_hours, maintenance_cost_usd,
          days_since_last_pm, technician_notes, timestamp
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)
    n = len(ai4i_df)

    # Build equipment assignments (deterministic per UDI)
    equipment_types = []
    equipment_models = []
    equipment_ids = []
    hospital_units = []

    eq_counters: dict = {}

    for _, row in ai4i_df.iterrows():
        t = row["Type"]
        options = TYPE_TO_EQUIPMENT[t]
        idx = int(row["UDI"]) % len(options)
        eq_type, models = options[idx]
        model = models[int(row["UDI"]) % len(models)]

        prefix = eq_type[:3].upper().replace(" ", "")
        eq_counters[prefix] = eq_counters.get(prefix, 0) + 1
        # Group into devices of ~30 records each for realism
        device_num = ((eq_counters[prefix] - 1) // 30) + 1
        eq_id = f"{prefix}{device_num:03d}"

        unit_options = HOSPITAL_UNITS.get(eq_type, ["General Ward"])
        unit = unit_options[int(row["UDI"]) % len(unit_options)]

        equipment_types.append(eq_type)
        equipment_models.append(model)
        equipment_ids.append(eq_id)
        hospital_units.append(unit)

    # Resolve failure_type (human-readable, priority: TWF > HDF > PWF > OSF > RNF)
    def resolve_failure_type(row):
        if row["TWF"]: return "Tool Wear Failure"
        if row["HDF"]: return "Heat Dissipation Failure"
        if row["PWF"]: return "Power Failure"
        if row["OSF"]: return "Overstrain Failure"
        if row["RNF"]: return "Random Failure"
        return "No Failure"

    failure_types = ai4i_df.apply(resolve_failure_type, axis=1).tolist()

    # Severity
    def assign_severity(fail, machine_fail):
        if not machine_fail:
            return rng.choice(["Low", "Medium"], p=[0.72, 0.28])
        if fail in ("Random Failure",):
            return rng.choice(["Medium", "High"], p=[0.4, 0.6])
        if fail == "Tool Wear Failure":
            return rng.choice(["High", "Critical"], p=[0.55, 0.45])
        return rng.choice(["Medium", "High", "Critical"], p=[0.25, 0.45, 0.30])

    severities = [
        assign_severity(ft, mf)
        for ft, mf in zip(failure_types, ai4i_df["Machine failure"])
    ]

    # Downtime hours
    downtime_map = {"Critical": (8, 48), "High": (3, 12), "Medium": (0.5, 4), "Low": (0, 0)}

    def assign_downtime(sev, machine_fail):
        if not machine_fail:
            return 0.0
        lo, hi = downtime_map.get(sev, (0, 0))
        return round(float(rng.uniform(lo, hi)), 1) if hi > 0 else 0.0

    downtimes = [
        assign_downtime(sev, mf)
        for sev, mf in zip(severities, ai4i_df["Machine failure"])
    ]

    # Maintenance cost
    cost_map = {"Critical": (5000, 25000), "High": (1000, 8000), "Medium": (200, 2000), "Low": (0, 0)}

    def assign_cost(sev, machine_fail):
        if not machine_fail:
            return 0
        lo, hi = cost_map.get(sev, (0, 0))
        return int(rng.uniform(lo, hi)) if hi > 0 else 0

    costs = [
        assign_cost(sev, mf)
        for sev, mf in zip(severities, ai4i_df["Machine failure"])
    ]

    # Days since last PM
    days_pm = rng.integers(0, 181, n).tolist()

    # Timestamps (spread over 2 years)
    base = pd.Timestamp("2023-01-01")
    timestamps = [
        (base + pd.Timedelta(days=int(rng.integers(0, 730)))).strftime("%Y-%m-%d %H:%M:%S")
        for _ in range(n)
    ]

    # Technician notes
    notes = [
        random.choice(TECHNICIAN_NOTES.get(ft, TECHNICIAN_NOTES["No Failure"]))
        for ft in failure_types
    ]

    enriched = ai4i_df.copy()
    # Rename UCI columns to our system's column names (keep UCI cols too)
    enriched["record_id"]              = [f"REC{i+1:05d}" for i in range(n)]
    enriched["equipment_id"]           = equipment_ids
    enriched["equipment_type"]         = equipment_types
    enriched["equipment_model"]        = equipment_models
    enriched["hospital_unit"]          = hospital_units
    enriched["timestamp"]              = timestamps
    enriched["air_temperature_k"]      = ai4i_df["Air temperature [K]"]
    enriched["process_temperature_k"]  = ai4i_df["Process temperature [K]"]
    enriched["rotational_speed_rpm"]   = ai4i_df["Rotational speed [rpm]"]
    enriched["torque_nm"]              = ai4i_df["Torque [Nm]"]
    enriched["tool_wear_min"]          = ai4i_df["Tool wear [min]"]
    enriched["machine_failure"]        = ai4i_df["Machine failure"]
    enriched["failure_type"]           = failure_types
    enriched["severity"]               = severities
    enriched["downtime_hours"]         = downtimes
    enriched["maintenance_cost_usd"]   = costs
    enriched["days_since_last_pm"]     = days_pm
    enriched["technician_notes"]       = notes

    return enriched


# ─── Public API ───────────────────────────────────────────────────────────────
def run_ingestion_pipeline(force: bool = False) -> pd.DataFrame:
    """
    Full pipeline:
    1. Generate (or load) ai4i2020.csv
    2. Enrich with medical equipment context
    3. Save medical_equipment_maintenance.csv
    4. Return enriched DataFrame
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Step 1: ai4i2020.csv
    if not os.path.exists(AI4I_CSV) or force:
        print("Generating ai4i2020.csv (UCI AI4I 2020 schema, 10 000 records)...")
        ai4i_df = generate_ai4i2020(n=10000)
        ai4i_df.to_csv(AI4I_CSV, index=False)
        print(f"  ✅ Saved: {AI4I_CSV}  ({len(ai4i_df):,} rows × {len(ai4i_df.columns)} cols)")
    else:
        print(f"Loading existing ai4i2020.csv...")
        ai4i_df = pd.read_csv(AI4I_CSV)
        print(f"  ✅ Loaded: {len(ai4i_df):,} rows")

    # Step 2: Enrich
    print("Enriching with medical equipment context...")
    enriched = enrich_with_medical_context(ai4i_df)
    enriched.to_csv(ENRICHED_CSV, index=False)
    print(f"  ✅ Saved: {ENRICHED_CSV}  ({len(enriched):,} rows × {len(enriched.columns)} cols)")

    # Summary stats
    failures = enriched[enriched["machine_failure"] == 1]
    print(f"\nDataset summary:")
    print(f"  Total records  : {len(enriched):,}")
    print(f"  Failures       : {len(failures):,} ({len(failures)/len(enriched)*100:.1f}%)")
    print(f"  Equipment types: {sorted(enriched['equipment_type'].unique().tolist())}")
    print(f"  Hospital units : {sorted(enriched['hospital_unit'].unique().tolist())}")
    print(f"  Failure types  : {[k for k in FAILURE_COL_TO_TYPE.values()]}")

    return enriched


def load_enriched_dataset() -> pd.DataFrame:
    """Load the enriched dataset; run ingestion pipeline if it doesn't exist."""
    if not os.path.exists(ENRICHED_CSV) or not os.path.exists(AI4I_CSV):
        return run_ingestion_pipeline()
    return pd.read_csv(ENRICHED_CSV)


if __name__ == "__main__":
    run_ingestion_pipeline(force=True)
