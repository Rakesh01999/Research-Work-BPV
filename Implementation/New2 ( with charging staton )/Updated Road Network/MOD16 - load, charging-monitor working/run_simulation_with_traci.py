
"""
SUMO TraCI to Excel/CSV Exporter for Test1 Configuration
Complete working solution for your Bangladesh EV simulation
Author: Custom script for Test1.sumocfg
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Check if required packages are installed
try:
    import traci
    print("✓ TraCI imported successfully")
except ImportError:
    print("✗ ERROR: TraCI not found!")
    print("Install with: pip install traci")
    sys.exit(1)

try:
    import pandas as pd
    print("✓ Pandas imported successfully")
except ImportError:
    print("✗ ERROR: Pandas not found!")
    print("Install with: pip install pandas openpyxl")
    sys.exit(1)


class Test1SUMOExporter:
    """
    Export SUMO simulation data to Excel/CSV format
    Designed for Test1.sumocfg with Bangladesh EV network
    """
    
    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        """
        Initialize the exporter
        
        Parameters:
        -----------
        sumocfg : str
            Path to SUMO configuration file
        output_folder : str
            Folder where outputs will be saved
        """
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"✓ Created output folder: {output_folder}")
        
        # Data containers
        self.battery_data = []
        self.realtime_data = []
        self.trip_data = {}
        self.charging_events = []
        
        # Statistics
        self.stats = {
            'total_vehicles': 0,
            'vehicles_completed': 0,
            'total_distance': 0,
            'total_energy_consumed': 0,
            'total_energy_regenerated': 0
        }
        
        # Verify SUMO configuration exists
        if not os.path.exists(sumocfg):
            print(f"✗ ERROR: Configuration file not found: {sumocfg}")
            sys.exit(1)
        
        print(f"✓ Initialized exporter for: {sumocfg}")
    
    def run_simulation(self, gui=False, step_length=1.0):
        """
        Run SUMO simulation and collect data
        
        Parameters:
        -----------
        gui : bool
            Use SUMO-GUI (True) or command-line SUMO (False)
        step_length : float
            Data collection interval (seconds)
        """
        print("\n" + "="*70)
        print("STARTING SUMO SIMULATION")
        print("="*70)
        print(f"Configuration: {self.sumocfg}")
        print(f"GUI Mode: {'Enabled' if gui else 'Disabled'}")
        print(f"Output Folder: {self.output_folder}")
        print(f"Data Collection Interval: {step_length} seconds")
        print("="*70 + "\n")
        
        # Determine SUMO binary
        if gui:
            sumo_binary = "sumo-gui"
            print("Starting SUMO-GUI... (Close the window when done)")
        else:
            sumo_binary = "sumo"
            print("Starting SUMO in command-line mode...")
        
        # Build SUMO command
        sumo_cmd = [
            sumo_binary,
            "-c", self.sumocfg,
            "--start",
            "--quit-on-end",
            "--no-warnings"
        ]
        
        try:
            # Start TraCI
            traci.start(sumo_cmd)
            print("✓ TraCI connection established\n")
            
            simulation_time = 0
            data_collection_interval = step_length
            next_collection_time = 0
            
            # Simulation loop
            while traci.simulation.getMinExpectedNumber() > 0:
                # Advance simulation
                traci.simulationStep()
                simulation_time = traci.simulation.getTime()
                
                # Collect data at specified intervals
                if simulation_time >= next_collection_time:
                    self._collect_data(simulation_time)
                    next_collection_time += data_collection_interval
                
                # Progress indicator every 10 seconds
                if int(simulation_time) % 10 == 0 and simulation_time > 0:
                    active_vehicles = len(traci.vehicle.getIDList())
                    print(f"Time: {int(simulation_time)}s | Active vehicles: {active_vehicles}")
            
            # Collect final trip info
            print("\n✓ Simulation completed!")
            print(f"Total simulation time: {simulation_time} seconds")
            print(f"Data records collected: {len(self.battery_data)}")
            
            # Close TraCI
            traci.close()
            
            return True
            
        except Exception as e:
            print(f"\n✗ ERROR during simulation: {e}")
            print(f"Error type: {type(e).__name__}")
            try:
                traci.close()
            except:
                pass
            return False
    
    def _collect_data(self, simulation_time):
        """Collect data from all vehicles at current timestep"""
        
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                # Basic vehicle data
                speed = traci.vehicle.getSpeed(veh_id)
                position = traci.vehicle.getPosition(veh_id)
                lane_id = traci.vehicle.getLaneID(veh_id)
                distance = traci.vehicle.getDistance(veh_id)
                waiting_time = traci.vehicle.getWaitingTime(veh_id)
                
                # Vehicle type
                vtype = traci.vehicle.getTypeID(veh_id)
                
                # Try to get battery data
                battery_capacity = 0
                max_battery = 0
                energy_consumed = 0
                energy_regen = 0
                charging_station = "NULL"
                
                try:
                    # Get battery device parameters
                    battery_capacity = float(traci.vehicle.getParameter(veh_id, "device.battery.actualBatteryCapacity"))
                    max_battery = float(traci.vehicle.getParameter(veh_id, "device.battery.maximumBatteryCapacity"))
                    energy_consumed = float(traci.vehicle.getParameter(veh_id, "device.battery.totalEnergyConsumed"))
                    energy_regen = float(traci.vehicle.getParameter(veh_id, "device.battery.totalEnergyRegenerated"))
                    
                    # Check if charging
                    charging_station_id = traci.vehicle.getParameter(veh_id, "device.battery.chargingStationId")
                    if charging_station_id and charging_station_id != "NULL":
                        charging_station = charging_station_id
                        
                        # Record charging event
                        self.charging_events.append({
                            'timestep': simulation_time,
                            'vehicle_id': veh_id,
                            'vehicle_type': vtype,
                            'charging_station': charging_station,
                            'battery_soc_percent': (battery_capacity / max_battery * 100) if max_battery > 0 else 0
                        })
                
                except:
                    pass  # Battery device not available for this vehicle
                
                # Battery data record
                if max_battery > 0:  # Only if battery device is active
                    battery_record = {
                        'timestep_sec': simulation_time,
                        'vehicle_id': veh_id,
                        'vehicle_type': vtype,
                        'actualBatteryCapacity_Wh': battery_capacity,
                        'maximumBatteryCapacity_Wh': max_battery,
                        'battery_soc_percent': (battery_capacity / max_battery * 100) if max_battery > 0 else 0,
                        'totalEnergyConsumed_Wh': energy_consumed,
                        'totalEnergyRegenerated_Wh': energy_regen,
                        'netEnergyUsed_Wh': energy_consumed - energy_regen,
                        'chargingStationId': charging_station,
                        'speed_ms': speed,
                        'speed_kmh': speed * 3.6,
                        'x_position_m': position[0],
                        'y_position_m': position[1],
                        'lane': lane_id,
                        'distance_traveled_m': distance,
                        'waiting_time_sec': waiting_time
                    }
                    self.battery_data.append(battery_record)
                
                # Real-time data (all vehicles)
                realtime_record = {
                    'timestep_sec': simulation_time,
                    'vehicle_id': veh_id,
                    'vehicle_type': vtype,
                    'speed_ms': speed,
                    'speed_kmh': speed * 3.6,
                    'x_position_m': position[0],
                    'y_position_m': position[1],
                    'lane': lane_id,
                    'distance_traveled_m': distance,
                    'waiting_time_sec': waiting_time
                }
                self.realtime_data.append(realtime_record)
                
                # Track trip data
                if veh_id not in self.trip_data:
                    self.trip_data[veh_id] = {
                        'vehicle_id': veh_id,
                        'vehicle_type': vtype,
                        'depart_time': simulation_time,
                        'max_speed_kmh': 0,
                        'total_waiting_time': 0,
                        'final_distance': 0
                    }
                
                # Update trip data
                self.trip_data[veh_id]['max_speed_kmh'] = max(
                    self.trip_data[veh_id]['max_speed_kmh'],
                    speed * 3.6
                )
                self.trip_data[veh_id]['total_waiting_time'] += waiting_time
                self.trip_data[veh_id]['final_distance'] = distance
                
            except traci.exceptions.TraCIException as e:
                # Vehicle might have left the simulation
                continue
            except Exception as e:
                print(f"Warning: Error collecting data for {veh_id}: {e}")
                continue
    
    def export_to_csv(self):
        """Export all data to CSV files"""
        print("\n" + "="*70)
        print("EXPORTING DATA TO CSV")
        print("="*70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Battery Data CSV
        if self.battery_data:
            df_battery = pd.DataFrame(self.battery_data)
            battery_file = os.path.join(self.output_folder, f'battery_data_{timestamp}.csv')
            df_battery.to_csv(battery_file, index=False)
            print(f"✓ Battery data exported: {battery_file}")
            print(f"  Records: {len(df_battery)}")
        else:
            print("⚠ No battery data collected")
        
        # 2. Real-time Data CSV
        if self.realtime_data:
            df_realtime = pd.DataFrame(self.realtime_data)
            realtime_file = os.path.join(self.output_folder, f'realtime_data_{timestamp}.csv')
            df_realtime.to_csv(realtime_file, index=False)
            print(f"✓ Real-time data exported: {realtime_file}")
            print(f"  Records: {len(df_realtime)}")
        else:
            print("⚠ No real-time data collected")
        
        # 3. Trip Summary CSV
        if self.trip_data:
            df_trips = pd.DataFrame(list(self.trip_data.values()))
            trips_file = os.path.join(self.output_folder, f'trip_summary_{timestamp}.csv')
            df_trips.to_csv(trips_file, index=False)
            print(f"✓ Trip summary exported: {trips_file}")
            print(f"  Vehicles: {len(df_trips)}")
        else:
            print("⚠ No trip data collected")
        
        # 4. Charging Events CSV
        if self.charging_events:
            df_charging = pd.DataFrame(self.charging_events)
            charging_file = os.path.join(self.output_folder, f'charging_events_{timestamp}.csv')
            df_charging.to_csv(charging_file, index=False)
            print(f"✓ Charging events exported: {charging_file}")
            print(f"  Events: {len(df_charging)}")
        else:
            print("⚠ No charging events recorded")
        
        print("="*70)
    
    def export_to_excel(self):
        """Export all data to a single Excel file with multiple sheets"""
        print("\n" + "="*70)
        print("EXPORTING DATA TO EXCEL")
        print("="*70)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = os.path.join(self.output_folder, f'simulation_results_{timestamp}.xlsx')
        
        try:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                
                # Sheet 1: Battery Data
                if self.battery_data:
                    df_battery = pd.DataFrame(self.battery_data)
                    df_battery.to_excel(writer, sheet_name='Battery_Data', index=False)
                    print(f"✓ Battery Data sheet: {len(df_battery)} records")
                
                # Sheet 2: Battery Summary by Vehicle
                if self.battery_data:
                    df_battery = pd.DataFrame(self.battery_data)
                    battery_summary = df_battery.groupby('vehicle_id').agg({
                        'vehicle_type': 'first',
                        'totalEnergyConsumed_Wh': 'max',
                        'totalEnergyRegenerated_Wh': 'max',
                        'netEnergyUsed_Wh': 'max',
                        'battery_soc_percent': 'last',
                        'distance_traveled_m': 'max',
                        'speed_kmh': 'mean'
                    }).reset_index()
                    
                    battery_summary.columns = [
                        'Vehicle_ID', 'Vehicle_Type', 'Total_Energy_Consumed_Wh',
                        'Total_Energy_Regenerated_Wh', 'Net_Energy_Used_Wh',
                        'Final_SoC_Percent', 'Total_Distance_m', 'Avg_Speed_kmh'
                    ]
                    
                    # Add calculated columns
                    battery_summary['Total_Distance_km'] = battery_summary['Total_Distance_m'] / 1000
                    battery_summary['Energy_Efficiency_Wh_per_km'] = (
                        battery_summary['Net_Energy_Used_Wh'] / battery_summary['Total_Distance_km']
                    )
                    battery_summary['Regeneration_Efficiency_Percent'] = (
                        battery_summary['Total_Energy_Regenerated_Wh'] / 
                        battery_summary['Total_Energy_Consumed_Wh'] * 100
                    )
                    
                    battery_summary.to_excel(writer, sheet_name='Battery_Summary', index=False)
                    print(f"✓ Battery Summary sheet: {len(battery_summary)} vehicles")
                
                # Sheet 3: Real-time Data
                if self.realtime_data:
                    df_realtime = pd.DataFrame(self.realtime_data)
                    df_realtime.to_excel(writer, sheet_name='Realtime_Data', index=False)
                    print(f"✓ Real-time Data sheet: {len(df_realtime)} records")
                
                # Sheet 4: Vehicle Type Statistics
                if self.realtime_data:
                    df_realtime = pd.DataFrame(self.realtime_data)
                    type_stats = df_realtime.groupby('vehicle_type').agg({
                        'vehicle_id': 'nunique',
                        'speed_kmh': ['mean', 'max'],
                        'distance_traveled_m': 'max',
                        'waiting_time_sec': 'sum'
                    }).reset_index()
                    
                    type_stats.columns = [
                        'Vehicle_Type', 'Count', 'Avg_Speed_kmh', 'Max_Speed_kmh',
                        'Max_Distance_m', 'Total_Waiting_Time_sec'
                    ]
                    
                    type_stats.to_excel(writer, sheet_name='Vehicle_Type_Stats', index=False)
                    print(f"✓ Vehicle Type Statistics sheet: {len(type_stats)} types")
                
                # Sheet 5: Charging Events
                if self.charging_events:
                    df_charging = pd.DataFrame(self.charging_events)
                    df_charging.to_excel(writer, sheet_name='Charging_Events', index=False)
                    print(f"✓ Charging Events sheet: {len(df_charging)} events")
                    
                    # Charging summary by station
                    charging_summary = df_charging.groupby('charging_station').agg({
                        'vehicle_id': 'count',
                        'battery_soc_percent': 'mean'
                    }).reset_index()
                    charging_summary.columns = ['Charging_Station', 'Total_Visits', 'Avg_SoC_at_Charge']
                    charging_summary.to_excel(writer, sheet_name='Charging_Summary', index=False)
                    print(f"✓ Charging Summary sheet: {len(charging_summary)} stations")
                
                # Sheet 6: Overall Statistics
                stats_data = []
                
                if self.battery_data:
                    df_battery = pd.DataFrame(self.battery_data)
                    total_vehicles = df_battery['vehicle_id'].nunique()
                    total_energy = df_battery.groupby('vehicle_id')['totalEnergyConsumed_Wh'].max().sum()
                    total_regen = df_battery.groupby('vehicle_id')['totalEnergyRegenerated_Wh'].max().sum()
                    net_energy = total_energy - total_regen
                    regen_eff = (total_regen / total_energy * 100) if total_energy > 0 else 0
                    
                    stats_data.extend([
                        ['Total Vehicles', total_vehicles, 'count'],
                        ['Total Energy Consumed', round(total_energy/1000, 2), 'kWh'],
                        ['Total Energy Regenerated', round(total_regen/1000, 2), 'kWh'],
                        ['Net Energy Used', round(net_energy/1000, 2), 'kWh'],
                        ['Regeneration Efficiency', round(regen_eff, 2), '%']
                    ])
                
                if self.realtime_data:
                    df_realtime = pd.DataFrame(self.realtime_data)
                    max_time = df_realtime['timestep_sec'].max()
                    avg_speed = df_realtime['speed_kmh'].mean()
                    total_distance = df_realtime.groupby('vehicle_id')['distance_traveled_m'].max().sum()
                    
                    stats_data.extend([
                        ['Simulation Duration', round(max_time, 0), 'seconds'],
                        ['Average Speed', round(avg_speed, 2), 'km/h'],
                        ['Total Distance Traveled', round(total_distance/1000, 2), 'km']
                    ])
                
                df_stats = pd.DataFrame(stats_data, columns=['Metric', 'Value', 'Unit'])
                df_stats.to_excel(writer, sheet_name='Overall_Statistics', index=False)
                print(f"✓ Overall Statistics sheet: {len(df_stats)} metrics")
            
            print(f"\n✓ Excel file created: {excel_file}")
            print(f"  Open with: Excel, LibreOffice, or Google Sheets")
            
        except Exception as e:
            print(f"✗ Error creating Excel file: {e}")
            print("  Falling back to CSV export...")
            self.export_to_csv()


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("SUMO SIMULATION DATA EXPORTER")
    print("Test1 Configuration - Bangladesh EV Network")
    print("="*70)
    
    # Configuration
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = False  # Set to True to see visualization
    DATA_INTERVAL = 1.0  # Collect data every 1 second
    
    # Check if SUMO config exists
    if not os.path.exists(SUMOCFG):
        print(f"\n✗ ERROR: {SUMOCFG} not found!")
        print("Make sure you're running this script in the correct directory.")
        return
    
    # Create exporter
    exporter = Test1SUMOExporter(
        sumocfg=SUMOCFG,
        output_folder=OUTPUT_FOLDER
    )
    
    # Run simulation
    success = exporter.run_simulation(gui=USE_GUI, step_length=DATA_INTERVAL)
    
    if not success:
        print("\n✗ Simulation failed!")
        return
    
    # Export to both CSV and Excel
    print("\n" + "="*70)
    print("EXPORTING RESULTS")
    print("="*70)
    
    # Export to CSV (always works)
    exporter.export_to_csv()
    
    # Try to export to Excel
    try:
        exporter.export_to_excel()
    except ImportError:
        print("\n⚠ Excel export requires openpyxl: pip install openpyxl")
        print("  CSV files have been created successfully.")
    
    print("\n" + "="*70)
    print("EXPORT COMPLETE!")
    print("="*70)
    print(f"\nAll output files saved in: {OUTPUT_FOLDER}/")
    print("\nYou can now:")
    print("  1. Open CSV files in Excel")
    print("  2. Open Excel file (if created)")
    print("  3. Analyze the data")
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
    