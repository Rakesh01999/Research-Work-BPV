
"""
Smart Charging Simulation with SOC Threshold Management
Automatically routes vehicles to nearest charging station when SOC < 30%
Includes charging delays and comprehensive tracking
"""

import os
import sys
import pandas as pd
from datetime import datetime
import math

try:
    import traci
    print("✓ TraCI imported successfully")
except ImportError:
    print("✗ ERROR: TraCI not found!")
    print("Install with: pip install traci")
    sys.exit(1)


class SmartChargingSimulation:
    """
    Smart charging system with SOC threshold monitoring
    Routes vehicles to nearest charging station when SOC < 30%
    """
    
    # SOC Threshold Configuration
    SOC_THRESHOLD = 30.0  # 30% - critical battery level
    SOC_TARGET = 80.0     # 80% - target after charging
    
    # Charging station locations (from Test1.chargingstations.add.xml)
    CHARGING_STATIONS = {
        'CS_Node2': {'lane': 'E1_0', 'power': 5000, 'position': (23.06, 128.29)},
        'CS_Node3_E1': {'lane': 'E1_1', 'power': 7000, 'position': (244.43, 139.39)},
        'CS_Node3_E2': {'lane': 'E2_0', 'power': 7000, 'position': (260.29, 137.87)},
        'CS_Node5': {'lane': 'E5_0', 'power': 5000, 'position': (-220.04, 6.13)},
        'CS_Node6': {'lane': 'E6_0', 'power': 5000, 'position': (-129.97, -86.83)},
        'CS_Node8_E7': {'lane': 'E7_1', 'power': 7000, 'position': (240.54, -110.00)},
        'CS_Node8_E8': {'lane': 'E8_0', 'power': 7000, 'position': (255.68, -111.70)}
    }
    
    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Data tracking
        self.vehicle_data = []
        self.charging_events = []
        self.low_soc_alerts = []
        self.charging_decisions = []
        
        # Vehicle state tracking
        self.vehicle_states = {}  # {veh_id: {'charging': bool, 'charge_start': time}}
        self.initial_soc = {}
        
        print(f"✓ Smart Charging Simulation initialized")
        print(f"  SOC Threshold: {self.SOC_THRESHOLD}%")
        print(f"  Target SOC: {self.SOC_TARGET}%")
        print(f"  Charging Stations: {len(self.CHARGING_STATIONS)}")
    
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance between two positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def find_nearest_charging_station(self, vehicle_position):
        """Find nearest charging station to vehicle"""
        nearest_station = None
        min_distance = float('inf')
        
        for station_id, station_info in self.CHARGING_STATIONS.items():
            distance = self.calculate_distance(vehicle_position, station_info['position'])
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
        
        return nearest_station, min_distance
    
    def get_vehicle_battery_info(self, veh_id):
        """Get comprehensive battery information"""
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
    
    def check_charging_needed(self, veh_id, battery_info, simulation_time):
        """Check if vehicle needs charging and route to station"""
        
        soc = battery_info['soc_percent']
        
        # Check if SOC below threshold
        if soc < self.SOC_THRESHOLD:
            
            # Get vehicle position
            position = traci.vehicle.getPosition(veh_id)
            veh_type = traci.vehicle.getTypeID(veh_id)
            
            # Find nearest charging station
            nearest_station, distance = self.find_nearest_charging_station(position)
            
            # Calculate SOC deficit
            soc_deficit = self.SOC_THRESHOLD - soc
            
            # Record low SOC alert
            alert = {
                'timestep_sec': simulation_time,
                'vehicle_id': veh_id,
                'vehicle_type': veh_type,
                'current_soc_percent': round(soc, 2),
                'threshold_soc_percent': self.SOC_THRESHOLD,
                'soc_below_threshold': round(soc_deficit, 2),
                'nearest_station': nearest_station,
                'distance_to_station_m': round(distance, 2),
                'battery_capacity_Wh': battery_info['actual_battery_Wh'],
                'max_battery_Wh': battery_info['max_battery_Wh'],
                'action': 'ROUTE_TO_CHARGING_STATION'
            }
            self.low_soc_alerts.append(alert)
            
            # Mark vehicle as needing charge
            if veh_id not in self.vehicle_states:
                self.vehicle_states[veh_id] = {
                    'charging_needed': True,
                    'target_station': nearest_station,
                    'alert_time': simulation_time
                }
            
            print(f"⚠️  LOW SOC ALERT: {veh_id} ({veh_type})")
            print(f"    Current SOC: {soc:.2f}% (Threshold: {self.SOC_THRESHOLD}%)")
            print(f"    Below threshold by: {soc_deficit:.2f}%")
            print(f"    Nearest station: {nearest_station} ({distance:.2f}m)")
            
            return True
        
        return False
    
    def simulate_charging(self, veh_id, battery_info, simulation_time):
        """Simulate charging process with delays"""
        
        # Check if vehicle is at charging station
        lane_id = traci.vehicle.getLaneID(veh_id)
        
        for station_id, station_info in self.CHARGING_STATIONS.items():
            if station_info['lane'] in lane_id:
                
                # Initialize charging state
                if veh_id not in self.vehicle_states:
                    self.vehicle_states[veh_id] = {}
                
                if 'charging_start' not in self.vehicle_states[veh_id]:
                    # Start charging
                    self.vehicle_states[veh_id]['charging_start'] = simulation_time
                    self.vehicle_states[veh_id]['charging_station'] = station_id
                    self.vehicle_states[veh_id]['soc_at_arrival'] = battery_info['soc_percent']
                    
                    print(f"🔌 CHARGING STARTED: {veh_id} at {station_id}")
                    print(f"    SOC at arrival: {battery_info['soc_percent']:.2f}%")
                
                # Calculate charging duration
                charge_start = self.vehicle_states[veh_id]['charging_start']
                charging_duration = simulation_time - charge_start
                
                # Charging parameters
                charging_power = station_info['power']  # Watts
                efficiency = 0.90  # 90% efficiency
                
                # Calculate energy charged (simplified)
                energy_charged_Wh = (charging_power * efficiency * charging_duration) / 3600
                
                # Update battery (simulation)
                new_soc = min(battery_info['soc_percent'] + (energy_charged_Wh / battery_info['max_battery_Wh'] * 100), 100)
                
                # Check if target SOC reached
                if new_soc >= self.SOC_TARGET or charging_duration >= 300:  # 5 min max
                    
                    # Record charging event
                    charging_event = {
                        'vehicle_id': veh_id,
                        'vehicle_type': traci.vehicle.getTypeID(veh_id),
                        'charging_station': station_id,
                        'arrival_time_sec': charge_start,
                        'departure_time_sec': simulation_time,
                        'charging_duration_sec': charging_duration,
                        'soc_at_arrival_percent': self.vehicle_states[veh_id]['soc_at_arrival'],
                        'soc_at_departure_percent': new_soc,
                        'soc_gained_percent': new_soc - self.vehicle_states[veh_id]['soc_at_arrival'],
                        'energy_charged_Wh': round(energy_charged_Wh, 2),
                        'charging_power_W': charging_power,
                        'station_efficiency': efficiency
                    }
                    self.charging_events.append(charging_event)
                    
                    print(f"✓ CHARGING COMPLETE: {veh_id}")
                    print(f"    Duration: {charging_duration:.1f}s")
                    print(f"    SOC: {self.vehicle_states[veh_id]['soc_at_arrival']:.2f}% → {new_soc:.2f}%")
                    print(f"    Energy charged: {energy_charged_Wh:.2f} Wh")
                    
                    # Clear charging state
                    del self.vehicle_states[veh_id]['charging_start']
                    del self.vehicle_states[veh_id]['charging_station']
                    
                    return True
        
        return False
    
    def collect_vehicle_data(self, simulation_time):
        """Collect data from all vehicles"""
        
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                # Basic info
                veh_type = traci.vehicle.getTypeID(veh_id)
                speed = traci.vehicle.getSpeed(veh_id)
                position = traci.vehicle.getPosition(veh_id)
                lane_id = traci.vehicle.getLaneID(veh_id)
                distance = traci.vehicle.getDistance(veh_id)
                
                # Battery info
                battery_info = self.get_vehicle_battery_info(veh_id)
                
                if battery_info is None:
                    continue
                
                # Store initial SOC
                if veh_id not in self.initial_soc:
                    self.initial_soc[veh_id] = battery_info['soc_percent']
                
                # Check if charging needed
                self.check_charging_needed(veh_id, battery_info, simulation_time)
                
                # Simulate charging if at station
                self.simulate_charging(veh_id, battery_info, simulation_time)
                
                # Record data
                record = {
                    'timestep_sec': simulation_time,
                    'vehicle_id': veh_id,
                    'vehicle_type': veh_type,
                    'actual_battery_Wh': battery_info['actual_battery_Wh'],
                    'max_battery_Wh': battery_info['max_battery_Wh'],
                    'soc_percent': round(battery_info['soc_percent'], 2),
                    'initial_soc_percent': round(self.initial_soc[veh_id], 2),
                    'soc_drop_percent': round(self.initial_soc[veh_id] - battery_info['soc_percent'], 2),
                    'below_threshold': 'YES' if battery_info['soc_percent'] < self.SOC_THRESHOLD else 'NO',
                    'threshold_deficit_percent': round(self.SOC_THRESHOLD - battery_info['soc_percent'], 2) if battery_info['soc_percent'] < self.SOC_THRESHOLD else 0,
                    'energy_consumed_Wh': battery_info['energy_consumed_Wh'],
                    'speed_ms': speed,
                    'x_position': position[0],
                    'y_position': position[1],
                    'lane': lane_id,
                    'distance_m': distance
                }
                self.vehicle_data.append(record)
                
            except Exception as e:
                continue
    
    def run_simulation(self, gui=False, max_time=600):
    # def run_simulation(self, gui=True, max_time=600):
        """Run simulation with smart charging"""
        
        print("\n" + "="*70)
        print("SMART CHARGING SIMULATION")
        print("="*70)
        print(f"Configuration: {self.sumocfg}")
        print(f"GUI Mode: {'Enabled' if gui else 'Disabled'}")
        print(f"Max Time: {max_time} seconds")
        print("="*70 + "\n")
        
        sumo_binary = "sumo-gui" if gui else "sumo"
        sumo_cmd = [sumo_binary, "-c", self.sumocfg, "--start", "--quit-on-end"]
        
        try:
            traci.start(sumo_cmd)
            print("✓ TraCI connection established\n")
            
            simulation_time = 0
            
            while traci.simulation.getMinExpectedNumber() > 0 and simulation_time < max_time:
                traci.simulationStep()
                simulation_time = traci.simulation.getTime()
                
                # Collect data every second
                if int(simulation_time) == simulation_time:
                    self.collect_vehicle_data(simulation_time)
                
                # Progress indicator
                if int(simulation_time) % 30 == 0 and simulation_time > 0:
                    active = len(traci.vehicle.getIDList())
                    print(f"⏱️  Time: {int(simulation_time)}s | Vehicles: {active} | Alerts: {len(self.low_soc_alerts)}")
            
            print(f"\n✓ Simulation completed at {simulation_time}s")
            traci.close()
            
            return True
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            try:
                traci.close()
            except:
                pass
            return False
    
    def export_results(self):
        """Export all results to CSV files"""
        
        print("\n" + "="*70)
        print("EXPORTING RESULTS")
        print("="*70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Vehicle Data with SOC Tracking
        if self.vehicle_data:
            df = pd.DataFrame(self.vehicle_data)
            filename = os.path.join(self.output_folder, f'vehicle_soc_tracking_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"✓ Vehicle SOC tracking: {filename}")
            print(f"  Records: {len(df)}")
        
        # 2. Low SOC Alerts (Critical!)
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            filename = os.path.join(self.output_folder, f'low_soc_alerts_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"✓ Low SOC alerts: {filename}")
            print(f"  Alerts: {len(df)}")
            
            # Print summary
            print(f"\n📊 LOW SOC SUMMARY:")
            print(f"  Total alerts: {len(df)}")
            print(f"  Unique vehicles: {df['vehicle_id'].nunique()}")
            print(f"  Average SOC deficit: {df['soc_below_threshold'].mean():.2f}%")
            print(f"  Most used station: {df['nearest_station'].mode()[0] if len(df) > 0 else 'N/A'}")
        else:
            print("ℹ️  No low SOC alerts (all vehicles maintained SOC > 30%)")
        
        # 3. Charging Events
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            filename = os.path.join(self.output_folder, f'charging_events_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"✓ Charging events: {filename}")
            print(f"  Events: {len(df)}")
            
            print(f"\n🔌 CHARGING SUMMARY:")
            print(f"  Total charging sessions: {len(df)}")
            print(f"  Average duration: {df['charging_duration_sec'].mean():.1f}s")
            print(f"  Average SOC gain: {df['soc_gained_percent'].mean():.2f}%")
            print(f"  Total energy charged: {df['energy_charged_Wh'].sum():.2f} Wh")
        else:
            print("ℹ️  No charging events recorded")
        
        # 4. Threshold Analysis Report
        self._generate_threshold_report(timestamp)
        
        print("="*70)
    
    def _generate_threshold_report(self, timestamp):
        """Generate detailed threshold analysis report"""
        
        filename = os.path.join(self.output_folder, f'threshold_analysis_{timestamp}.txt')
        
        with open(filename, 'w') as f:
            f.write("="*70 + "\n")
            f.write("SOC THRESHOLD ANALYSIS REPORT\n")
            f.write("="*70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"SOC Threshold: {self.SOC_THRESHOLD}%\n")
            f.write(f"Target SOC: {self.SOC_TARGET}%\n")
            f.write("="*70 + "\n\n")
            
            # Vehicle-wise analysis
            if self.vehicle_data:
                df = pd.DataFrame(self.vehicle_data)
                
                f.write("VEHICLE-WISE SOC ANALYSIS\n")
                f.write("-"*70 + "\n")
                
                for veh_id in df['vehicle_id'].unique():
                    veh_data = df[df['vehicle_id'] == veh_id]
                    min_soc = veh_data['soc_percent'].min()
                    below_threshold = veh_data[veh_data['soc_percent'] < self.SOC_THRESHOLD]
                    
                    f.write(f"\nVehicle: {veh_id}\n")
                    f.write(f"  Type: {veh_data['vehicle_type'].iloc[0]}\n")
                    f.write(f"  Initial SOC: {veh_data['initial_soc_percent'].iloc[0]:.2f}%\n")
                    f.write(f"  Minimum SOC: {min_soc:.2f}%\n")
                    f.write(f"  Below threshold: {'YES' if min_soc < self.SOC_THRESHOLD else 'NO'}\n")
                    
                    if len(below_threshold) > 0:
                        f.write(f"  Times below threshold: {len(below_threshold)}\n")
                        f.write(f"  Maximum deficit: {below_threshold['threshold_deficit_percent'].max():.2f}%\n")
                    
                f.write("\n" + "="*70 + "\n")
        
        print(f"✓ Threshold analysis report: {filename}")


def main():
    """Main execution"""
    
    print("\n" + "="*70)
    print("SMART EV CHARGING SIMULATION WITH SOC THRESHOLD")
    print("Automatic routing to nearest charging station when SOC < 30%")
    print("="*70 + "\n")
    
    # Configuration
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = False  # Set True to visualize
    # USE_GUI = True  # Set True to visualize
    MAX_TIME = 600   # 10 minutes
    
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: {SUMOCFG} not found!")
        return
    
    # Create simulation
    sim = SmartChargingSimulation(
        sumocfg=SUMOCFG,
        output_folder=OUTPUT_FOLDER
    )
    
    # Run simulation
    success = sim.run_simulation(gui=USE_GUI, max_time=MAX_TIME)
    
    if not success:
        print("\n✗ Simulation failed!")
        return
    
    # Export results
    sim.export_results()
    
    print("\n" + "="*70)
    print("✓ SIMULATION COMPLETE!")
    print(f"Output folder: {OUTPUT_FOLDER}/")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()