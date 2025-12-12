

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

