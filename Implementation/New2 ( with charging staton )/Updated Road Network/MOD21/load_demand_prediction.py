"""
Enhanced Smart Charging Simulation - ML-Ready Single CSV Output
For: Simulation-Based Analysis and Machine Learning Prediction of Electric Vehicle 
     Charging Load Demand in Khulna City, Bangladesh
     
Output: Single comprehensive CSV with all important features for ML analysis
"""

import os
import sys
import traceback
from datetime import datetime
from collections import defaultdict, deque

try:
    import traci
    print("✓ TraCI imported successfully")
except ImportError:
    print("✗ ERROR: TraCI not found! Install: pip install traci")
    sys.exit(1)

import pandas as pd
import numpy as np


class SmartChargingStationMonitor:
    
    # ========== Configuration ==========
    SOC_THRESHOLD = 30.0
    SOC_TARGET = 70.0
    MIN_CHARGE_TIME = 30
    MAX_CHARGE_TIME = 300
    
    # Charging stations (matching your XML with separate charging/waiting slots)
    CHARGING_STATIONS = {
        'pa_2': {
            'charging_area': 'pa_2_charging',
            'waiting_area': 'pa_2_waiting',
            'lane': 'E0_0', 
            'edge': 'E0', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 3
        },
        'pa_2_rev': {
            'charging_area': 'pa_2_rev_charging',
            'waiting_area': 'pa_2_rev_waiting',
            'lane': '-E0_0', 
            'edge': '-E0', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 3
        },
        'pa_3': {
            'charging_area': 'pa_3_charging',
            'waiting_area': 'pa_3_waiting',
            'lane': 'E1_0', 
            'edge': 'E1', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 3
        },
        'pa_3_rev': {
            'charging_area': 'pa_3_rev_charging',
            'waiting_area': 'pa_3_rev_waiting',
            'lane': '-E1_0', 
            'edge': '-E1', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 3
        },
        'pa_6': {
            'charging_area': 'pa_6_charging',
            'waiting_area': 'pa_6_waiting',
            'lane': 'E5_0', 
            'edge': 'E5', 
            'power_kW': 25.0, 
            'efficiency': 0.95, 
            'charging_slots': 5, 
            'waiting_slots': 3
        },
        'pa_6_rev': {
            'charging_area': 'pa_6_rev_charging',
            'waiting_area': 'pa_6_rev_waiting',
            'lane': '-E5_0', 
            'edge': '-E5', 
            'power_kW': 25.0, 
            'efficiency': 0.95, 
            'charging_slots': 5, 
            'waiting_slots': 3
        },
        'pa_7': {
            'charging_area': 'pa_7_charging',
            'waiting_area': 'pa_7_waiting',
            'lane': 'E6_0', 
            'edge': 'E6', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 2
        },
        'pa_7_rev': {
            'charging_area': 'pa_7_rev_charging',
            'waiting_area': 'pa_7_rev_waiting',
            'lane': '-E6_0', 
            'edge': '-E6', 
            'power_kW': 20.0, 
            'efficiency': 0.95, 
            'charging_slots': 4, 
            'waiting_slots': 2
        },
        'pa_8': {
            'charging_area': 'pa_8_charging',
            'waiting_area': 'pa_8_waiting',
            'lane': 'E7_0', 
            'edge': 'E7', 
            'power_kW': 25.0, 
            'efficiency': 0.95, 
            'charging_slots': 5, 
            'waiting_slots': 3
        },
        'pa_8_rev': {
            'charging_area': 'pa_8_rev_charging',
            'waiting_area': 'pa_8_rev_waiting',
            'lane': '-E7_0', 
            'edge': '-E7', 
            'power_kW': 25.0, 
            'efficiency': 0.95, 
            'charging_slots': 5, 
            'waiting_slots': 3
        }
    }


    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Main data structure for ML-ready output
        self.ml_data = []
        
        # Vehicle tracking
        self.vehicle_states = {}
        self.initial_soc = {}
        self.charging_start_times = {}
        self.waiting_start_times = {}
        
        # Station tracking with separate charging/waiting
        self.station_charging_slots = {}
        self.station_waiting_queue = {}
        self.currently_charging = {}
        self.currently_waiting = {}
        
        # Initialize station tracking
        for station_id in self.CHARGING_STATIONS.keys():
            self.station_charging_slots[station_id] = set()
            self.station_waiting_queue[station_id] = deque()
        
        # Historical tracking for features
        self.station_hourly_demand = defaultdict(lambda: defaultdict(float))
        self.station_hourly_vehicles = defaultdict(lambda: defaultdict(int))
        
        print("✓ ML-Ready Charging Station Monitor Initialized")
        print(f"  SOC: {self.SOC_THRESHOLD}% → {self.SOC_TARGET}%")
        total_charging = sum(s['charging_slots'] for s in self.CHARGING_STATIONS.values())
        total_waiting = sum(s['waiting_slots'] for s in self.CHARGING_STATIONS.values())
        print(f"  Stations: {len(self.CHARGING_STATIONS)} ({total_charging} charging + {total_waiting} waiting slots)")
        print(f"  Output: Single comprehensive CSV for ML analysis")
    
    def get_battery_info(self, vid):
        """Get battery information for a vehicle"""
        try:
            try:
                charge = traci.vehicle.getParameter(vid, "device.battery.chargeLevel")
                capacity = traci.vehicle.getParameter(vid, "device.battery.capacity")
                energy = traci.vehicle.getParameter(vid, "device.battery.totalEnergyConsumed")
            except:
                charge = traci.vehicle.getParameter(vid, "actualBatteryCapacity") or \
                        traci.vehicle.getParameter(vid, "device.battery.actualBatteryCapacity")
                capacity = traci.vehicle.getParameter(vid, "maximumBatteryCapacity") or \
                          traci.vehicle.getParameter(vid, "device.battery.maximumBatteryCapacity")
                try:
                    energy = traci.vehicle.getParameter(vid, "device.battery.totalEnergyConsumed")
                except:
                    energy = 0.0
            
            c = float(charge) if charge else 0.0
            cap = float(capacity) if capacity else 0.0
            e = float(energy) if energy else 0.0
            soc = (c / cap * 100.0) if cap > 0 else 0.0
            
            return {'charge_Wh': c, 'capacity_Wh': cap, 'soc_percent': soc, 'energy_consumed_Wh': e}
        except:
            return None
    
    def get_charging_station_id(self, vid):
        """Detect if vehicle is at a charging station"""
        if vid in self.currently_charging:
            return self.currently_charging[vid]
        if vid in self.currently_waiting:
            return self.currently_waiting[vid]
        
        try:
            parking_id = traci.vehicle.getParameter(vid, "parking")
            if parking_id:
                for station_id, config in self.CHARGING_STATIONS.items():
                    if parking_id in [config['charging_area'], config['waiting_area']]:
                        return station_id
        except:
            pass
        return None
    
    def assign_to_charging_station(self, vid, station_id):
        """Assign vehicle to charging or waiting area"""
        config = self.CHARGING_STATIONS[station_id]
        
        # Check charging slots first
        if len(self.station_charging_slots[station_id]) < config['charging_slots']:
            self.station_charging_slots[station_id].add(vid)
            self.currently_charging[vid] = station_id
            self.charging_start_times[vid] = traci.simulation.getTime()
            return 'charging'
        else:
            # Add to waiting queue
            if vid not in self.station_waiting_queue[station_id]:
                self.station_waiting_queue[station_id].append(vid)
                self.currently_waiting[vid] = station_id
                self.waiting_start_times[vid] = traci.simulation.getTime()
            return 'waiting'
    
    def release_from_station(self, vid, station_id):
        """Release vehicle and promote from queue if available"""
        config = self.CHARGING_STATIONS[station_id]
        
        # Release from charging
        if vid in self.station_charging_slots[station_id]:
            self.station_charging_slots[station_id].remove(vid)
            if vid in self.currently_charging:
                del self.currently_charging[vid]
            if vid in self.charging_start_times:
                del self.charging_start_times[vid]
            
            # Promote from waiting queue
            if len(self.station_waiting_queue[station_id]) > 0:
                next_vid = self.station_waiting_queue[station_id].popleft()
                self.station_charging_slots[station_id].add(next_vid)
                self.currently_charging[next_vid] = station_id
                self.charging_start_times[next_vid] = traci.simulation.getTime()
                if next_vid in self.currently_waiting:
                    del self.currently_waiting[next_vid]
        
        # Release from waiting
        elif vid in self.currently_waiting:
            if vid in self.station_waiting_queue[station_id]:
                self.station_waiting_queue[station_id].remove(vid)
            del self.currently_waiting[vid]
            if vid in self.waiting_start_times:
                del self.waiting_start_times[vid]
    
    def reroute_and_schedule_charge(self, vid, station_id, battery_info):
        """Reroute vehicle to charging station"""
        config = self.CHARGING_STATIONS[station_id]
        
        try:
            status = self.assign_to_charging_station(vid, station_id)
            
            if status == 'charging':
                # Direct to charging area
                traci.vehicle.setParkingAreaStop(
                    vid, config['charging_area'],
                    duration=self.MIN_CHARGE_TIME,
                    flags=traci.constants.STOP_PARKING
                )
            elif status == 'waiting':
                # Direct to waiting area
                traci.vehicle.setParkingAreaStop(
                    vid, config['waiting_area'],
                    duration=60,
                    flags=traci.constants.STOP_PARKING
                )
        except Exception as e:
            pass
    
    def get_time_features(self, timestep_sec):
        """Extract time-based features"""
        hours = (timestep_sec / 3600.0) % 24
        minutes = (timestep_sec / 60.0) % 60
        
        return {
            'hour_of_day': int(hours),
            'minute_of_hour': int(minutes),
            'is_peak_hour': 1 if (7 <= hours < 10) or (17 <= hours < 20) else 0,
            'is_business_hour': 1 if 8 <= hours < 18 else 0,
            'time_period': self._get_time_period(hours)
        }
    
    def _get_time_period(self, hour):
        """Categorize time into periods"""
        if 0 <= hour < 6:
            return 'night'
        elif 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        else:
            return 'evening'
    
    def calculate_station_features(self, station_id, timestep_sec):
        """Calculate features for a specific station"""
        config = self.CHARGING_STATIONS[station_id]
        
        vehicles_charging = len(self.station_charging_slots[station_id])
        vehicles_waiting = len(self.station_waiting_queue[station_id])
        
        # Utilization
        charging_utilization = (vehicles_charging / config['charging_slots']) * 100
        waiting_utilization = (vehicles_waiting / config['waiting_slots']) * 100
        
        # Current power demand for this station
        power_demand = vehicles_charging * config['power_kW']
        
        # Queue length
        queue_length = vehicles_waiting
        
        # Availability
        charging_slots_available = config['charging_slots'] - vehicles_charging
        waiting_slots_available = config['waiting_slots'] - vehicles_waiting
        
        return {
            'vehicles_charging': vehicles_charging,
            'vehicles_waiting': vehicles_waiting,
            'charging_utilization_percent': round(charging_utilization, 2),
            'waiting_utilization_percent': round(waiting_utilization, 2),
            'power_demand_kW': round(power_demand, 2),
            'queue_length': queue_length,
            'charging_slots_available': charging_slots_available,
            'waiting_slots_available': waiting_slots_available,
            'total_slots': config['charging_slots'] + config['waiting_slots'],
            'station_power_capacity_kW': config['power_kW'],
            'station_charging_capacity': config['charging_slots']
        }
    
    def calculate_system_features(self, timestep_sec):
        """Calculate system-wide features"""
        total_vehicles_charging = sum(len(slots) for slots in self.station_charging_slots.values())
        total_vehicles_waiting = sum(len(queue) for queue in self.station_waiting_queue.values())
        
        # Total power demand across all stations
        total_power_demand = 0
        for station_id in self.CHARGING_STATIONS.keys():
            vehicles_at_station = len(self.station_charging_slots[station_id])
            power = vehicles_at_station * self.CHARGING_STATIONS[station_id]['power_kW']
            total_power_demand += power
        
        # System capacity
        total_charging_capacity = sum(s['charging_slots'] for s in self.CHARGING_STATIONS.values())
        total_waiting_capacity = sum(s['waiting_slots'] for s in self.CHARGING_STATIONS.values())
        
        system_utilization = (total_vehicles_charging / total_charging_capacity) * 100 if total_charging_capacity > 0 else 0
        
        return {
            'total_vehicles_charging': total_vehicles_charging,
            'total_vehicles_waiting': total_vehicles_waiting,
            'total_power_demand_kW': round(total_power_demand, 2),
            'system_charging_utilization_percent': round(system_utilization, 2),
            'total_active_vehicles': len(traci.vehicle.getIDList()),
            'total_charging_capacity': total_charging_capacity,
            'total_waiting_capacity': total_waiting_capacity
        }
    
    def collect_data(self, timestep_sec):
        """Collect comprehensive ML-ready data at each timestep"""
        vehicle_ids = traci.vehicle.getIDList()
        
        # Get time features
        time_features = self.get_time_features(timestep_sec)
        
        # Get system-wide features
        system_features = self.calculate_system_features(timestep_sec)
        
        # Collect station-level data
        for station_id in self.CHARGING_STATIONS.keys():
            station_features = self.calculate_station_features(station_id, timestep_sec)
            
            # Combine all features for this station at this timestep
            record = {
                # Temporal features
                'timestep_sec': timestep_sec,
                'hour_of_day': time_features['hour_of_day'],
                'minute_of_hour': time_features['minute_of_hour'],
                'is_peak_hour': time_features['is_peak_hour'],
                'is_business_hour': time_features['is_business_hour'],
                'time_period': time_features['time_period'],
                
                # Station identification
                'station_id': station_id,
                'station_edge': self.CHARGING_STATIONS[station_id]['edge'],
                'station_power_capacity_kW': station_features['station_power_capacity_kW'],
                'station_charging_slots': station_features['station_charging_capacity'],
                
                # Station load features (TARGET VARIABLES)
                'station_power_demand_kW': station_features['power_demand_kW'],
                'station_vehicles_charging': station_features['vehicles_charging'],
                
                # Station utilization features
                'station_charging_utilization_percent': station_features['charging_utilization_percent'],
                'station_waiting_utilization_percent': station_features['waiting_utilization_percent'],
                'station_vehicles_waiting': station_features['vehicles_waiting'],
                'station_queue_length': station_features['queue_length'],
                'station_charging_slots_available': station_features['charging_slots_available'],
                'station_waiting_slots_available': station_features['waiting_slots_available'],
                
                # System-wide features
                'system_total_power_demand_kW': system_features['total_power_demand_kW'],
                'system_total_vehicles_charging': system_features['total_vehicles_charging'],
                'system_total_vehicles_waiting': system_features['total_vehicles_waiting'],
                'system_charging_utilization_percent': system_features['system_charging_utilization_percent'],
                'system_total_active_vehicles': system_features['total_active_vehicles'],
                
                # Derived features for ML
                'load_per_vehicle_kW': round(station_features['power_demand_kW'] / station_features['vehicles_charging'], 2) if station_features['vehicles_charging'] > 0 else 0,
                'congestion_ratio': round((station_features['vehicles_charging'] + station_features['vehicles_waiting']) / station_features['total_slots'], 2) if station_features['total_slots'] > 0 else 0,
                'demand_to_capacity_ratio': round(station_features['power_demand_kW'] / (station_features['station_power_capacity_kW'] * station_features['station_charging_capacity']), 2) if (station_features['station_power_capacity_kW'] * station_features['station_charging_capacity']) > 0 else 0
            }
            
            self.ml_data.append(record)
        
        # Handle vehicle charging logic
        for v in vehicle_ids:
            try:
                b = self.get_battery_info(v)
                if not b:
                    continue
                
                # Initialize SOC tracking
                if v not in self.initial_soc:
                    self.initial_soc[v] = b['soc_percent']
                
                # Check if at a station
                station = self.get_charging_station_id(v)
                
                # Charging completion check
                if v in self.currently_charging:
                    if b['soc_percent'] >= self.SOC_TARGET:
                        self.release_from_station(v, self.currently_charging[v])
                        try:
                            traci.vehicle.resume(v)
                        except:
                            pass
                
                # Low SOC routing
                elif b['soc_percent'] < self.SOC_THRESHOLD and v not in self.vehicle_states:
                    self.vehicle_states[v] = 'needs_charge'
                    
                    # Find best station
                    best_station = None
                    min_queue = float('inf')
                    
                    for sid, cfg in self.CHARGING_STATIONS.items():
                        total_occupied = len(self.station_charging_slots[sid]) + len(self.station_waiting_queue[sid])
                        if total_occupied < min_queue:
                            min_queue = total_occupied
                            best_station = sid
                    
                    if best_station:
                        self.reroute_and_schedule_charge(v, best_station, b)
            except:
                continue
    
    def run_simulation(self, gui=True, max_time=600):
        """Run the SUMO simulation"""
        print(f"\n{'='*70}\nML-READY CHARGING SIMULATION\n{'='*70}")
        
        cmd = ["sumo-gui" if gui else "sumo", "-c", self.sumocfg, "--start", "--quit-on-end"]
        
        try:
            traci.start(cmd)
            print("✓ Started\n")
        except Exception as e:
            print(f"✗ Failed: {e}")
            return False
        
        try:
            t = 0
            while traci.simulation.getMinExpectedNumber() > 0 and t < max_time:
                traci.simulationStep()
                t = traci.simulation.getTime()
                
                # Collect data every second
                if int(t) == t:
                    self.collect_data(t)
                
                # Progress update every 30 seconds
                if int(t) % 30 == 0 and t > 0:
                    active = len(traci.vehicle.getIDList())
                    chrg = len(self.currently_charging)
                    wait = sum(len(q) for q in self.station_waiting_queue.values())
                    
                    if len(self.ml_data) > 0:
                        recent_data = [d for d in self.ml_data if d['timestep_sec'] == t]
                        total_load = sum(d['station_power_demand_kW'] for d in recent_data)
                        print(f"⏱️ {int(t)}s | Active:{active} Charging:{chrg} Waiting:{wait} Load:{total_load:.1f}kW")
            
            traci.close()
            print(f"\n✓ Simulation completed at {t}s")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            try:
                traci.close()
            except:
                pass
            return False
    
    def export_ml_dataset(self):
        """Export single comprehensive ML-ready CSV"""
        print(f"\n{'='*70}\nEXPORTING ML DATASET\n{'='*70}")
        
        if not self.ml_data:
            print("✗ No data collected!")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(self.ml_data)
        
        # Add rolling/lagging features for better predictions
        print("Creating advanced features...")
        
        # Sort by station and time
        df = df.sort_values(['station_id', 'timestep_sec'])
        
        # Create lag features (previous timestep values)
        for col in ['station_power_demand_kW', 'station_vehicles_charging', 'system_total_power_demand_kW']:
            df[f'{col}_lag1'] = df.groupby('station_id')[col].shift(1)
            df[f'{col}_lag5'] = df.groupby('station_id')[col].shift(5)
        
        # Create rolling averages
        for col in ['station_power_demand_kW', 'station_vehicles_charging']:
            df[f'{col}_rolling_avg_5min'] = df.groupby('station_id')[col].rolling(window=5, min_periods=1).mean().reset_index(0, drop=True)
            df[f'{col}_rolling_avg_10min'] = df.groupby('station_id')[col].rolling(window=10, min_periods=1).mean().reset_index(0, drop=True)
        
        # Fill NaN values from lag features
        df = df.fillna(0)
        
        # Create timestamp for filename
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'ev_charging_ml_dataset_{ts}.csv'
        filepath = os.path.join(self.output_folder, filename)
        
        # Save to CSV
        df.to_csv(filepath, index=False)
        
        print(f"✓ ML Dataset: {filepath}")
        print(f"  Records: {len(df):,}")
        print(f"  Features: {len(df.columns)}")
        print(f"  Stations: {df['station_id'].nunique()}")
        print(f"  Time Range: {df['timestep_sec'].min():.0f}s - {df['timestep_sec'].max():.0f}s")
        
        # Summary statistics
        print(f"\n📊 DATASET SUMMARY:")
        print(f"  Peak System Load: {df['system_total_power_demand_kW'].max():.2f} kW")
        print(f"  Average System Load: {df['system_total_power_demand_kW'].mean():.2f} kW")
        print(f"  Max Vehicles Charging: {int(df['system_total_vehicles_charging'].max())}")
        print(f"  Average Station Utilization: {df['station_charging_utilization_percent'].mean():.1f}%")
        
        # Feature importance info
        print(f"\n🎯 KEY FEATURES FOR ML:")
        print(f"  Target Variables:")
        print(f"    - station_power_demand_kW (main target)")
        print(f"    - station_vehicles_charging")
        print(f"  Temporal Features:")
        print(f"    - hour_of_day, is_peak_hour, time_period")
        print(f"  Station Features:")
        print(f"    - station_charging_utilization_percent")
        print(f"    - station_queue_length")
        print(f"    - congestion_ratio")
        print(f"  System Features:")
        print(f"    - system_total_power_demand_kW")
        print(f"    - system_charging_utilization_percent")
        print(f"  Lag Features:")
        print(f"    - *_lag1, *_lag5, *_rolling_avg_*")
        
        print(f"\n✓ Ready for ML analysis!")
        print(f"{'='*70}\n")
        
        return filepath


def main():
    """Main execution function"""
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT = 'simulation_outputs'
    GUI = True
    MAX_TIME = 600
    
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: {SUMOCFG} not found!")
        return
    
    print("="*70)
    print("ELECTRIC VEHICLE CHARGING LOAD DEMAND SIMULATION")
    print("Khulna City, Bangladesh")
    print("="*70)
    
    sim = SmartChargingStationMonitor(sumocfg=SUMOCFG, output_folder=OUTPUT)
    
    if sim.run_simulation(gui=GUI, max_time=MAX_TIME):
        filepath = sim.export_ml_dataset()
        print("✓ SIMULATION COMPLETE!")
        print(f"✓ ML Dataset saved: {filepath}")
    else:
        print("✗ SIMULATION FAILED!")


if __name__ == "__main__":
    main()