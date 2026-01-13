

---

# 🚗 **What Is Happening in "run_smart_charging_simulation.py" Simulation**

My updated script implements an **Enhanced Smart Charging System** for EVs inside SUMO.
It intelligently manages **charging decisions, routing, charging slot availability, and journey continuation**.

Below is the complete breakdown:

---

# ✅ **1. Vehicles are continuously monitored**

Every simulation second, the system checks for each vehicle:

* Current battery SOC (%)
* Position, lane, speed, distance traveled
* Whether the vehicle is currently charging
* Whether the vehicle needs charging soon

This happens inside the functions:

```
collect_vehicle_data()
monitor_charging()
```

---

# ✅ **2. When SOC < 30%, the system triggers a charging decision**

Whenever a vehicle’s SOC falls below:

```
SOC_THRESHOLD = 30%
```

the system searches for:

✔ The nearest charging station
✔ That is reachable
✔ That is not occupied
✔ With the shortest route

This is done using:

```
find_nearest_reachable_station()
```

---

# ✅ **3. Charging slot management (major improvement)**

My script now keeps track of which station is occupied:

```
station_occupancy = {}
```

This means:

* A station is marked **occupied** when a vehicle goes there.
* No other vehicle will be routed to the same station.
* When a vehicle finishes charging:
  → the station becomes **free** immediately
  → next vehicle can use it

This prevents traffic jams at the station area.

---

# ✅ **4. Vehicles get optimized charging time**

Charging duration is reduced and optimized:

```
MIN_CHARGE_TIME = 30 seconds
MAX_CHARGE_TIME = 300 seconds
SOC_TARGET = 70%
```

The system calculates the *exact time needed* to reach 70% SOC, but the time is forced to stay between 30–300 seconds.

This ensures:

* Fast rotation
* No long delays
* More efficiency

---

# ✅ **5. Vehicles automatically reroute to a charging station**

When a station is selected, the script builds a **combined route**:

1. Current position → station
2. Station → original destination

This ensures:

✔ No impossible or broken routes
✔ SUMO knows the vehicle must stop at the charging area
✔ After charging, the vehicle continues automatically

This is implemented in:

```
reroute_and_schedule_charge()
```

---

# ✅ **6. Vehicle charging is detected (start + end)**

The simulation automatically detects:

* When charging starts
* When charging stops
* How many seconds charging lasted
* SOC before and after charging

This is done inside:

```
monitor_charging()
```

---

# ✅ **7. After charging, the vehicle resumes its journey**

After charging ends:

* The station slot is freed
* The vehicle continues following the remainder of its route
* It is allowed to be rerouted again later if SOC drops

Printed as:

```
"RESUMING JOURNEY"
```

---

# ✅ **8. Detailed logs and data exports**

At the end, three CSV files are generated:

### 📌 Vehicle tracking

Every second telemetry (SOC, speed, distance, location)

### 📌 Low SOC alerts

When vehicles fall below the 30% threshold

### 📌 Charging events

Start time, end time, SOC change, duration

Exported from:

```
export_results()
```

---

# 🟢 **In summary, my simulation is doing the following:**

### ✔ Detecting low SOC

### ✔ Finding the closest free charging station

### ✔ Rerouting vehicles intelligently

### ✔ Scheduling charging with reduced time

### ✔ Freeing station slots instantly after use

### ✔ Preventing mid-road traffic congestion

### ✔ Automatically continuing the journey after charge

### ✔ Recording everything in CSV files

---


---

# Simple_SOC_Threshold_Tracker.py - Detailed Explanation

## 📋 Main Purpose

This Python script monitors the battery charge levels of electric vehicles (Easy Bikes, E-Rickshaws, E-Vans) running in my SUMO simulation and records when any vehicle's charge **drops below 30%**.

---

## 🔍 What Does the Script Do?

### **1. Runs the Simulation**
- Starts SUMO simulation using my `Test1.sumocfg` file
- Simulation runs for 600 seconds (10 minutes)
- Simulation updates every 0.1 seconds

### **2. Collects Battery Information**
Every second, it collects this information for each vehicle:

#### **Battery Information:**
- **actualBatteryCapacity**: How much charge is currently in the battery (in Wh)
- **maximumBatteryCapacity**: Maximum battery capacity (in Wh)
- **SOC (State of Charge)**: Battery charge as a percentage
  - Calculation: `(current charge / maximum charge) × 100`
  - Example: `(864 / 2700) × 100 = 32%`
