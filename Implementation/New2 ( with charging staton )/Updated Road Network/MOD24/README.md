# Simulation-Based Analysis and Machine Learning Prediction of EV Charging Load Demand
### Khulna City, Bangladesh

This project uses SUMO (Simulation of Urban MObility) to simulate Electric Vehicle (EV) traffic and charging behaviors in Khulna City. The scripts collect high-resolution data to predict charging load demand using Machine Learning.

## 📂 Key Scripts

### 1. `charging_station_monitor.py` (Primary Data Collector)
**Status:** ✅ Active / Recommended
**Purpose:** Runs the main simulation with **Enhanced Queue Management**. It manages charging slots and waiting queues effectively and collects the most comprehensive dataset for analysis.

*   **Key Features:**
    *   **Vehicle-Centric Data:** Outputs one row for EACH vehicle at EACH timestep.
    *   **Context Aware:** Each vehicle row includes the overall System State (Total Load, Total Vehicles) and the Station State (if applicable).
    *   **Smart Queue Management:** Separates vehicles into 'charging' and 'waiting' slots.
    *   **Outputs:** A detailed CSV for detailed behavioral analysis.

*   **Output File:** `simulation_outputs/EV_Charging_Load_Demand_Dataset_YYYYMMDD_HHMMSS.csv`

### 2. `load_demand_prediction.py` (ML-Feature Generator)
**Status:** ℹ️ Alternative
**Purpose:** Focuses on generating station-level aggregated features with lagged variables for immediate time-series forecasting.

---

## 📊 Dataset Structure (`charging_station_monitor.py`)

The primary output is a **Vehicle-Centric Dataset**. 
**Resolution:** 1 row per vehicle per timestep.

### Column Dictionary

| Category | Column Name | Description |
| :--- | :--- | :--- |
| **Identity** | `timestep_sec` | Simulation second. |
| | `vehicle_id` | **Type ID** of the vehicle (e.g., `easyBike_001`). used as ID. |
| **Vehicle Metrics** | `speed_ms` | Current speed (m/s). |
| | `acceleration_ms2` | Current acceleration (m/s²). |
| | `soc_percent` | State of Charge (%). |
| | `energy_consumed_Wh` | Cumulative energy consumed. |
| | `status` | `driving`, `idle`, `charging`, `waiting`. |
| | `lane_id` | ID of the lane (sanitized, `NEG_` prefix for negative edges). |

| **Station Context** | `current_station_id` | ID of station if charging/waiting (else `none`). |
| *(If at station)* | `station_load_kW` | Current load of that station. |
| | `station_vehicles_charging` | Count of vehicles charging at that station. |
| | `station_queue_length` | Count of vehicles waiting at that station. |
| **System Context** | `system_total_load_kW` | **(Target)** Total power demand of the entire grid. |
| *(Repeated for all)* | `system_total_vehicles` | Total active vehicles in map. |
| | `system_avg_speed_ms` | Average speed of ALL vehicles. |
| | `system_avg_soc_percent` | Average SOC of ALL vehicles. |
| | `system_avg_moving_speed_ms` | Average speed of moving vehicles. |
| | `system_avg_charging_soc_percent` | Average SOC of charging vehicles. |


### Vehicle Status Definitions
| Status | Meaning | Condition |
| :--- | :--- | :--- |
| **`charging`** | Active Charging | Plugged into a charging slot (`vid` in charging list). |
| **`waiting`** | Queued at Station | Waiting in line for a slot (`vid` in waiting queue). |
| **`idle`** | Stuck in Traffic / Stopped | On road but Speed < 0.1 m/s (traffic lights/jams). |
| **`driving`** | Moving normally | Moving on road (Speed ≥ 0.1 m/s). |

---

## 🚀 How to Run

Requirements: `python`, `sumo` (must be in PATH), `traci`, `pandas`.

### To run the primary collector:
```bash
python charging_station_monitor.py
```
The simulation will open SUMO-GUI (default). To run in headless mode (faster), edit the script and set `GUI = False` in the `main()` function.
