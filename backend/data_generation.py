import pandas as pd
import numpy as np
import random
import os

EQUIPMENT_TYPES = ["MRI", "CT Scanner", "Ventilator", "Infusion Pump", "Patient Monitor", "Ultrasound", "ICU Device", "Lab Analyzer"]
HOSPITAL_UNITS = ["ICU", "Emergency", "Radiology", "Cardiology", "Neurology", "General Ward", "Laboratory", "Oncology"]
FAILURE_TYPES = ["No Failure", "Tool Wear Failure", "Heat Dissipation Failure", "Power Failure", "Overstrain Failure", "Random Failure"]
SEVERITY = ["Low", "Medium", "High", "Critical"]
MODELS = {
    "MRI": ["Siemens MAGNETOM Vida", "GE SIGNA Premier", "Philips Ingenia 3T"],
    "CT Scanner": ["Siemens SOMATOM Drive", "GE Revolution CT", "Canon Aquilion Prime"],
    "Ventilator": ["Drager Evita Infinity V500", "Medtronic PB980", "Hamilton-C6"],
    "Infusion Pump": ["BD Alaris System", "Baxter Sigma Spectrum", "ICU Medical Plum 360"],
    "Patient Monitor": ["Philips IntelliVue MX750", "GE Carescape B650", "Mindray BeneVision N22"],
    "Ultrasound": ["GE LOGIQ E10", "Philips EPIQ Elite", "Siemens ACUSON S3000"],
    "ICU Device": ["Spacelabs Patient Monitor", "Nellcor PM1000N", "Masimo Radical-7"],
    "Lab Analyzer": ["Abbott ARCHITECT i2000SR", "Roche cobas 8000", "Beckman Coulter AU5800"],
}

def generate_maintenance_record(idx: int, equipment_id: str, equipment_type: str, unit: str, rng: np.random.Generator) -> dict:
    model = rng.choice(MODELS[equipment_type])
    base_temp = 298 + rng.normal(0, 2)
    process_temp = base_temp + 10 + rng.normal(0, 1)
    rotational_speed = int(rng.normal(1500, 200))
    torque = round(rng.normal(40, 10), 1)
    tool_wear = int(rng.uniform(0, 250))

    # Determine failure
    failure_prob = 0.05
    if tool_wear > 200:
        failure_prob += 0.15
    if abs(base_temp - 298) > 4:
        failure_prob += 0.10
    if rotational_speed < 1200 or rotational_speed > 1800:
        failure_prob += 0.08
    if torque > 60 or torque < 20:
        failure_prob += 0.07

    has_failure = rng.random() < failure_prob

    if has_failure:
        weights = [0, 0.25, 0.25, 0.20, 0.20, 0.10]
        failure_type = rng.choice(FAILURE_TYPES, p=weights)
        severity = rng.choice(["Medium", "High", "Critical"], p=[0.3, 0.45, 0.25])
    else:
        failure_type = "No Failure"
        severity = rng.choice(["Low", "Medium"], p=[0.7, 0.3])

    downtime = 0
    if has_failure:
        if severity == "Critical":
            downtime = round(rng.uniform(8, 48), 1)
        elif severity == "High":
            downtime = round(rng.uniform(4, 12), 1)
        else:
            downtime = round(rng.uniform(1, 5), 1)

    maintenance_cost = 0
    if has_failure:
        cost_map = {"Critical": (5000, 25000), "High": (1000, 8000), "Medium": (200, 2000)}
        low, high = cost_map.get(severity, (100, 500))
        maintenance_cost = int(rng.uniform(low, high))

    days_since_pm = int(rng.uniform(0, 180))
    timestamp = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.uniform(0, 730)))

    return {
        "record_id": f"REC{idx:05d}",
        "equipment_id": equipment_id,
        "equipment_type": equipment_type,
        "equipment_model": model,
        "hospital_unit": unit,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "air_temperature_k": round(base_temp, 2),
        "process_temperature_k": round(process_temp, 2),
        "rotational_speed_rpm": max(100, rotational_speed),
        "torque_nm": max(1.0, torque),
        "tool_wear_min": tool_wear,
        "machine_failure": 1 if has_failure else 0,
        "failure_type": failure_type,
        "severity": severity,
        "downtime_hours": downtime,
        "maintenance_cost_usd": maintenance_cost,
        "days_since_last_pm": days_since_pm,
        "technician_notes": _generate_notes(equipment_type, failure_type, severity, tool_wear),
    }


