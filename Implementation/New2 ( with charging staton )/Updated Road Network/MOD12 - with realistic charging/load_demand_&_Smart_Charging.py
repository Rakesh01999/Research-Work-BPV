"""
Smart Charging Simulation WITH Load Demand Analysis
Routes vehicles to charging stations AND calculates load demand
"""

import os
import sys
import pandas as pd
from datetime import datetime
import math
import numpy as np
import matplotlib.pyplot as plt

try:
    import traci
    print("✓ TraCI imported successfully")
except ImportError:
    print("✗ ERROR: TraCI not found!")
    sys.exit(1)


class SmartChargingWithLoadDemand:
    """
    Combined: Smart charging + Load demand calculation
    """
    
    # SOC Threshold Configuration
    SOC_THRESHOLD = 30.0  # 30% - critical battery level
    SOC_TARGET = 80.0     # 80% - target after charging
    
    # Charging station locations and specs
    CHARGING_STATIONS = {
        'CS_Node2': {'lane': 'E1_0', 'power': 5000, 'power_kW': 5.0, 'position': (23.06, 128.29), 'efficiency': 0.90},
        'CS_Node3_E1': {'lane': 'E1_1', 'power': 7000, 'power_kW': 7.0, 'position': (244.43, 139.39), 'efficiency': 0.92},
        'CS_Node3_E2': {'lane': 'E2_0', 'power': 7000, 'power_kW': 7.0, 'position': (260.29, 137.87), 'efficiency': 0.92},
        'CS_Node5': {'lane': 'E5_0', 'power': 5000, 'power_kW': 5.0, 'position': (-220.04, 6.13), 'efficiency': 0.88},
        'CS_Node6': {'lane': 'E6_0', 'power': 5000, 'power_kW': 5.0, 'position': (-129.97, -86.83), 'efficiency': 0.88},
        'CS_Node8_E7': {'lane': 'E7_1', 'power': 7000, 'power_kW': 7.0, 'position': (240.54, -110.00), 'efficiency': 0.92},
        'CS_Node8_E8': {'lane': 'E8_0', 'power': 7000, 'power_kW': 7.0, 'position': (255.68, -111.70), 'efficiency': 0.92}
    }
    
    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Smart charging data
        self.vehicle_data = []
        self.charging_events = []
        self.low_soc_alerts = []
        self.vehicle_states = {}
        self.initial_soc = {}
        
        # Load demand data
        self.load_demand_data = []
        self.station_usage = {station: [] for station in self.CHARGING_STATIONS}
        
        print(f"✓ Smart Charging + Load Demand System initialized")
        print(f"  SOC Threshold: {self.SOC_THRESHOLD}%")
        print(f"  Target SOC: {self.SOC_TARGET}%")
        print(f"  Charging Stations: {len(self.CHARGING_STATIONS)}")
    
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def find_nearest_charging_station(self, vehicle_position):
        """Find nearest station"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station_info in self.CHARGING_STATIONS.items():
            distance = self.calculate_distance(vehicle_position, station_info['position'])
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
        
        return nearest_station, min_distance
    
    def get_vehicle_battery_info(self, veh_id):
        """Get battery information"""
        try:
            actual_battery = float(traci.vehicle.getParameter(veh_id, "device.battery.actualBatteryCapacity"))
            max_battery = float(traci.vehicle.getParameter(veh_id, "device.battery.maximumBatteryCapacity"))
            energy_consumed = float(traci.vehicle.getParameter(veh_id, "device.battery.totalEnergyConsumed"))
            
            soc_percent = (actual_battery / max_battery * 100) if max_battery > 0 else 0
            
            return {
                'actual_battery_Wh': actual_battery,
                'max_battery_Wh': max_battery,
                'soc_percent': soc_percent,
                'energy_consumed_Wh': energy_consumed
            }
        except:
            return None
    
    def route_to_nearest_charging_station(self, veh_id, nearest_station, battery_info):
        """Command vehicle to stop at charging station"""
        try:
            station_info = self.CHARGING_STATIONS[nearest_station]
            current_soc = battery_info['soc_percent']
            max_battery = battery_info['max_battery_Wh']
            energy_needed = (self.SOC_TARGET - current_soc) / 100 * max_battery
            charging_power = station_info['power']
            efficiency = 0.90
            charging_duration = (energy_needed / (charging_power * efficiency)) * 3600
            charging_duration = max(60, min(charging_duration, 300))
            
            traci.vehicle.setChargingStationStop(
                veh_id,
                nearest_station,
                duration=charging_duration
            )
            
            print(f"🔌 ROUTING {veh_id} to {nearest_station}")
            print(f"   Charging for {charging_duration:.0f}s → {self.SOC_TARGET}%")
            
            return True
        except Exception as e:
            print(f"❌ Error routing {veh_id}: {e}")
            return False
    
    def check_charging_needed(self, veh_id, battery_info, simulation_time):
        """Check if vehicle needs charging"""
        soc = battery_info['soc_percent']
        
        if soc < self.SOC_THRESHOLD:
            if veh_id in self.vehicle_states and 'routed_to_station' in self.vehicle_states[veh_id]:
                return False
            
            position = traci.vehicle.getPosition(veh_id)
            veh_type = traci.vehicle.getTypeID(veh_id)
            nearest_station, distance = self.find_nearest_charging_station(position)
            soc_deficit = self.SOC_THRESHOLD - soc
            
            alert = {
                'timestep_sec': simulation_time,
                'vehicle_id': veh_id,
                'vehicle_type': veh_type,
                'current_soc_percent': round(soc, 2),
                'threshold_soc_percent': self.SOC_THRESHOLD,
                'soc_below_threshold': round(soc_deficit, 2),
                'nearest_station': nearest_station,
                'distance_to_station_m': round(distance, 2),
                'action': 'COMMANDED_TO_STOP_AND_CHARGE'
            }
            self.low_soc_alerts.append(alert)
            
            success = self.route_to_nearest_charging_station(veh_id, nearest_station, battery_info)
            
            if success:
                if veh_id not in self.vehicle_states:
                    self.vehicle_states[veh_id] = {}
                self.vehicle_states[veh_id]['routed_to_station'] = nearest_station
                self.vehicle_states[veh_id]['alert_time'] = simulation_time
            
            print(f"⚠️  LOW SOC: {veh_id} → {nearest_station}")
            return True
        
        return False
    
    def monitor_real_charging(self, simulation_time):
        """Monitor actual charging"""
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                charging_station_id = traci.vehicle.getParameter(veh_id, "device.battery.chargingStationId")
                
                if charging_station_id and charging_station_id != "NULL":
                    battery_info = self.get_vehicle_battery_info(veh_id)
                    if not battery_info:
                        continue
                    
                    if veh_id not in self.vehicle_states:
                        self.vehicle_states[veh_id] = {}
                    
                    if 'charging_start_time' not in self.vehicle_states[veh_id]:
                        self.vehicle_states[veh_id]['charging_start_time'] = simulation_time
                        self.vehicle_states[veh_id]['soc_at_start'] = battery_info['soc_percent']
                        self.vehicle_states[veh_id]['charging_station_active'] = charging_station_id
                        
                        print(f"🔌 CHARGING STARTED: {veh_id} at {charging_station_id} ({battery_info['soc_percent']:.1f}%)")
                else:
                    if veh_id in self.vehicle_states and 'charging_start_time' in self.vehicle_states[veh_id]:
                        battery_info = self.get_vehicle_battery_info(veh_id)
                        if not battery_info:
                            continue
                        
                        charge_start = self.vehicle_states[veh_id]['charging_start_time']
                        soc_start = self.vehicle_states[veh_id]['soc_at_start']
                        soc_end = battery_info['soc_percent']
                        duration = simulation_time - charge_start
                        station_used = self.vehicle_states[veh_id].get('charging_station_active', 'UNKNOWN')
                        
                        charging_event = {
                            'vehicle_id': veh_id,
                            'vehicle_type': traci.vehicle.getTypeID(veh_id),
                            'charging_station': station_used,
                            'start_time_sec': charge_start,
                            'end_time_sec': simulation_time,
                            'duration_sec': round(duration, 1),
                            'soc_at_start_percent': round(soc_start, 2),
                            'soc_at_end_percent': round(soc_end, 2),
                            'soc_gained_percent': round(soc_end - soc_start, 2),
                            'charging_type': 'WIRED_PLUG_IN',
                            'charging_successful': 'YES' if soc_end > soc_start else 'NO'
                        }
                        self.charging_events.append(charging_event)
                        
                        print(f"✅ CHARGING COMPLETE: {veh_id} | {soc_start:.1f}% → {soc_end:.1f}%")
                        
                        del self.vehicle_states[veh_id]['charging_start_time']
                        del self.vehicle_states[veh_id]['soc_at_start']
                        if 'charging_station_active' in self.vehicle_states[veh_id]:
                            del self.vehicle_states[veh_id]['charging_station_active']
            except:
                continue
    
    def calculate_instantaneous_load(self, simulation_time):
        """Calculate load demand at current timestep"""
        vehicle_ids = traci.vehicle.getIDList()
        
        station_loads = {station: {'vehicles': 0, 'power_kW': 0} 
                        for station in self.CHARGING_STATIONS}
        
        total_power_kW = 0
        
        for veh_id in vehicle_ids:
            try:
                charging_station_id = traci.vehicle.getParameter(veh_id, "device.battery.chargingStationId")
                
                if charging_station_id and charging_station_id != "NULL":
                    if charging_station_id in self.CHARGING_STATIONS:
                        station_power = self.CHARGING_STATIONS[charging_station_id]['power_kW']
                        
                        station_loads[charging_station_id]['vehicles'] += 1
                        station_loads[charging_station_id]['power_kW'] += station_power
                        total_power_kW += station_power
            except:
                continue
        
        load_record = {
            'timestep_sec': simulation_time,
            'total_vehicles_charging': sum(s['vehicles'] for s in station_loads.values()),
            'total_power_demand_kW': round(total_power_kW, 3),
            'total_power_demand_MW': round(total_power_kW / 1000, 6)
        }
        
        for station, data in station_loads.items():
            load_record[f'{station}_vehicles'] = data['vehicles']
            load_record[f'{station}_power_kW'] = round(data['power_kW'], 3)
        
        self.load_demand_data.append(load_record)
    
    def collect_vehicle_data(self, simulation_time):
        """Collect all data"""
        self.monitor_real_charging(simulation_time)
        self.calculate_instantaneous_load(simulation_time)
        
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                veh_type = traci.vehicle.getTypeID(veh_id)
                battery_info = self.get_vehicle_battery_info(veh_id)
                
                if battery_info is None:
                    continue
                
                if veh_id not in self.initial_soc:
                    self.initial_soc[veh_id] = battery_info['soc_percent']
                
                self.check_charging_needed(veh_id, battery_info, simulation_time)
            except:
                continue
    
    def run_simulation(self, gui=True, max_time=600):
        """Run simulation"""
        print("\n" + "="*70)
        print("SMART CHARGING WITH LOAD DEMAND ANALYSIS")
        print("="*70)
        print(f"Max Time: {max_time}s")
        print("="*70 + "\n")
        
        sumo_binary = "sumo-gui" if gui else "sumo"
        sumo_cmd = [sumo_binary, "-c", self.sumocfg, "--start", "--quit-on-end"]
        
        try:
            traci.start(sumo_cmd)
            print("✓ TraCI connected\n")
            
            simulation_time = 0
            
            while traci.simulation.getMinExpectedNumber() > 0 and simulation_time < max_time:
                traci.simulationStep()
                simulation_time = traci.simulation.getTime()
                
                if int(simulation_time) == simulation_time:
                    self.collect_vehicle_data(simulation_time)
                
                if int(simulation_time) % 30 == 0 and simulation_time > 0:
                    active = len(traci.vehicle.getIDList())
                    charging = sum(1 for v in self.vehicle_states.values() if 'charging_start_time' in v)
                    if self.load_demand_data:
                        load = self.load_demand_data[-1]['total_power_demand_kW']
                        print(f"⏱️  {int(simulation_time)}s | Vehicles: {active} | Charging: {charging} | Load: {load:.1f} kW")
            
            print(f"\n✓ Completed at {simulation_time}s")
            traci.close()
            return True
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            try:
                traci.close()
            except:
                pass
            return False
    
    def export_results(self):
        """Export all results"""
        print("\n" + "="*70)
        print("EXPORTING RESULTS")
        print("="*70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Charging events
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            filename = os.path.join(self.output_folder, f'charging_events_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ Charging events: {filename} ({len(df)} events)")
        
        # 2. Low SOC alerts
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            filename = os.path.join(self.output_folder, f'low_soc_alerts_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"✓ Low SOC alerts: {filename} ({len(df)} alerts)")
        
        # 3. Load demand time series
        if self.load_demand_data:
            df = pd.DataFrame(self.load_demand_data)
            filename = os.path.join(self.output_folder, f'load_demand_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"✓ Load demand: {filename} ({len(df)} records)")
            
            # Calculate statistics
            peak_load = df['total_power_demand_kW'].max()
            avg_load = df['total_power_demand_kW'].mean()
            total_energy = df['total_power_demand_kW'].sum() / 3600
            max_vehicles = df['total_vehicles_charging'].max()
            load_factor = (avg_load / peak_load * 100) if peak_load > 0 else 0
            
            print(f"\n📊 LOAD DEMAND SUMMARY:")
            print(f"  Peak Load: {peak_load:.2f} kW")
            print(f"  Average Load: {avg_load:.2f} kW")
            print(f"  Total Energy: {total_energy:.3f} kWh")
            print(f"  Load Factor: {load_factor:.1f}%")
            print(f"  Max Charging: {int(max_vehicles)} vehicles")
        
        print("="*70)


def main():
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = True
    MAX_TIME = 600
    
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: {SUMOCFG} not found!")
        return
    
    sim = SmartChargingWithLoadDemand(
        sumocfg=SUMOCFG,
        output_folder=OUTPUT_FOLDER
    )
    
    success = sim.run_simulation(gui=USE_GUI, max_time=MAX_TIME)
    
    if not success:
        print("\n✗ Simulation failed!")
        return
    
    sim.export_results()
    
    print("\n✓ COMPLETE!")


if __name__ == "__main__":
    main()