- **totalEnergyConsumed**: Total energy consumed (in Wh)
- **totalEnergyRegenerated**: Energy recovered from regenerative braking

#### **Vehicle Position Information:**
- Current speed of the vehicle (in m/s)
- Vehicle's X, Y position (where it is on the map)
- Which lane it's traveling in
- Total distance traveled

### **3. Detects Threshold Violations**

When any vehicle's SOC **drops below 30%**:

#### **On First Violation:**
- Shows warning message on screen:
  ```
  ⚠️ THRESHOLD VIOLATION: easyBike_forward1.0
      Time: 45s
      Type: easyBike
      SOC: 28.50% (Threshold: 30%)
      DEFICIT: 1.50%
      Battery: 769 / 2700 Wh
  ```

#### **Tracks Violations:**
- When the threshold was first crossed
- What was the minimum percentage reached
- What was the maximum deficit
- How many times it stayed below 30%

### **4. Creates Four Output Files**

After simulation ends, these files are created in the `simulation_outputs/` folder:

#### **File 1: all_vehicle_data_[timestamp].csv**
- **Everything Recorded**: Complete information for every vehicle every second
- **Number of Columns**: 18 columns
- **Example Data**:
  ```
  timestep_sec | vehicle_id | vehicle_type | soc_percent | below_threshold | deficit_percent
  45           | easyBike.0 | easyBike    | 28.50       | YES             | 1.50
  46           | easyBike.0 | easyBike    | 28.30       | YES             | 1.70
  ```

#### **File 2: THRESHOLD_VIOLATIONS_ALL_[timestamp].csv**
- **Only Violations**: All records when SOC < 30%
- Which vehicle, when, where, at what charge level - everything
- **Benefit**: Can understand at what time most violations occurred

#### **File 3: VIOLATION_SUMMARY_[timestamp].csv**
- **Summary per Vehicle**: All violations for one vehicle together
- **Columns**:
  - `first_violation_time_sec`: When it first went below 30%
  - `minimum_soc_reached_percent`: What was the lowest level reached
  - `maximum_deficit_percent`: What was the maximum deficit
  - `total_violation_count`: How many times threshold was violated

#### **File 4: THRESHOLD_REPORT_[timestamp].txt**
- **Human-Readable Report**
- Overall statistics
- Detailed information for each vehicle
- Analysis by vehicle type

---

## 🎯 Why Do I Need This Script?

### **1. To Understand Battery Management**
- Which type of vehicle's battery drains faster?
- Which route consumes more battery?
- Where are charging stations needed?

### **2. Problem Identification**
- If many vehicles drop below 30% = Not enough charging stations
- If more violations in specific area = New station needed there

### **3. Research Data Collection**
- Data for thesis or research
- CSV files for creating graphs and charts
- Statistics for decision making

---

## 📊 Output Examples

### **On Screen It Will Show:**
```
======================================================================
SIMPLE SOC THRESHOLD TRACKER
======================================================================
Configuration: Test1.sumocfg
GUI Mode: Disabled
Max Time: 600s
Threshold: 30.0%
======================================================================

✓ TraCI connected

⏱️ Time: 30s | Active: 45 | Vehicles below 30%: 0
⏱️ Time: 60s | Active: 67 | Vehicles below 30%: 3

⚠️ THRESHOLD VIOLATION: easyBike_forward1.12
    Time: 68s
    Type: easyBike
    SOC: 29.45% (Threshold: 30%)
    DEFICIT: 0.55%
    Battery: 795 / 2700 Wh

⏱️ Time: 90s | Active: 82 | Vehicles below 30%: 8
...
```

### **Report File Will Contain:**
```
======================================================================
SOC THRESHOLD VIOLATION REPORT
======================================================================
Generated: 2024-12-11 15:30:45
Threshold: 30.0%
Simulation duration: 600s
======================================================================

SUMMARY
----------------------------------------------------------------------
Total vehicles with violations: 47
Total violation records: 1,234
Average deficit: 3.45%
Maximum deficit: 12.87%
Minimum SOC reached: 17.13%


VEHICLE-WISE DETAILS
----------------------------------------------------------------------

easyBike_forward1.0 (easyBike)
  First violation: 45s at 29.50%
  Minimum SOC: 22.30%
  Maximum deficit: 7.70%
  Total violations: 89
```

---

## ⚙️ How Does It Work? (Technical Flow)

