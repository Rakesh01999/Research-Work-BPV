# Understanding Your CSV Rows - Detailed Explanation

## 📊 Sample Rows Breakdown

### Row 577 - Easy Bike Vehicle
```csv
577, 9, easyBike_034, 13.89, 0.19, 34.84, 18.73, E0_0, driving, none, 0, 0, 0, 0, 98, 48, 29, 13, 7.72, 26.19, 11.6, 30.33, 23.69, 307.7, 640
```

### Row 578 - E-Rickshaw Vehicle
```csv
578, 9, eRickshaw_026, 11.49, 0.44, 33.41, 95.36, E9_1, driving, none, 0, 0, 0, 0, 97, 50, 28, 11, 7.69, 26.22, 11.67, 29.69, 23.71, 301.7, 620
```

---

## 🔍 Column-by-Column Explanation

### 1️⃣ Identity & Time Features

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **1** | `timestep_sec` | 577 | 578 | **Simulation second** - Row 577 is at 577 seconds (~9.6 min), Row 578 is at 578 seconds |
| **2** | `minute_of_hour` | 9 | 9 | **Minute within the hour** - Both at 9th minute (0:09:37 and 0:09:38) |
| **3** | `vehicle_id` | easyBike_034 | eRickshaw_026 | **Vehicle type** - One Easy Bike, one E-Rickshaw |

---

### 2️⃣ Vehicle-Specific Metrics (Individual Vehicle Data)

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **4** | `speed_ms` | 13.89 m/s | 11.49 m/s | **Current speed** - Easy Bike going faster (~50 km/h vs ~41 km/h) |
| **5** | `acceleration_ms2` | 0.19 m/s² | 0.44 m/s² | **Acceleration** - E-Rickshaw accelerating faster |
| **6** | `soc_percent` | 34.84% | 33.41% | **Battery level** - Both have low battery (~34% and ~33%) |
| **7** | `energy_consumed_Wh` | 18.73 Wh | 95.36 Wh | **Energy used** - E-Rickshaw consumed much more (5x more) |
| **8** | `lane_id` | E0_0 | E9_1 | **Current lane** - Different roads (Edge 0 lane 0 vs Edge 9 lane 1) |
| **9** | `status` | driving | driving | **Vehicle status** - Both are actively driving (not charging/waiting) |

#### 📝 Notes on Vehicle Data:
- **Easy Bike (034)**: Going fast (50 km/h), low battery (34.8%), used only 18.73 Wh so far
- **E-Rickshaw (026)**: Going slower (41 km/h), low battery (33.4%), used 95.36 Wh (heavier vehicle = more energy)

---

### 3️⃣ Station Context (Where Vehicle Is)

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **10** | `current_station_id` | none | none | **At charging station?** - Both NOT at any station |
| **11** | `station_load_kW` | 0 | 0 | **Station power** - Not applicable (not at station) |
| **12** | `station_vehicles_charging` | 0 | 0 | **Vehicles charging there** - Not applicable |
| **13** | `station_queue_length` | 0 | 0 | **Queue at station** - Not applicable |
| **14** | `station_utilization_percent` | 0 | 0 | **Station occupancy** - Not applicable |

#### 📝 Notes on Station Data:
- Both vehicles are **driving on the road**, not at any charging station
- All station-related columns are 0 or "none" because they're not at a station
- These columns would show values if the vehicle was at a charging station

---

### 4️⃣ System-Wide Context (Global Traffic State)

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **15** | `system_total_vehicles` | 98 | 97 | **Total vehicles in simulation** - Decreased by 1 (one vehicle left) |
| **16** | `system_moving_vehicles` | 48 | 50 | **Vehicles driving** - Increased from 48 to 50 |
| **17** | `system_charging_vehicles` | 29 | 28 | **Vehicles charging** - Decreased from 29 to 28 |
| **18** | `system_waiting_vehicles` | 13 | 11 | **Vehicles in queue** - Decreased from 13 to 11 |

#### 📊 System State Analysis:

**At Second 577 (Row 577):**
- 98 total vehicles
- 48 driving + 29 charging + 13 waiting = 90 vehicles accounted for
- 8 vehicles in other states (stopped, etc.)

**At Second 578 (Row 578):**
- 97 total vehicles (1 vehicle completed trip and left)
- 50 driving + 28 charging + 11 waiting = 89 vehicles accounted for
- 8 vehicles in other states

**What happened between seconds 577→578:**
- ✅ 1 vehicle left the simulation (98→97 total)
- ✅ 2 more started driving (48→50 moving)
- ✅ 1 vehicle stopped charging (29→28 charging)
- ✅ 2 vehicles left queues (13→11 waiting)

---

