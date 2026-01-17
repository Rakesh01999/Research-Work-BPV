"""
Enhanced Smart Charging Simulation with Optimized Charging and Slot Management

Key Features:
- Reduced max charging time for faster turnaround
- Automatic journey resumption after charging completion
- Dynamic slot management - stations become available immediately after vehicle departure
- Conservative route planning to avoid impossible routes
- Comprehensive telemetry and event logging

Requirements:
- TraCI (pip install traci)
- SUMO simulation environment
"""

import os
import sys
import traceback
from datetime import datetime

try:
    import traci
except ImportError:
    print("✗ ERROR: TraCI not installed. Install using: pip install traci")
    sys.exit(1)

import pandas as pd


class EnhancedSmartCharging:
    # ---------- Optimized Parameters ----------
    SOC_THRESHOLD = 30.0      # % threshold to trigger charging
    SOC_TARGET = 70.0         # % target after charging (increased for better range)
    
    MIN_CHARGE_TIME = 30      # seconds (reduced minimum)
    MAX_CHARGE_TIME = 300     # seconds (reduced from 600 to 300 for faster turnaround)
    
    # Charging station definitions (must match your additional XML)
    CHARGING_STATIONS = {
        # FORWARD DIRECTION STATIONS
        'pa_2':     {'lane': 'E0_0',  'edge': 'E0',  'startPos': 745.11, 'power': 20, 'efficiency': 0.95},
        'pa_3':     {'lane': 'E1_0',  'edge': 'E1',  'startPos': 727.99, 'power': 20, 'efficiency': 0.95},
        'pa_6':     {'lane': 'E5_0',  'edge': 'E5',  'startPos': 250.48, 'power': 25, 'efficiency': 0.95},
        'pa_7':     {'lane': 'E6_0',  'edge': 'E6',  'startPos': 420.48, 'power': 20, 'efficiency': 0.95},
        'pa_8':     {'lane': 'E7_0',  'edge': 'E7',  'startPos': 830.91, 'power': 25, 'efficiency': 0.95},

        # REVERSE DIRECTION STATIONS
        'pa_2_rev': {'lane': '-E0_0', 'edge': '-E0', 'startPos': 0.54,   'power': 20, 'efficiency': 0.95},
        'pa_3_rev': {'lane': '-E1_0', 'edge': '-E1', 'startPos': 0.38,   'power': 20, 'efficiency': 0.95},
        'pa_6_rev': {'lane': '-E5_0', 'edge': '-E5', 'startPos': 0.08,   'power': 25, 'efficiency': 0.95},
        'pa_7_rev': {'lane': '-E6_0', 'edge': '-E6', 'startPos': 1.10,   'power': 20, 'efficiency': 0.95},
        'pa_8_rev': {'lane': '-E7_0', 'edge': '-E7', 'startPos': 0.05,   'power': 25, 'efficiency': 0.95},
    }

    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        os.makedirs(self.output_folder, exist_ok=True)

        # Data collection structures
        self.vehicle_data = []
        self.low_soc_alerts = []
        self.charging_events = []
        self.vehicle_states = {}      # Per-vehicle runtime metadata
        self.initial_soc = {}         # Initial SOC per vehicle
        self.station_occupancy = {}   # Track which vehicle is at which station
        
        print("✓ Enhanced Smart Charging System Initialized")
        print(f"  SOC Threshold: {self.SOC_THRESHOLD}%")
        print(f"  SOC Target: {self.SOC_TARGET}%")
        print(f"  Max Charge Time: {self.MAX_CHARGE_TIME}s (optimized for quick turnaround)")

    # ========================
    # Utility Functions
    # ========================
    
    def sanitize_lane_id(self, lane_id):
        """Sanitize lane ID for CSV export"""
        if lane_id is None:
            return "UNKNOWN"
        lane_id = str(lane_id)
        if lane_id == "":
            return "UNKNOWN"
        if lane_id.startswith(':'):
            return "Internal_" + lane_id[1:]
        if lane_id.startswith('-'):
            return "NEG_" + lane_id[1:]
        return lane_id

    def get_battery_info(self, vid):
        """Retrieve comprehensive battery information for a vehicle"""
        try:
            # Try modern parameter names first
            try:
                charge = traci.vehicle.getParameter(vid, "device.battery.chargeLevel")
                capacity = traci.vehicle.getParameter(vid, "device.battery.capacity")
                energy_consumed = traci.vehicle.getParameter(vid, "device.battery.totalEnergyConsumed")
            except Exception:
                # Fallback to older parameter names
                charge = traci.vehicle.getParameter(vid, "actualBatteryCapacity") \
                         or traci.vehicle.getParameter(vid, "device.battery.actualBatteryCapacity")
                capacity = traci.vehicle.getParameter(vid, "maximumBatteryCapacity") \
                           or traci.vehicle.getParameter(vid, "device.battery.maximumBatteryCapacity")
                try:
                    energy_consumed = traci.vehicle.getParameter(vid, "device.battery.totalEnergyConsumed")
                except Exception:
                    energy_consumed = 0.0

            charge_f = float(charge) if charge is not None else 0.0
            capacity_f = float(capacity) if capacity is not None else 0.0
            energy_consumed_f = float(energy_consumed) if energy_consumed is not None else 0.0

            soc_percent = (charge_f / capacity_f * 100.0) if capacity_f > 0 else 0.0

            return {
                'charge_Wh': charge_f,
                'capacity_Wh': capacity_f,
                'soc_percent': soc_percent,
                'energy_consumed_Wh': energy_consumed_f
            }
        except Exception:
            return None

    def get_battery_info_safe(self, vid):
        """Safe wrapper for battery info retrieval"""
        try:
            return self.get_battery_info(vid)
        except Exception:
            return None

    # ========================
    # Route Planning Functions
    # ========================

    def find_nearest_reachable_station(self, vid):
        """
        Find the nearest charging station that is:
        1. Reachable from current position
        2. Not currently occupied
        3. Has the shortest route distance
        
        Returns dict with station info and route details, or None if no station available
        """
        try:
            cur_edge = traci.vehicle.getRoadID(vid)
            if not cur_edge or cur_edge.startswith(':'):
                return None
        except Exception:
            return None

        best = None
        best_len = float('inf')

        for sid, info in self.CHARGING_STATIONS.items():
            station_edge = info.get('edge')
            if station_edge is None:
                continue

            # Skip if already routed to this station
            vs = self.vehicle_states.get(vid, {})
            if vs.get('routed_to') == sid:
                continue
            
            # Skip if station is currently occupied
            if sid in self.station_occupancy:
                continue

            # Find route from current edge to station edge
            try:
                route_to = traci.simulation.findRoute(cur_edge, station_edge)
            except Exception:
                route_to = None

            if not route_to or not getattr(route_to, "edges", None):
                continue

            # Verify station edge is in the route
            if station_edge not in route_to.edges:
                continue

            # Get vehicle's destination for route planning
            dest_edge = None
            try:
                vroute = traci.vehicle.getRoute(vid)
                if vroute and len(vroute) > 0:
                    dest_edge = vroute[-1]
            except Exception:
                dest_edge = None

            # Plan route from station back to destination
            route_back = None
            back_len = 0.0
            if dest_edge:
                try:
                    route_back = traci.simulation.findRoute(station_edge, dest_edge)
                    if route_back and getattr(route_back, "length", None):
                        back_len = route_back.length
                except Exception:
                    route_back = None

            total_len = getattr(route_to, "length", float('inf')) + back_len

            if total_len < best_len:
                best_len = total_len
                best = {
                    'id': sid,
                    'info': info,
                    'route_to': route_to,
                    'route_back': route_back,
                    'total_length': total_len
                }

        return best

    def calculate_charge_time(self, batt_info, station_info):
        """Calculate optimal charging time based on battery state and station power"""
        current_soc = batt_info.get('soc_percent', 0.0)
        capacity = batt_info.get('capacity_Wh', 0.0)
        
        # Energy needed to reach target SOC
        energy_needed_Wh = max(0.0, (self.SOC_TARGET - current_soc) / 100.0 * capacity)
        
        # Station power and efficiency
        power_w = float(station_info.get('power', 20)) * 1000.0
        efficiency = float(station_info.get('efficiency', 0.95))
        
        # Calculate time (convert to seconds)
        if power_w * efficiency > 0 and energy_needed_Wh > 0:
            charge_time = (energy_needed_Wh / (power_w * efficiency)) * 3600.0
        else:
            charge_time = self.MIN_CHARGE_TIME
        
        # Apply bounds
        charge_time = max(self.MIN_CHARGE_TIME, min(self.MAX_CHARGE_TIME, charge_time))
        
        return charge_time

    # ========================
    # Charging Management
    # ========================

    def reroute_and_schedule_charge(self, vid, station_choice, batt_info):
        """
        Reroute vehicle to charging station and schedule charging stop.
        The vehicle will automatically resume journey after charging completes.
        """
        try:
            sid = station_choice['id']
            info = station_choice['info']
            route_to = station_choice.get('route_to')
            route_back = station_choice.get('route_back')

            # Calculate optimal charging time
            charge_time = self.calculate_charge_time(batt_info, info)

            # Build combined route: current -> station -> destination
            combined_edges = []
            
            if route_to and getattr(route_to, "edges", None):
                combined_edges.extend(route_to.edges)
            else:
                print(f"⚠ Cannot compute route to station {sid} for {vid}. Skipping.")
                return False

            # Add return route to destination
            if route_back and getattr(route_back, "edges", None):
                back_edges = route_back.edges
                # Avoid duplicating station edge at junction
                if back_edges and combined_edges and back_edges[0] == combined_edges[-1]:
                    combined_edges.extend(back_edges[1:])
                else:
                    combined_edges.extend(back_edges)

            # Remove consecutive duplicate edges
            cleaned = []
            for e in combined_edges:
                if not cleaned or cleaned[-1] != e:
                    cleaned.append(e)
            combined_edges = cleaned

            # Apply new route
            try:
                traci.vehicle.setRoute(vid, combined_edges)
            except Exception as e:
                print(f"⚠ setRoute failed for {vid} -> {sid}: {e}")
                return False

            # Schedule parking stop at charging station
            try:
                traci.vehicle.setParkingAreaStop(vid, sid, duration=charge_time)
            except Exception as e:
                print(f"⚠ setParkingAreaStop failed for {vid} -> {sid}: {e}")
                return False

            # Mark station as occupied
            self.station_occupancy[sid] = vid

            # Update vehicle state
            now = traci.simulation.getTime()
            if vid not in self.vehicle_states:
                self.vehicle_states[vid] = {}
            
            self.vehicle_states[vid].update({
                'routed_to': sid,
                'routed_time': now,
                'scheduled_charge_time': charge_time,
                'charge_scheduled': True
            })

            print(f"🔌 ROUTED {vid} -> {sid} | Charge time: {charge_time:.0f}s | Route: {station_choice.get('total_length', 0.0):.1f}m")
            return True
            
        except Exception:
            traceback.print_exc()
            return False

    def monitor_charging(self, sim_time):
        """
        Monitor charging events and manage station slot availability.
        When charging completes and vehicle departs, station slot is freed.
        """
        try:
            vids = traci.vehicle.getIDList()
        except Exception:
            return

        # Track which vehicles are currently in simulation
        active_vids = set(vids)
        
        # Check for vehicles that have left (completed their journey)
        for vid in list(self.vehicle_states.keys()):
            if vid not in active_vids:
                # Vehicle has left simulation - free any occupied station
                vs = self.vehicle_states.get(vid, {})
                station = vs.get('routed_to')
                if station and station in self.station_occupancy:
                    if self.station_occupancy[station] == vid:
                        del self.station_occupancy[station]
                        print(f"✅ STATION FREED: {station} (vehicle {vid} departed)")
                
                # Clean up vehicle state
                del self.vehicle_states[vid]

        for vid in vids:
            charging_station_id = None
            try:
                # Check if vehicle is currently at a charging station
                try:
                    charging_station_id = traci.vehicle.getParameter(vid, "device.battery.chargingStationId")
                except Exception:
                    try:
                        charging_station_id = traci.vehicle.getParameter(vid, "chargingStationId")
                    except Exception:
                        charging_station_id = None
            except Exception:
                charging_station_id = None

            # Vehicle is charging
            if charging_station_id and charging_station_id not in ("NULL", "", "None"):
                batt = self.get_battery_info_safe(vid)
                if batt is None:
                    continue
                    
                if vid not in self.vehicle_states:
                    self.vehicle_states[vid] = {}
                    
                # Record charging start
                if 'charging_start' not in self.vehicle_states[vid]:
                    self.vehicle_states[vid]['charging_start'] = sim_time
                    self.vehicle_states[vid]['soc_start'] = batt['soc_percent']
                    self.vehicle_states[vid]['charging_station_active'] = charging_station_id
                    print(f"🔋 CHARGING: {vid} @ {charging_station_id} | SOC {batt['soc_percent']:.2f}%")
                    
            else:
                # Vehicle has stopped charging
                if vid in self.vehicle_states and 'charging_start' in self.vehicle_states[vid]:
                    batt = self.get_battery_info_safe(vid)
                    if batt is None:
                        # Clean up markers
                        self.vehicle_states[vid].pop('charging_start', None)
                        self.vehicle_states[vid].pop('soc_start', None)
                        self.vehicle_states[vid].pop('charging_station_active', None)
                        continue

                    # Record charging completion event
                    start = self.vehicle_states[vid].pop('charging_start')
                    soc0 = self.vehicle_states[vid].pop('soc_start', 0.0)
                    station_used = self.vehicle_states[vid].pop('charging_station_active', 'UNKNOWN')
                    duration = sim_time - start

                    event = {
                        'vehicle_id': vid,
                        'vehicle_type': traci.vehicle.getTypeID(vid),
                        'charging_station': station_used,
                        'start_time_sec': start,
                        'end_time_sec': sim_time,
                        'duration_sec': round(duration, 1),
                        'soc_at_start_percent': round(soc0, 2),
                        'soc_at_end_percent': round(batt['soc_percent'], 2),
                        'soc_gained_percent': round(batt['soc_percent'] - soc0, 2)
                    }
                    self.charging_events.append(event)
                    
                    # Free the station slot
                    if station_used in self.station_occupancy:
                        if self.station_occupancy[station_used] == vid:
                            del self.station_occupancy[station_used]
                            print(f"✅ STATION AVAILABLE: {station_used} (charging complete)")
                    
                    # Clear routing state so vehicle can be rerouted if needed again
                    self.vehicle_states[vid].pop('routed_to', None)
                    self.vehicle_states[vid].pop('charge_scheduled', None)
                    
                    print(f"✅ CHARGE COMPLETE: {vid} @ {station_used} | {duration:.1f}s | SOC {soc0:.1f}% → {batt['soc_percent']:.1f}% (+{batt['soc_percent']-soc0:.1f}%)")
                    print(f"🚗 RESUMING JOURNEY: {vid}")

    # ========================
    # Data Collection
    # ========================

    def collect_vehicle_data(self, sim_time):
        """Collect vehicle telemetry and make charging decisions"""
        
        # Monitor charging status first
        self.monitor_charging(sim_time)

        try:
            vids = traci.vehicle.getIDList()
        except Exception:
            vids = []

        for vid in vids:
            try:
                batt = self.get_battery_info_safe(vid)
                if batt is None:
                    continue

                # Get lane and road info
                try:
                    lane_raw = traci.vehicle.getLaneID(vid)
                except Exception:
                    lane_raw = None
                try:
                    road_raw = traci.vehicle.getRoadID(vid)
                except Exception:
                    road_raw = None

                lane_s = self.sanitize_lane_id(lane_raw)
                road_s = self.sanitize_lane_id(road_raw)

                # Record initial SOC
                if vid not in self.initial_soc:
                    self.initial_soc[vid] = batt['soc_percent']

                # Check if charging needed
                vs = self.vehicle_states.get(vid, {})
                already_scheduled = vs.get('charge_scheduled', False)
                
                if batt['soc_percent'] < self.SOC_THRESHOLD and not already_scheduled:
                    station_choice = self.find_nearest_reachable_station(vid)
                    
                    if station_choice:
                        # Log alert
                        alert = {
                            'timestep_sec': sim_time,
                            'vehicle_id': vid,
                            'vehicle_type': traci.vehicle.getTypeID(vid),
                            'current_soc_percent': round(batt['soc_percent'], 2),
                            'nearest_station': station_choice['id'],
                            'route_length_m': round(station_choice.get('total_length', 0.0), 2)
                        }
                        self.low_soc_alerts.append(alert)
                        
                        # Schedule charging
                        self.reroute_and_schedule_charge(vid, station_choice, batt)

                # Collect telemetry
                try:
                    pos = traci.vehicle.getPosition(vid)
                except Exception:
                    pos = (0.0, 0.0)
                try:
                    speed = traci.vehicle.getSpeed(vid)
                except Exception:
                    speed = 0.0
                try:
                    distance = traci.vehicle.getDistance(vid)
                except Exception:
                    distance = 0.0

                record = {
                    'timestep_sec': sim_time,
                    'vehicle_id': vid,
                    'vehicle_type': traci.vehicle.getTypeID(vid),
                    'soc_percent': round(batt['soc_percent'], 2),
                    'initial_soc_percent': round(self.initial_soc.get(vid, batt['soc_percent']), 2),
                    'soc_drop_percent': round(self.initial_soc.get(vid, batt['soc_percent']) - batt['soc_percent'], 2),
                    'energy_consumed_Wh': round(batt['energy_consumed_Wh'], 2),
                    'lane': lane_s,
                    'road_id': road_s,
                    'x_position': round(pos[0], 2),
                    'y_position': round(pos[1], 2),
                    'speed_ms': round(speed, 2),
                    'distance_m': round(distance, 2)
                }

                self.vehicle_data.append(record)
                
            except Exception:
                traceback.print_exc()
                continue

    # ========================
    # Simulation Execution
    # ========================

    def run_simulation(self, gui=False, max_time=600):
        """Run the SUMO simulation with smart charging"""
        sumo_bin = "sumo-gui" if gui else "sumo"
        sumo_cmd = [sumo_bin, "-c", self.sumocfg, "--start", "--quit-on-end"]

        try:
            traci.start(sumo_cmd)
            print("✓ TraCI connection established")
            print("✓ Simulation started\n")
        except Exception as e:
            print("✗ Could not start TraCI:", e)
            traceback.print_exc()
            return False

        try:
            sim_time = 0.0
            while traci.simulation.getMinExpectedNumber() > 0 and sim_time < max_time:
                traci.simulationStep()
                sim_time = traci.simulation.getTime()

                # Collect data every second
                if int(sim_time) == sim_time:
                    self.collect_vehicle_data(sim_time)

                # Status update every 30 seconds
                if int(sim_time) % 30 == 0 and sim_time > 0:
                    try:
                        active = len(traci.vehicle.getIDList())
                    except Exception:
                        active = 0
                    charging_now = sum(1 for v in self.vehicle_states.values() if 'charging_start' in v)
                    occupied_stations = len(self.station_occupancy)
                    print(f"⏱ Time {int(sim_time)}s | Active: {active} | Charging: {charging_now} | Occupied Stations: {occupied_stations} | Total Alerts: {len(self.low_soc_alerts)}")

            traci.close()
            print(f"\n✓ Simulation completed at {sim_time}s")
            return True
            
        except Exception as e:
            print("✗ Simulation error:", e)
            traceback.print_exc()
            try:
                traci.close()
            except Exception:
                pass
            return False

    def export_results(self):
        """Export all collected data to CSV files"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        print("\n" + "="*60)
        print("EXPORTING RESULTS")
        print("="*60)

        # Export vehicle tracking data
        if self.vehicle_data:
            cols = [
                'timestep_sec', 'vehicle_id', 'vehicle_type',
                'soc_percent', 'initial_soc_percent', 'soc_drop_percent',
                'energy_consumed_Wh', 'lane', 'road_id',
                'x_position', 'y_position', 'speed_ms', 'distance_m'
            ]
            df = pd.DataFrame(self.vehicle_data, columns=cols)
            fname = os.path.join(self.output_folder, f"vehicle_tracking_{ts}.csv")
            df.to_csv(fname, index=False)
            print(f"✓ Vehicle tracking: {fname}")
            print(f"  Records: {len(df):,}")

        # Export low SOC alerts
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            fname = os.path.join(self.output_folder, f"low_soc_alerts_{ts}.csv")
            df.to_csv(fname, index=False)
            print(f"✓ Low SOC alerts: {fname}")
            print(f"  Alerts: {len(df):,}")

        # Export charging events
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            fname = os.path.join(self.output_folder, f"charging_events_{ts}.csv")
            df.to_csv(fname, index=False)
            print(f"✓ Charging events: {fname}")
            print(f"  Events: {len(df):,}")
            
            # Print summary statistics
            if len(df) > 0:
                print("\n  Charging Summary:")
                print(f"    Avg duration: {df['duration_sec'].mean():.1f}s")
                print(f"    Avg SOC gain: {df['soc_gained_percent'].mean():.1f}%")
                print(f"    Max SOC gain: {df['soc_gained_percent'].max():.1f}%")

        print("="*60)
        print("✓ Export complete")
        print("="*60 + "\n")


# ========================
# Main Entry Point
# ========================

def main():
    """Main execution function"""
    
    # Configuration
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT_FOLDER = 'simulation_outputs'
    USE_GUI = True              # Set to False for faster headless simulation
    MAX_TIME = 600              # Simulation time limit in seconds

    print("\n" + "="*60)
    print("ENHANCED SMART CHARGING SIMULATION")
    print("="*60)
    print(f"Config file: {SUMOCFG}")
    print(f"Output folder: {OUTPUT_FOLDER}")
    print(f"GUI mode: {'Enabled' if USE_GUI else 'Disabled'}")
    print(f"Max simulation time: {MAX_TIME}s")
    print("="*60 + "\n")

    # Check if config file exists
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: SUMO config '{SUMOCFG}' not found in current directory.")
        print(f"  Current directory: {os.getcwd()}")
        return

    # Create and run simulation
    sim = EnhancedSmartCharging(sumocfg=SUMOCFG, output_folder=OUTPUT_FOLDER)
    success = sim.run_simulation(gui=USE_GUI, max_time=MAX_TIME)
    
    if success:
        sim.export_results()
        print("✓ Simulation completed successfully!")
    else:
        print("✗ Simulation failed or terminated early.")


if __name__ == "__main__":
    main()