```
1. Script starts 
    ↓
2. Launches SUMO simulation (via TraCI)
    ↓
3. Every 0.1 seconds:
    - Simulation advances one step
    ↓
4. Every 1 second:
    - Gets list of all vehicles
    - Reads battery information for each vehicle
    - Calculates SOC
    - Checks if below 30%
    - Saves data
    ↓
5. If SOC < 30%:
    - Prints warning
    - Records violation
    ↓
6. After 600 seconds or when all vehicles finish:
    - Closes simulation
    - Creates CSV files
    - Generates report
    ↓
7. Complete!
```

---

## 💡 Important Points

### **What the Script Does:**
✅ Monitors battery levels  
✅ Records threshold violations  
✅ Saves detailed data in CSV files  
✅ Creates comprehensive reports  

### **What the Script Does NOT Do:**
❌ Does not send vehicles to charging stations  
❌ Does not change routes  
❌ Does not control charging  
❌ Does not stop simulation (only monitors)  

---

## 🎓 Usefulness for My Thesis

This script will give me:

1. **Quantitative Data**: How many vehicles, when, where faced battery problems
2. **Performance Metrics**: Average SOC, minimum SOC, deficit
3. **Research Insights**: Whether charging infrastructure is sufficient
4. **Graph Data**: Can create graphs in Excel/Python from CSV files

---

## 🚀 How to Use

```bash
# Run directly
python Simple_SOC_Threshold_Tracker.py

# Or if I want to see it with GUI, change inside the script:
USE_GUI = True  # Change from False to True
```

**Check Output:**
- Open `simulation_outputs/` folder
- Analyze CSV files with Excel or Python
- Read TXT report

---



---


# **📊 Complete Load Demand Analysis Explanation**

---

## **1. FUNDAMENTAL CONCEPTS**

### **A. Power vs Energy**
```
Power (kW) = Rate of energy transfer at an instant
Energy (kWh) = Power × Time (total consumption)

Example:
- A vehicle charging at 20 kW for 0.5 hours consumes 10 kWh
```

### **B. State of Charge (SOC)**
```
SOC (%) = (Current Battery Charge / Maximum Battery Capacity) × 100

Example:
- Battery capacity: 7200 Wh
- Current charge: 2160 Wh
- SOC = (2160 / 7200) × 100 = 30%
```

---

## **2. LOAD DEMAND CALCULATIONS (Step-by-Step)**

### **A. Individual Vehicle Charging Power**

When a vehicle is charging at a station:

```python
# From your charging stations configuration:
pa_2: power_kW = 20.0 kW
pa_3: power_kW = 20.0 kW
pa_6: power_kW = 25.0 kW (higher power)
pa_7: power_kW = 20.0 kW
pa_8: power_kW = 25.0 kW (higher power)
```

**Mathematical representation:**
```
P_vehicle = P_station × η_charging

Where:
- P_vehicle = Actual power delivered to vehicle battery (kW)
- P_station = Station rated power (20 or 25 kW)
- η_charging = Charging efficiency (0.95 or 95%)
```

**Example:**
```
Vehicle at pa_2:
P_vehicle = 20 kW × 0.95 = 19 kW (actual to battery)
P_grid = 20 kW (drawn from grid - this is what we count in load)
```

### **B. Per-Station Load Calculation**

For each station at timestep `t`:

```python
# In calculate_load() function:

for station_id, vehicles_charging in currently_charging.items():
    n_vehicles = count(vehicles_at_this_station)
    P_station = CHARGING_STATIONS[station_id]['power_kW']
    
    # Station load
    station_load_kW = n_vehicles × P_station
```

**Example from your CSV:**
```
Timestep 100:
- pa_2_vehicles = 2
- pa_2_power_kW = 2 × 20.0 = 40.0 kW

- pa_6_vehicles = 3  
- pa_6_power_kW = 3 × 25.0 = 75.0 kW
```

### **C. Total System Load**

```python
total_power_demand_kW = Σ(all station loads)
total_power_demand_MW = total_power_demand_kW / 1000
```

**Mathematical formula:**
```
P_total(t) = Σ[n_i(t) × P_i]
             i=1 to N_stations

Where:
- P_total(t) = Total power demand at time t
- n_i(t) = Number of vehicles charging at station i at time t
- P_i = Power rating of station i
- N_stations = Total number of charging stations (10 in your case)
```