### 5️⃣ System Averages (Traffic Statistics)

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **19** | `system_avg_speed_ms` | 7.72 m/s | 7.69 m/s | **Average speed (all vehicles)** - ~27.8 km/h |
| **20** | `system_avg_soc_percent` | 26.19% | 26.22% | **Average battery (all vehicles)** - System-wide ~26% |
| **21** | `system_avg_moving_speed_ms` | 11.6 m/s | 11.67 m/s | **Average speed (driving only)** - ~41.9 km/h |
| **22** | `system_avg_moving_soc_percent` | 30.33% | 29.69% | **Average battery (driving only)** - Moving vehicles ~30% |
| **23** | `system_avg_charging_soc_percent` | 23.69% | 23.71% | **Average battery (charging)** - Charging vehicles ~24% |
| **24** | `system_avg_charging_duration_sec` | 307.7 s | 301.7 s | **Average charging time** - ~5 minutes per vehicle |

#### 📊 System Statistics Analysis:

**Speed Context:**
- System average: ~7.7 m/s (includes stopped/charging vehicles)
- Moving vehicles only: ~11.6 m/s (much faster, makes sense)
- Our Easy Bike (13.89 m/s) is **faster than average**
- Our E-Rickshaw (11.49 m/s) is **close to average**

**Battery Context:**
- System average SOC: ~26% (many vehicles have low battery)
- Moving vehicles: ~30% SOC (driving vehicles have slightly more battery)
- Charging vehicles: ~24% SOC (vehicles at stations are lower, why they're charging)
- Our Easy Bike (34.84%) is **above average** ✅
- Our E-Rickshaw (33.41%) is **above average** ✅

**Charging Context:**
- Average charging session: ~5 minutes (307 seconds)
- 28-29 vehicles charging simultaneously
- 11-13 vehicles waiting in queues

---

### 6️⃣ Target Variable (What We're Predicting)

| Column # | Name | Row 577 | Row 578 | Meaning |
|----------|------|---------|---------|---------|
| **25** | `system_total_load_kW` | **640 kW** | **620 kW** | **TOTAL CHARGING POWER** - System-wide electricity demand |

#### ⚡ Load Analysis:

**At Second 577:**
- 29 vehicles charging
- Total power: 640 kW
- Average per vehicle: ~22 kW per vehicle

**At Second 578:**
- 28 vehicles charging (1 less)
- Total power: 620 kW (decreased by 20 kW)
- Average per vehicle: ~22 kW per vehicle

**Load Change:**
- Decreased from 640 kW → 620 kW (drop of 20 kW)
- Makes sense: 1 less vehicle charging
- This is what your ML model will predict!

---

## 🎯 Key Insights from These Rows

### Vehicle Level:
1. **Easy Bike 034**:
   - Fast moving (50 km/h)
   - Battery getting low (34.8%)
   - Efficient (only used 18.73 Wh)
   - May need charging soon

2. **E-Rickshaw 026**:
   - Moderate speed (41 km/h)
   - Battery also low (33.4%)
   - Heavy energy user (95.36 Wh)
   - Likely needs charging soon

### System Level:
1. **Traffic State**:
   - Peak time: 98-97 vehicles active
   - About 50% driving, 30% charging, 11% waiting
   - System is busy but not overloaded

2. **Charging Infrastructure**:
   - 28-29 stations occupied
   - ~640 kW total power draw
   - ~5 minute average charging time
   - Some queue pressure (11-13 waiting)

3. **Energy Pattern**:
   - Most vehicles have low battery (~26% average)
   - Charging demand is high (640 kW)
   - System is in peak charging period

---

## 📈 ML Model Context

### These rows help the model learn:

**Input Features (X):**
- Time: 9th minute of hour
- Vehicle speed: 13.89 m/s and 11.49 m/s
- Battery level: 34.84% and 33.41%
- System state: 98-97 vehicles, 48-50 moving, 29-28 charging
- Average conditions: ~26% SOC, ~7.7 m/s speed

**Target Variable (y):**
- Load: 640 kW → 620 kW

**Model learns:**
- When 29 vehicles charge → ~640 kW
- When 28 vehicles charge → ~620 kW
- Each vehicle ≈ 20-22 kW on average
- Time of day, vehicle mix, SOC levels all affect total load

---

## 🔍 Summary Table

| Aspect | Row 577 | Row 578 | Change |
|--------|---------|---------|--------|
| **Time** | 577 sec (9:37) | 578 sec (9:38) | +1 sec |
| **This Vehicle** | Easy Bike, 50 km/h, 34.8% SOC | E-Rickshaw, 41 km/h, 33.4% SOC | Different vehicles |
| **Total Vehicles** | 98 | 97 | -1 |
| **Charging** | 29 vehicles | 28 vehicles | -1 |
| **System Load** | **640 kW** | **620 kW** | **-20 kW** |
| **Avg Battery** | 26.19% | 26.22% | Stable |
| **Avg Speed** | 7.72 m/s | 7.69 m/s | Stable |

---

## 💡 Bottom Line

These two rows represent:
- **Two different vehicles** at consecutive seconds
- **Both have low battery** (~34%) and may need charging soon
- **System is in high demand**: 28-29 vehicles charging = 620-640 kW load
- **Your ML model learns**: How vehicle count, battery levels, time, and traffic patterns predict the total charging load

This data format is perfect for supervised learning where you predict `system_total_load_kW` based on all the other features! 🎯