def _generate_notes(eq_type: str, failure: str, severity: str, wear: int) -> str:
    notes_map = {
        "No Failure": [
            f"Routine inspection completed. All parameters normal. Tool wear at {wear} min.",
            "Preventive maintenance performed. Equipment functioning within specifications.",
            "Scheduled check completed. No anomalies detected.",
        ],
        "Tool Wear Failure": [
            f"Component wear detected at {wear} min. Replacement scheduled.",
            f"Excessive tool wear ({wear} min) causing performance degradation. Immediate replacement required.",
            "Wear-induced failure. Component replaced and tested.",
        ],
        "Heat Dissipation Failure": [
            "Thermal management issue detected. Cooling system serviced.",
            "Overheating observed during operation. Fan replaced and airflow restored.",
            "Heat dissipation failure. Thermal paste replaced, heat sinks cleaned.",
        ],
        "Power Failure": [
            "Power supply unit failure. UPS system activated. PSU replaced.",
            "Electrical fault detected. Power board inspected and replaced.",
            "Intermittent power issues. Wiring checked and replaced faulty components.",
        ],
        "Overstrain Failure": [
            "Mechanical overstrain detected. Load limits exceeded. Recalibrated.",
            "Motor overstrain failure. Drive belt replaced and torque limits adjusted.",
            "Excessive load caused component failure. Safety limits updated.",
        ],
        "Random Failure": [
            "Unexpected failure with no clear root cause. Full diagnostic performed.",
            "Sporadic failure detected. Firmware updated and sensors recalibrated.",
            "Intermittent failure. All connections tested, sensor replaced.",
        ],
    }
    options = notes_map.get(failure, ["Maintenance completed."])
    return random.choice(options)


def generate_dataset(n_records: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Create equipment fleet
    equipment_list = []
    for eq_type in EQUIPMENT_TYPES:
        n_units = max(2, int(rng.integers(3, 8)))
        for i in range(n_units):
            unit = rng.choice(HOSPITAL_UNITS)
            eq_id = f"{eq_type[:3].upper()}{i+1:03d}"
            equipment_list.append((eq_id, eq_type, unit))

    records = []
    for idx in range(n_records):
        eq_id, eq_type, unit = equipment_list[idx % len(equipment_list)]
        record = generate_maintenance_record(idx, eq_id, eq_type, unit, rng)
        records.append(record)

    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def save_dataset(output_path: str = None, n_records: int = 1000) -> str:
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), "data", "medical_equipment_maintenance.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = generate_dataset(n_records)
    df.to_csv(output_path, index=False)
    print(f"Dataset saved: {output_path} ({len(df)} records)")
    return output_path


def load_dataset(path: str = None) -> pd.DataFrame:
    """
    Load the medical equipment maintenance dataset.
    Prefers the ai4i2020-derived enriched dataset (data_ingestion pipeline).
    Falls back to synthetic generation if ingestion module is unavailable.
    """
    try:
        from data_ingestion import load_enriched_dataset
        return load_enriched_dataset()
    except ImportError:
        pass

    if path is None:
        path = os.path.join(os.path.dirname(__file__), "data", "medical_equipment_maintenance.csv")
    if not os.path.exists(path):
        print("Dataset not found. Generating synthetic dataset...")
        save_dataset(path)
    return pd.read_csv(path)


if __name__ == "__main__":
    from data_ingestion import run_ingestion_pipeline
    run_ingestion_pipeline(force=True)