**Example:**
```
Timestep 150:
pa_2: 2 vehicles × 20 kW = 40 kW
pa_3: 1 vehicle × 20 kW = 20 kW
pa_6: 4 vehicles × 25 kW = 100 kW
pa_8_rev: 2 vehicles × 25 kW = 50 kW
Others: 0 kW

Total = 40 + 20 + 100 + 50 = 210 kW = 0.210 MW
```

---

## **3. CHARGING DURATION & ENERGY CONSUMPTION**

### **A. Energy Required**

```python
# Energy needed to charge from current SOC to target SOC

E_needed = (SOC_target - SOC_current) / 100 × Battery_capacity

# In your script:
SOC_threshold = 30% (triggers charging)
SOC_target = 70% (target after charging)
```

**Example for eRickshaw:**
```
Battery capacity = 7200 Wh = 7.2 kWh
Current SOC = 30%
Target SOC = 70%

E_needed = (70 - 30) / 100 × 7.2 kWh
         = 0.40 × 7.2
         = 2.88 kWh
```

### **B. Charging Time Calculation**

```python
# From calculate_charge_time() function:

t_charge = E_needed / (P_station × η)

Where:
- t_charge = Charging duration (hours)
- E_needed = Energy required (kWh)
- P_station = Station power (kW)
- η = Efficiency (0.95)
```

**Example:**
```
E_needed = 2.88 kWh
P_station = 20 kW
η = 0.95

t_charge = 2.88 / (20 × 0.95)
         = 2.88 / 19
         = 0.1516 hours
         = 0.1516 × 3600 seconds
         = 545.7 seconds ≈ 9.1 minutes

But limited by MAX_CHARGE_TIME = 300 seconds = 5 minutes
So actual: 300 seconds
```

### **C. Actual Energy Delivered**

```python
# Energy delivered during actual charging time

E_delivered = P_station × η × t_actual

Where t_actual = min(t_calculated, MAX_CHARGE_TIME)
```

**Example:**
```
t_actual = 300 seconds = 0.0833 hours
P_station = 20 kW
η = 0.95

E_delivered = 20 × 0.95 × 0.0833
            = 1.58 kWh

Final SOC = Initial SOC + (E_delivered / Battery_capacity) × 100
          = 30% + (1.58 / 7.2) × 100
          = 30% + 21.9%
          = 51.9%
```

---

## **4. LOAD PROFILE METRICS**

### **A. Peak Load**
```python
Peak_load = max(total_power_demand_kW) across all timesteps

# This represents maximum simultaneous charging power
```

**Impact:**
- Grid infrastructure sizing
- Transformer capacity requirements
- Peak demand charges

### **B. Average Load**
```python
Average_load = mean(total_power_demand_kW) for timesteps where load > 0

# Average power when any charging is happening
```

### **C. Total Energy Consumption**
```python
# Integration of power over time

E_total = Σ[P(t) × Δt] for all timesteps

# In your script (timestep = 1 second):
E_total_kWh = Σ(total_power_demand_kW) / 3600

# Because: kW × seconds / 3600 = kWh
```

**Example:**
```
Timestep 1: 100 kW for 1 second = 100/3600 = 0.0278 kWh
Timestep 2: 150 kW for 1 second = 150/3600 = 0.0417 kWh
...
Total over 600 seconds = sum all / 3600
```

### **D. Load Factor**
```python
Load_factor = (Average_load / Peak_load) × 100%

# Measures how efficiently the charging infrastructure is used
```

**Interpretation:**
- **High load factor (>70%)**: Consistent utilization, efficient
- **Low load factor (<40%)**: Sporadic use, underutilized capacity
- **Your case**: Depends on traffic patterns and SOC distribution

---

## **5. REAL-WORLD EXAMPLE FROM YOUR SIMULATION**

Let's analyze a specific moment:

### **Scenario: Timestep = 250 seconds**

```
CSV Data:
timestep_sec = 250
total_vehicles_charging = 6
total_power_demand_kW = 130.0
total_power_demand_MW = 0.130

Station breakdown:
pa_2_vehicles = 1,  pa_2_power_kW = 20.0
pa_3_vehicles = 0,  pa_3_power_kW = 0.0
pa_6_vehicles = 2,  pa_6_power_kW = 50.0
pa_7_vehicles = 0,  pa_7_power_kW = 0.0
pa_8_vehicles = 1,  pa_8_power_kW = 25.0
pa_2_rev_vehicles = 0, pa_2_rev_power_kW = 0.0
pa_3_rev_vehicles = 1, pa_3_rev_power_kW = 20.0
pa_6_rev_vehicles = 1, pa_6_rev_power_kW = 25.0
pa_7_rev_vehicles = 0, pa_7_rev_power_kW = 0.0
pa_8_rev_vehicles = 0, pa_8_rev_power_kW = 0.0
```

