
"""
Simple SOC Threshold Tracker
Just tracks when vehicles drop below 30% SOC
No rerouting - just monitoring and reporting
"""

import os
import sys
import pandas as pd
from datetime import datetime
import math

try:
    import traci
    print("✓ TraCI imported")
except ImportError:
    print("✗ ERROR: TraCI not found!")
    sys.exit(1)


class SimpleSOCTracker:
    """Simple threshold tracking without rerouting"""
    
    SOC_THRESHOLD = 30.0  # 30% threshold
    
    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Data storage
        self.all_vehicle_data = []
        self.threshold_violations = []
        self.violation_summary = {}  # Track first violation per vehicle
        
        print(f"✓ Simple SOC Tracker initialized")
        print(f"  Threshold: {self.SOC_THRESHOLD}%")
    
    def get_battery_info(self, veh_id):
        """Get battery information safely"""
        try:
            actual = float(traci.vehicle.getParameter(veh_id, "device.battery.actualBatteryCapacity"))
            maximum = float(traci.vehicle.getParameter(veh_id, "device.battery.maximumBatteryCapacity"))
            consumed = float(traci.vehicle.getParameter(veh_id, "device.battery.totalEnergyConsumed"))
            regen = float(traci.vehicle.getParameter(veh_id, "device.battery.totalEnergyRegenerated"))
            
            soc = (actual / maximum * 100) if maximum > 0 else 0
            
            return {
                'actual_Wh': actual,
                'max_Wh': maximum,
                'soc_percent': soc,
                'consumed_Wh': consumed,
                'regen_Wh': regen
            }
        except:
            return None
    
    def collect_data(self, timestep):
        """Collect data from all vehicles"""
        
        vehicle_ids = traci.vehicle.getIDList()
        
        for veh_id in vehicle_ids:
            try:
                # Get battery info
                battery = self.get_battery_info(veh_id)
                if not battery:
                    continue
                
                # Get vehicle info
                veh_type = traci.vehicle.getTypeID(veh_id)
                speed = traci.vehicle.getSpeed(veh_id)
                position = traci.vehicle.getPosition(veh_id)
                lane = traci.vehicle.getLaneID(veh_id)
                distance = traci.vehicle.getDistance(veh_id)
                
                soc = battery['soc_percent']
                below_threshold = soc < self.SOC_THRESHOLD
                deficit = max(0, self.SOC_THRESHOLD - soc)
                
                # Record all data
                record = {
                    'timestep_sec': timestep,
                    'vehicle_id': veh_id,
                    'vehicle_type': veh_type,
                    'soc_percent': round(soc, 3),
                    'threshold_percent': self.SOC_THRESHOLD,
                    'below_threshold': 'YES' if below_threshold else 'NO',
                    'deficit_percent': round(deficit, 3),
                    'actual_battery_Wh': round(battery['actual_Wh'], 2),
                    'max_battery_Wh': round(battery['max_Wh'], 2),
                    'energy_consumed_Wh': round(battery['consumed_Wh'], 2),
                    'energy_regen_Wh': round(battery['regen_Wh'], 2),
                    'net_energy_Wh': round(battery['consumed_Wh'] - battery['regen_Wh'], 2),
                    'speed_ms': round(speed, 2),
                    'distance_m': round(distance, 2),
                    'x_position': round(position[0], 2),
                    'y_position': round(position[1], 2),
                    'lane': lane
                }
                
                self.all_vehicle_data.append(record)
                
                # Track threshold violations
                if below_threshold:
                    
                    violation = {
                        'timestep_sec': timestep,
                        'vehicle_id': veh_id,
                        'vehicle_type': veh_type,
                        'current_soc_percent': round(soc, 3),
                        'threshold_percent': self.SOC_THRESHOLD,
                        'deficit_percent': round(deficit, 3),
                        'actual_battery_Wh': round(battery['actual_Wh'], 2),
                        'max_battery_Wh': round(battery['max_Wh'], 2),
                        'energy_consumed_Wh': round(battery['consumed_Wh'], 2),
                        'position_x': round(position[0], 2),
                        'position_y': round(position[1], 2),
                        'speed_ms': round(speed, 2)
                    }
                    
                    self.threshold_violations.append(violation)
                    
                    # Track first violation per vehicle
                    if veh_id not in self.violation_summary:
                        self.violation_summary[veh_id] = {
                            'first_violation_time': timestep,
                            'first_violation_soc': soc,
                            'vehicle_type': veh_type,
                            'min_soc_reached': soc,
                            'max_deficit': deficit,
                            'total_violations': 1
                        }
                        
                        # Print alert
                        print(f"\n⚠️  THRESHOLD VIOLATION: {veh_id}")
                        print(f"    Time: {timestep}s")
                        print(f"    SOC: {soc:.2f}% (Threshold: {self.SOC_THRESHOLD}%)")
                        print(f"    DEFICIT: {deficit:.2f}%")
                        print(f"    Battery: {battery['actual_Wh']:.0f} / {battery['max_Wh']:.0f} Wh")
                    else:
                        # Update summary
                        self.violation_summary[veh_id]['min_soc_reached'] = min(
                            self.violation_summary[veh_id]['min_soc_reached'],
                            soc
                        )
                        self.violation_summary[veh_id]['max_deficit'] = max(
                            self.violation_summary[veh_id]['max_deficit'],
                            deficit
                        )
                        self.violation_summary[veh_id]['total_violations'] += 1
                
            except Exception as e:
                continue
    
    def run_simulation(self, gui=False, max_time=600):
        """Run simulation"""
        
        print("\n" + "="*70)
        print("SIMPLE SOC THRESHOLD TRACKER")
        print("="*70)
        print(f"Configuration: {self.sumocfg}")
        print(f"GUI Mode: {'Enabled' if gui else 'Disabled'}")
        print(f"Max Time: {max_time}s")
        print(f"Threshold: {self.SOC_THRESHOLD}%")
        print("="*70 + "\n")
        
        sumo_binary = "sumo-gui" if gui else "sumo"
        sumo_cmd = [sumo_binary, "-c", self.sumocfg, "--start", "--quit-on-end", "--no-warnings"]
        
        try:
            traci.start(sumo_cmd)
            print("✓ TraCI connected\n")
            
            step = 0
            
            while traci.simulation.getMinExpectedNumber() > 0 and step < max_time:
                traci.simulationStep()
                step = traci.simulation.getTime()
                
                # Collect data every second
                if int(step) == step:
                    self.collect_data(step)
                
                # Progress update
                if int(step) % 30 == 0 and step > 0:
                    active = len(traci.vehicle.getIDList())
                    violations = len(self.violation_summary)
                    print(f"⏱️  Time: {int(step)}s | Active: {active} | Vehicles below 30%: {violations}")
            
            print(f"\n✓ Simulation completed at {step}s")
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
        
        # 1. All vehicle data
        if self.all_vehicle_data:
            df = pd.DataFrame(self.all_vehicle_data)
            filename = os.path.join(self.output_folder, f'all_vehicle_data_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ All vehicle data: {filename}")
            print(f"  Total records: {len(df):,}")
            print(f"  Unique vehicles: {df['vehicle_id'].nunique()}")
            print(f"  Time range: {df['timestep_sec'].min():.0f}s - {df['timestep_sec'].max():.0f}s")
        
        # 2. Threshold violations (ALL occurrences)
        if self.threshold_violations:
            df = pd.DataFrame(self.threshold_violations)
            filename = os.path.join(self.output_folder, f'THRESHOLD_VIOLATIONS_ALL_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ All threshold violations: {filename}")
            print(f"  Total violation records: {len(df):,}")
            print(f"  Unique vehicles violated: {df['vehicle_id'].nunique()}")
            print(f"  Average deficit: {df['deficit_percent'].mean():.3f}%")
            print(f"  Maximum deficit: {df['deficit_percent'].max():.3f}%")
            print(f"  Minimum SOC observed: {df['current_soc_percent'].min():.3f}%")
        else:
            print(f"\n✓ No threshold violations detected")
            print(f"  All vehicles maintained SOC > {self.SOC_THRESHOLD}%")
        
        # 3. Violation summary (per vehicle)
        if self.violation_summary:
            summary_data = []
            for veh_id, data in self.violation_summary.items():
                summary_data.append({
                    'vehicle_id': veh_id,
                    'vehicle_type': data['vehicle_type'],
                    'first_violation_time_sec': data['first_violation_time'],
                    'first_violation_soc_percent': round(data['first_violation_soc'], 3),
                    'minimum_soc_reached_percent': round(data['min_soc_reached'], 3),
                    'maximum_deficit_percent': round(data['max_deficit'], 3),
                    'total_violation_count': data['total_violations']
                })
            
            df = pd.DataFrame(summary_data)
            filename = os.path.join(self.output_folder, f'VIOLATION_SUMMARY_{timestamp}.csv')
            df.to_csv(filename, index=False)
            print(f"\n✓ Violation summary: {filename}")
            print(f"  Vehicles with violations: {len(df)}")
            
            # Statistics by vehicle type
            print(f"\n  📊 Violations by vehicle type:")
            for vtype in df['vehicle_type'].unique():
                vtype_data = df[df['vehicle_type'] == vtype]
                print(f"    {vtype}:")
                print(f"      Vehicles: {len(vtype_data)}")
                print(f"      Avg min SOC: {vtype_data['minimum_soc_reached_percent'].mean():.2f}%")
                print(f"      Avg max deficit: {vtype_data['maximum_deficit_percent'].mean():.2f}%")
        
        # 4. Generate text report
        report_file = os.path.join(self.output_folder, f'THRESHOLD_REPORT_{timestamp}.txt')
        with open(report_file, 'w') as f:
            f.write("="*70 + "\n")
            f.write("SOC THRESHOLD VIOLATION REPORT\n")
            f.write("="*70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Threshold: {self.SOC_THRESHOLD}%\n")
            f.write(f"Simulation duration: {max(df['timestep_sec']) if self.all_vehicle_data else 0}s\n")
            f.write("="*70 + "\n\n")
            
            if self.violation_summary:
                f.write(f"SUMMARY\n")
                f.write("-"*70 + "\n")
                f.write(f"Total vehicles with violations: {len(self.violation_summary)}\n")
                f.write(f"Total violation records: {len(self.threshold_violations)}\n")
                
                df_viol = pd.DataFrame(self.threshold_violations)
                f.write(f"Average deficit: {df_viol['deficit_percent'].mean():.3f}%\n")
                f.write(f"Maximum deficit: {df_viol['deficit_percent'].max():.3f}%\n")
                f.write(f"Minimum SOC reached: {df_viol['current_soc_percent'].min():.3f}%\n")
                f.write("\n")
                
                f.write("VEHICLE-WISE DETAILS\n")
                f.write("-"*70 + "\n")
                for veh_id, data in sorted(self.violation_summary.items()):
                    f.write(f"\n{veh_id} ({data['vehicle_type']})\n")
                    f.write(f"  First violation: {data['first_violation_time']}s at {data['first_violation_soc']:.2f}%\n")
                    f.write(f"  Minimum SOC: {data['min_soc_reached']:.3f}%\n")
                    f.write(f"  Maximum deficit: {data['max_deficit']:.3f}%\n")
                    f.write(f"  Total violations: {data['total_violations']}\n")
            else:
                f.write("No threshold violations detected.\n")
                f.write(f"All vehicles maintained SOC above {self.SOC_THRESHOLD}%\n")
        
        print(f"\n✓ Detailed report: {report_file}")
        print("="*70)


def main():
    """Main execution"""
    
    print("\n" + "="*70)
    print("SIMPLE SOC THRESHOLD VIOLATION TRACKER")
    print("Monitors vehicles dropping below 30% SOC")
    print("="*70 + "\n")
    
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = False  # Set True to visualize
    MAX_TIME = 600
    
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: {SUMOCFG} not found!")
        print("Make sure you're in the correct directory.")
        return
    
    # Create tracker
    tracker = SimpleSOCTracker(sumocfg=SUMOCFG, output_folder=OUTPUT_FOLDER)
    
    # Run simulation
    success = tracker.run_simulation(gui=USE_GUI, max_time=MAX_TIME)
    
    if not success:
        print("\n✗ Simulation failed!")
        return
    
    # Export results
    tracker.export_results()
    
    print(f"\n✓ COMPLETE!")
    print(f"Check {OUTPUT_FOLDER}/ for:")
    print(f"  - THRESHOLD_VIOLATIONS_ALL_*.csv (all violations)")
    print(f"  - VIOLATION_SUMMARY_*.csv (per-vehicle summary)")
    print(f"  - THRESHOLD_REPORT_*.txt (detailed report)")
    print(f"  - all_vehicle_data_*.csv (complete data)")
    print()


if __name__ == "__main__":
    main()
    