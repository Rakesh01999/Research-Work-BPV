# Simulation-Based Analysis and Machine Learning Prediction of EV Charging Load Demand
### Khulna City, Bangladesh

This project uses SUMO (Simulation of Urban MObility) to simulate Electric Vehicle (EV) traffic and charging behaviors in Khulna City. The scripts collect high-resolution data to predict charging load demand using Machine Learning.

## 📂 Key Scripts

### 1. `charging_station_monitor.py` (Primary Data Collector)
**Status:** ✅ Active / Recommended
**Purpose:** Runs the main simulation with **Enhanced Queue Management**. It manages charging slots and waiting queues effectively and collects the most comprehensive dataset for analysis.

*   **Key Features:**
    *   **Smart Queue Management:** Separates vehicles into 'charging' and 'waiting' slots.
    *   **Real-time Monitoring:** Promotes vehicles from waiting to charging automatically.
    *   **System-Wide Aggregation:** Collects aggregate metrics for the entire traffic system (not just charging vehicles).
    *   **Outputs:** A "Long-Format" CSV (one row per station per timestep).

*   **Output File:** `simulation_outputs/EV_Charging_Load_Demand_Dataset_YYYYMMDD_HHMMSS.csv`

### 2. `load_demand_prediction.py` (ML-Ready Generator)
**Status:** ℹ️ Alternative / Feature Engineering Focus
**Purpose:** A variation of the monitor that focuses on generating features specifically for immediate ML training, such as **lagged variables** and **rolling averages**.

*   **Key Features:**
    *   **Lag Features:** Automatically creates `lag1`, `lag5` columns (past values).
    *   **Rolling Averages:** Creates 5-min and 10-min rolling average columns for load demand.
*   **Output File:** `simulation_outputs/ev_charging_ml_dataset_YYYYMMDD_HHMMSS.csv`

### 3. `charging_station_monitor0.py` / `charging_station_monitor1.py`
**Status:** 🔒 Legacy / Backup
**Purpose:** Older versions of the monitoring script. Kept for archival purposes.

---

## 📊 Dataset Structure

The primary output (`EV_Charging_Load_Demand_Dataset_...`) contains detailed metrics at **1-second resolution**.

### Column Dictionary

| Category | Column Name | Description |
| :--- | :--- | :--- |
| **Time** | `timestep_sec` | Simulation second (0-600s). |
| | `minute_of_hour` | Minute within the hour. |
| **Identity** | `station_id` | ID of the charging station (e.g., `pa_2`). |
| | `station_edge` | Road edge ID where station is located. |
| **Target** | `station_power_demand_kW` | **(Target)** Total power currently being drawn at station. |
| | `station_vehicles_charging` | Number of vehicles currently charging. |
| **Station State** | `station_vehicles_waiting` | Number of vehicles in queue. |
| | `station_charging_utilization_%` | % of charging slots occupied. |
| | `station_queue_length` | Depth of the waiting queue. |
| | `congestion_ratio` | Ratio of total demand (charging+waiting) to total capacity. |
| **System State** | `system_total_vehicles` | Total active vehicles in the map. |
| | `system_moving_vehicles` | Vehicles currently driving (speed > 0.1 m/s). |
| | `system_avg_speed_ms` | Average speed of ALL active vehicles. |
| | `system_avg_soc_percent` | Average Battery SOC of ALL active vehicles. |
| | `system_total_power_demand_kW` | Total power demand of the entire city grid. |

*(Note: The CSV contains additional derived metrics not listed above.)*

---

## 🚀 How to Run

Requirements: `python`, `sumo` (must be in PATH), `traci`, `pandas`.

### To run the primary collector:
```bash
python charging_station_monitor.py
```

### To run the ML-feature generator:
```bash
python load_demand_prediction.py
```

The simulation will open SUMO-GUI (default). To run in headless mode (faster), edit the script and set `GUI = False` in the `main()` function.