**Analysis:**

1. **Active Stations**: 5 out of 10
2. **Total Load**: 130 kW = 0.13 MW
3. **Per-station loads**:
   - Forward direction: 20 + 50 + 25 = 95 kW
   - Reverse direction: 20 + 25 = 45 kW

4. **Energy consumed in this 1 second**:
   ```
   E = 130 kW × (1/3600) h = 0.0361 kWh = 36.1 Wh
   ```

5. **If this continues for 5 minutes**:
   ```
   E = 130 kW × (300/3600) h = 10.83 kWh
   ```

---

## **6. COMPLETE SIMULATION METRICS**

### **From 600-second simulation:**

```python
# Aggregate calculations:

1. Peak Load:
   Peak = max(all total_power_demand_kW values)
   
2. Average Active Load:
   Avg = mean(total_power_demand_kW where > 0)
   
3. Total Energy:
   E_total = sum(total_power_demand_kW) / 3600 kWh
   
4. Load Factor:
   LF = (Avg / Peak) × 100%
   
5. Utilization Rate:
   UR = (timesteps with charging / total timesteps) × 100%
   
6. Average Vehicles Charging:
   Avg_vehicles = mean(total_vehicles_charging where > 0)
   
7. Peak Simultaneous Charging:
   Peak_vehicles = max(total_vehicles_charging)
```

---

## **7. VEHICLE-LEVEL ENERGY FLOW**

### **Complete Energy Balance for One Vehicle:**

```python
# Starting state
Initial_SOC = 32%  (example: triggers charging at < 30%)
Battery_capacity = 7200 Wh
Initial_energy = 0.32 × 7200 = 2304 Wh

# Charging phase
Charging_duration = 300 seconds = 5 minutes
Station_power = 20 kW = 20000 W
Efficiency = 0.95

Energy_from_grid = 20000 W × 300 s = 6,000,000 J = 1666.7 Wh
Energy_to_battery = 1666.7 × 0.95 = 1583.3 Wh

# Final state
Final_energy = 2304 + 1583.3 = 3887.3 Wh
Final_SOC = 3887.3 / 7200 × 100 = 54%

# Energy losses
Losses = 1666.7 - 1583.3 = 83.4 Wh (5% loss)
```

---

## **8. GRID IMPACT ANALYSIS**

### **A. Instantaneous Grid Load**
```
At any moment t:
Grid_load(t) = Baseline_load + Σ(Charging_load)
```

### **B. Daily Energy Consumption**
```python
# If this pattern repeats:

Daily_charging_sessions = (24 hours × 3600 s) / 600 s × sessions_per_period
Daily_energy = Total_energy_per_600s × scaling_factor
```

### **C. Peak Demand Cost**
```
Demand_charge = Peak_kW × Rate_per_kW
```

**Example:**
```
If Peak = 200 kW
Demand rate = $15/kW/month
Monthly demand charge = 200 × $15 = $3,000
```

---

## **9. KEY FORMULAS SUMMARY**

| Metric | Formula | Units |
|--------|---------|-------|
| **Instantaneous Load** | `Σ(n_i × P_i)` | kW |
| **Energy Needed** | `ΔSOC × Capacity / 100` | kWh |
| **Charge Time** | `E_needed / (P × η)` | hours |
| **Energy Delivered** | `P × η × t` | kWh |
| **SOC Change** | `(E_delivered / Capacity) × 100` | % |
| **Total Energy** | `Σ(P(t) × Δt)` | kWh |
| **Load Factor** | `(P_avg / P_peak) × 100` | % |

---

## **10. INTERPRETATION OF YOUR CSV OUTPUT**

Each row represents **1 second** of simulation:

```csv
timestep_sec,total_vehicles_charging,total_power_demand_kW,...
1.0,0,0.0,...              ← No charging yet
50.0,2,45.0,...            ← 2 vehicles, 45 kW total
150.0,5,115.0,...          ← 5 vehicles, 115 kW total
300.0,8,180.0,...          ← Peak: 8 vehicles, 180 kW
600.0,3,65.0,...           ← End: 3 vehicles still charging
```

**What this tells you:**
- Charging demand varies over time
- Peak occurs when most vehicles charge simultaneously
- Grid must handle peak, not average
- Total energy = integration under the load curve

---
