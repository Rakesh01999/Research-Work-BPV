"""
Smart Charging Simulation with SOC Threshold Management
Automatically routes vehicles to nearest charging station when SOC < 30%
REAL wired (plug-in) charging - Bangladesh scenario
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
    Implements REAL wired charging (vehicles physically stop and charge)
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
        self.vehicle_states = {}  # {veh_id: {'routed_to_station': str, 'charging_start_time': float}}
        self.initial_soc = {}
        
        print(f"✓ Smart Charging Simulation initialized")
        print(f"  SOC Threshold: {self.SOC_THRESHOLD}%")
        print(f"  Target SOC: {self.SOC_TARGET}%")
        print(f"  Charging Stations: {len(self.CHARGING_STATIONS)}")
        print(f"  Charging Mode: WIRED (plug-in/plug-out)")
    
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
    
    def route_to_nearest_charging_station(self, veh_id, nearest_station, battery_info):
        """Command vehicle to stop at charging station for WIRED charging"""
        
        try:
            # Get station info
            station_info = self.CHARGING_STATIONS[nearest_station]
            
            # Calculate charging duration needed
            current_soc = battery_info['soc_percent']
            max_battery = battery_info['max_battery_Wh']
            
            # Energy needed to reach 80% SOC
            energy_needed = (self.SOC_TARGET - current_soc) / 100 * max_battery
            charging_power = station_info['power']  # Watts
            efficiency = 0.90
            
            # Charging duration (seconds) = (Energy needed / Power) * 3600
            charging_duration = (energy_needed / (charging_power * efficiency)) * 3600
            charging_duration = max(60, min(charging_duration, 300))  # 1-5 minutes range
            
            # CRITICAL: Command vehicle to STOP at charging station
            # This is the key for WIRED charging - vehicle physically stops
            traci.vehicle.setChargingStationStop(
                veh_id,
                nearest_station,
                duration=charging_duration  # Stay for calculated time
            )
            
            print(f"🔌 ROUTING {veh_id} to {nearest_station} for WIRED CHARGING")
            print(f"   Will stop and charge for {charging_duration:.0f} seconds")
            print(f"   Target SOC: {current_soc:.1f}% → {self.SOC_TARGET}%")
            
            return True
            
        except Exception as e:
            print(f"❌ Error routing {veh_id}: {e}")
            return False
    
    def check_charging_needed(self, veh_id, battery_info, simulation_time):
        """Check if vehicle needs charging and route to station"""
        
        soc = battery_info['soc_percent']
        
        # Check if SOC below threshold
        if soc < self.SOC_THRESHOLD:
            
            # Only route once per vehicle (avoid repeated routing)
            if veh_id in self.vehicle_states and 'routed_to_station' in self.vehicle_states[veh_id]:
                return False  # Already routed
            
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
                'action': 'COMMANDED_TO_STOP_AND_CHARGE'
            }
            self.low_soc_alerts.append(alert)
            
            # ROUTE VEHICLE TO CHARGING STATION (WIRED CHARGING)
            success = self.route_to_nearest_charging_station(veh_id, nearest_station, battery_info)
            
            if success:
                # Mark vehicle as routed
                if veh_id not in self.vehicle_states:
                    self.vehicle_states[veh_id] = {}
                self.vehicle_states[veh_id]['routed_to_station'] = nearest_station
                self.vehicle_states[veh_id]['alert_time'] = simulation_time
            
            print(f"⚠️  LOW SOC ALERT: {veh_id} ({veh_type})")
            print(f"    Current SOC: {soc:.2f}% (Threshold: {self.SOC_THRESHOLD}%)")
            print(f"    Below threshold by: {soc_deficit:.2f}%")
            print(f"    Commanded to stop at: {nearest_station} ({distance:.2f}m)")
            
            return True
        
        return False
    
    def monitor_real_charging(self, simulation_time):
        """Monitor vehicles that are ACTUALLY charging (REAL SUMO charging)"""
        
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                # Check if vehicle is currently charging
                charging_station_id = traci.vehicle.getParameter(veh_id, "device.battery.chargingStationId")
                
                if charging_station_id and charging_station_id != "NULL":
                    # Vehicle IS charging right now
                    
                    battery_info = self.get_vehicle_battery_info(veh_id)
                    if not battery_info:
                        continue
                    
                    # Track charging start
                    if veh_id not in self.vehicle_states:
                        self.vehicle_states[veh_id] = {}
                    
                    if 'charging_start_time' not in self.vehicle_states[veh_id]:
                        # Charging just started
                        self.vehicle_states[veh_id]['charging_start_time'] = simulation_time
                        self.vehicle_states[veh_id]['soc_at_start'] = battery_info['soc_percent']
                        self.vehicle_states[veh_id]['charging_station_active'] = charging_station_id
                        
                        print(f"🔌 REAL CHARGING STARTED: {veh_id} at {charging_station_id}")
                        print(f"    SOC at plug-in: {battery_info['soc_percent']:.2f}%")
                        print(f"    Vehicle physically stopped for WIRED charging")
                    
                else:
                    # Vehicle NOT charging (or just finished)
                    if veh_id in self.vehicle_states and 'charging_start_time' in self.vehicle_states[veh_id]:
                        # Charging just completed
                        
                        battery_info = self.get_vehicle_battery_info(veh_id)
                        if not battery_info:
                            continue
                        
                        # Record completed charging event
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
                        
                        print(f"✅ WIRED CHARGING COMPLETE: {veh_id}")
                        print(f"    Duration: {duration:.1f}s")
                        print(f"    SOC: {soc_start:.2f}% → {soc_end:.2f}% (gained: {soc_end - soc_start:.2f}%)")
                        print(f"    Vehicle unplugged and resuming journey")
                        
                        # Clear charging state
                        del self.vehicle_states[veh_id]['charging_start_time']
                        del self.vehicle_states[veh_id]['soc_at_start']
                        if 'charging_station_active' in self.vehicle_states[veh_id]:
                            del self.vehicle_states[veh_id]['charging_station_active']
            
            except Exception as e:
                continue
    
    def collect_vehicle_data(self, simulation_time):
        """Collect data from all vehicles"""
        
        # Monitor real charging events first
        self.monitor_real_charging(simulation_time)
        
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
                
                # Check if charging needed (will route vehicle if needed)
                self.check_charging_needed(veh_id, battery_info, simulation_time)
                
                # Check if currently charging
                is_charging = False
                try:
                    charging_station_id = traci.vehicle.getParameter(veh_id, "device.battery.chargingStationId")
                    if charging_station_id and charging_station_id != "NULL":
                        is_charging = True
                except:
                    pass
                
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
                    'currently_charging': 'YES' if is_charging else 'NO',
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
        """Run simulation with smart WIRED charging"""
        
        print("\n" + "="*70)
        print("SMART WIRED CHARGING SIMULATION - BANGLADESH SCENARIO")
        print("="*70)
        print(f"Configuration: {self.sumocfg}")
        print(f"GUI Mode: {'Enabled' if gui else 'Disabled'}")
        print(f"Max Time: {max_time} seconds")
        print(f"Charging Mode: WIRED (Plug-in/Plug-out)")
        print(f"chargeInTransit: FALSE (vehicles must stop)")
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
                    charging_now = sum(1 for v in self.vehicle_states.values() if 'charging_start_time' in v)
                    print(f"⏱️  Time: {int(simulation_time)}s | Vehicles: {active} | Charging: {charging_now} | Alerts: {len(self.low_soc_alerts)}")
            
            print(f"\n✓ Simulation completed at {simulation_time}s")
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
            print(f"\n✓ Vehicle SOC tracking: {filename}")
            print(f"  Records: {len(df)}")
        
        # 2. Low SOC Alerts (Critical!)
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            filename = os.path.join(self.output_folder, f'low_soc_alerts_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ Low SOC alerts: {filename}")
            print(f"  Alerts: {len(df)}")
            
            # Print summary
            print(f"\n📊 LOW SOC SUMMARY:")
            print(f"  Total alerts: {len(df)}")
            print(f"  Unique vehicles: {df['vehicle_id'].nunique()}")
            print(f"  Average SOC deficit: {df['soc_below_threshold'].mean():.2f}%")
            print(f"  Most used station: {df['nearest_station'].mode()[0] if len(df) > 0 else 'N/A'}")
        else:
            print("\nℹ️  No low SOC alerts (all vehicles maintained SOC > 30%)")
        
        # 3. Charging Events (REAL WIRED CHARGING)
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            filename = os.path.join(self.output_folder, f'WIRED_charging_events_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ WIRED Charging events: {filename}")
            print(f"  Events: {len(df)}")
            
            print(f"\n🔌 WIRED CHARGING SUMMARY:")
            print(f"  Total charging sessions: {len(df)}")
            print(f"  Average duration: {df['duration_sec'].mean():.1f}s")
            print(f"  Average SOC gain: {df['soc_gained_percent'].mean():.2f}%")
            print(f"  Successful charges: {(df['charging_successful'] == 'YES').sum()}")
            
            # Station usage
            print(f"\n📍 STATION USAGE:")
            station_counts = df['charging_station'].value_counts()
            for station, count in station_counts.items():
                print(f"  {station}: {count} vehicles")
        else:
            print("\nℹ️  No charging events recorded")
            print("  (Vehicles may not have reached charging stations yet)")
        
        # 4. Threshold Analysis Report
        self._generate_threshold_report(timestamp)
        
        print("="*70)
    
    def _generate_threshold_report(self, timestamp):
        """Generate detailed threshold analysis report"""
        
        filename = os.path.join(self.output_folder, f'threshold_analysis_{timestamp}.txt')
        
        with open(filename, 'w') as f:
            f.write("="*70 + "\n")
            f.write("SOC THRESHOLD ANALYSIS REPORT - WIRED CHARGING\n")
            f.write("="*70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"SOC Threshold: {self.SOC_THRESHOLD}%\n")
            f.write(f"Target SOC: {self.SOC_TARGET}%\n")
            f.write(f"Charging Mode: WIRED (Plug-in/Plug-out)\n")
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
                    
                    # Check if vehicle charged
                    if veh_id in [e['vehicle_id'] for e in self.charging_events]:
                        f.write(f"  Charging: COMPLETED\n")
                    elif veh_id in self.vehicle_states and 'routed_to_station' in self.vehicle_states[veh_id]:
                        f.write(f"  Charging: ROUTED (in progress)\n")
                    
                f.write("\n" + "="*70 + "\n")
        
        print(f"\n✓ Threshold analysis report: {filename}")


def main():
    """Main execution"""
    
    print("\n" + "="*70)
    print("SMART EV CHARGING SIMULATION - BANGLADESH WIRED CHARGING")
    print("Real plug-in/plug-out charging at physical stations")
    print("="*70 + "\n")
    
    # Configuration
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = True  # Set True to visualize
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
    print("\nGenerated files:")
    print("  - vehicle_soc_tracking_*.csv (all vehicle data)")
    print("  - low_soc_alerts_*.csv (when SOC < 30%)")
    print("  - WIRED_charging_events_*.csv (actual charging sessions)")
    print("  - threshold_analysis_*.txt (detailed report)")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()