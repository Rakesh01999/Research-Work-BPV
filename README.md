# Simulation-Based Analysis & ML Prediction of EV Charging Load Demand
## 📍 Khulna City, Bangladesh

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![SUMO](https://img.shields.io/badge/Simulator-SUMO-green.svg)](https://eclipse.dev/sumo/)
[![Machine Learning](https://img.shields.io/badge/ML-XGBoost%20%7C%20Random%20Forest-orange.svg)](https://scikit-learn.org/)

A comprehensive research project focusing on the simulation, monitoring, and machine-learning-based prediction of Electric Vehicle (EV) charging load demand within the urban framework of Khulna City, Bangladesh.

---

## 📖 Overview
This repository contains the full implementation of a research study aimed at optimizing EV infrastructure. By integrating **SUMO (Simulation of Urban MObility)** with advanced **Machine Learning algorithms**, this project predicts the system-wide electrical load required for EV charging based on real-time traffic flux and station occupancy.

### Key Research Objectives:
- **Traffic Modeling**: Simulating realistic vehicle movement in the Khulna City road network.
- **Demand Estimation**: Monitoring individual vehicle energy consumption and station-level load.
- **Predictive Analytics**: Implementing high-accuracy ML models to forecast load demand (kW).

---

## 📂 Project Structure
The repository is organized into specific modules for simulation, data, and presentation:

```bash
├── Implementation/         # Core simulation and monitoring logic
│   └── New2/               # Latest SUMO configurations and monitors
│       ├── run_simulation.py
│       └── vehicle_monitor.py
├── Data/                   # Datasets and raw simulation outputs
├── Thesis-Defense/         # Final analysis and ML model training
│   └── defense/
│       └── Load Demand Prediction Analysis Using ML/
│           ├── ml_models.py      # Main ML pipeline
│           └── plots/            # Result visualizations
├── Thesis-Papers/          # Literature review and reference materials
└── README.md
```

---

## 🛠️ Methodology

### 1. Traffic & Charging Simulation (SUMO)
We utilize **SUMO** to model the urban traffic environment. The network includes:
- **Net Edit**: Customized road network reflecting Khulna City geography.
- **Route Monitoring**: Dynamic vehicle routing based on battery status.
- **Charging Stations**: Parameterized charging points with real-time load monitoring.

### 2. Data Engineering
Data is captured via `vehicle_monitor.py` and `charging_station_monitor.py`. Key features include:
- `vehicle_id`, `lane_id`, `status` (Charging/Driving)
- `battery_level (%)`, `waiting_time`
- **Target**: `system_total_load_kW`

### 3. Machine Learning Framework
We comparative evaluate four primary regression models:
- **XGBoost Regressor** (Best performance)
- **Random Forest**
- **Decision Trees**
- **Linear Regression**

---

## 📊 Results & Analysis

### Model Performance Comparison
| Model | MAE (kW) | RMSE (kW) | R2 Score |
| :--- | :--- | :--- | :--- |
| **XGBoost** | 0.00035 | 0.00038 | **0.9999** |
| **Random Forest** | 0.00 | 0.00 | 1.00 |
| **Decision Tree** | 0.00 | 0.00 | 1.00 |
| **Linear Regression** | 8.57 | 11.24 | 0.9991 |

### Key Visualizations
> [!TIP]
> Figures are generated during the ML pipeline execution (`ml_models.py`).

| Feature Importance | Actual vs Predicted Load |
| :---: | :---: |
| ![Feature Importance](./Thesis-Defense/defense/Load%20Demand%20Prediction%20Analysis%20Using%20ML/feature_importance.png) | ![Actual vs Predicted](./Thesis-Defense/defense/Load%20Demand%20Prediction%20Analysis%20Using%20ML/actual_vs_predicted.png) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- [SUMO Simulation Suite](https://eclipse.dev/sumo/)
- Required Libraries:
  ```bash
  pip install pandas numpy scikit-learn xgboost matplotlib seaborn
  ```

### Running Simulation
1. Navigate to `Implementation/New2/`
2. Run the SUMO simulation:
   ```bash
   python run_simulation.py
   ```

### Training ML Models
1. Navigate to the ML directory:
   ```bash
   cd "Thesis-Defense/defense/Load Demand Prediction Analysis Using ML"
   ```
2. Run the analysis script:
   ```bash
   python ml_models.py
   ```

---

## 🎓 Attribution
**Research conducted at:** Jashore University of Science and Technology (JUST), Bangladesh.
**Principal Researcher:** Rakesh 

> This work is part of a thesis study on sustainable urban infrastructure and electric vehicle integration in developing cities.
