"""
Enhanced Smart Charging Simulation with Detailed Station Monitoring
Tracks: Station occupancy, vehicle IDs, charging duration, and power load per station
"""

import os
import sys
import traceback
from datetime import datetime
from collections import defaultdict

try:
    import traci
    print("✓ TraCI imported successfully")
except ImportError:
    print("✗ ERROR: TraCI not found! Install: pip install traci")
    sys.exit(1)

import pandas as pd


class SmartChargingStationMonitor:
    
    # ========== Configuration ==========
    SOC_THRESHOLD = 30.0
    SOC_TARGET = 70.0
    MIN_CHARGE_TIME = 30
    MAX_CHARGE_TIME = 300
    
    # Charging stations (matching your XML)
    CHARGING_STATIONS = {
        'pa_2': {'lane': 'E0_0', 'edge': 'E0', 'startPos': 745.11, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_3': {'lane': 'E1_0', 'edge': 'E1', 'startPos': 727.99, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_6': {'lane': 'E5_0', 'edge': 'E5', 'startPos': 250.48, 'power_kW': 25.0, 'efficiency': 0.95, 'capacity': 5},
        'pa_7': {'lane': 'E6_0', 'edge': 'E6', 'startPos': 420.48, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_8': {'lane': 'E7_0', 'edge': 'E7', 'startPos': 830.91, 'power_kW': 25.0, 'efficiency': 0.95, 'capacity': 5},
        'pa_2_rev': {'lane': '-E0_0', 'edge': '-E0', 'startPos': 0.54, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_3_rev': {'lane': '-E1_0', 'edge': '-E1', 'startPos': 0.38, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_6_rev': {'lane': '-E5_0', 'edge': '-E5', 'startPos': 0.08, 'power_kW': 25.0, 'efficiency': 0.95, 'capacity': 5},
        'pa_7_rev': {'lane': '-E6_0', 'edge': '-E6', 'startPos': 1.10, 'power_kW': 20.0, 'efficiency': 0.95, 'capacity': 4},
        'pa_8_rev': {'lane': '-E7_0', 'edge': '-E7', 'startPos': 0.05, 'power_kW': 25.0, 'efficiency': 0.95, 'capacity': 5}
    }
    
    def __init__(self, sumocfg='Test1.sumocfg', output_folder='simulation_outputs'):
        self.sumocfg = sumocfg
        self.output_folder = output_folder
        os.makedirs(output_folder, exist_ok=True)
        
        # Existing data structures
        self.vehicle_data = []
        self.charging_events = []
        self.low_soc_alerts = []
        self.load_demand_data = []
        self.vehicle_states = {}
        self.initial_soc = {}
        self.station_occupancy = {}
        self.currently_charging = {}
        
        # NEW: Detailed station monitoring
        self.station_snapshots = []  # Time-series snapshots of each station
        self.station_vehicle_history = defaultdict(list)  # Per-station vehicle tracking
        
        print("✓ Enhanced Charging Station Monitor Initialized")
        print(f"  SOC: {self.SOC_THRESHOLD}% → {self.SOC_TARGET}%")
        print(f"  Stations: {len(self.CHARGING_STATIONS)} ({sum(s['capacity'] for s in self.CHARGING_STATIONS.values())} total slots)")
    
    def get_battery_info(self, vid):
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
        """Detect if vehicle is charging"""
        # Method 1: Direct parameter check
        try:
            cs = traci.vehicle.getParameter(vid, "device.battery.chargingStationId")
            if cs and cs not in ("NULL", "", "None", "none"):
                return cs
        except:
            pass
        
        # Method 2: Alternative parameter name
        try:
            cs = traci.vehicle.getParameter(vid, "chargingStationId")
            if cs and cs not in ("NULL", "", "None", "none"):
                return cs
        except:
            pass
        
        # Method 3: Check stops
        try:
            stops = traci.vehicle.getStops(vid)
            if stops:
                for stop in stops:
                    if hasattr(stop, 'stoppingPlaceID'):
                        place_id = stop.stoppingPlaceID
                        if place_id in self.CHARGING_STATIONS:
                            speed = traci.vehicle.getSpeed(vid)
                            if speed < 0.5:
                                return place_id
        except:
            pass
        
        # Method 4: Check internal tracking
        if vid in self.currently_charging:
            return self.currently_charging[vid]
        
        return None
    
    def find_nearest_reachable_station(self, vid):
        try:
            cur_edge = traci.vehicle.getRoadID(vid)
            if not cur_edge or cur_edge.startswith(':'):
                return None
        except:
            return None
        
        best = None
        best_len = float('inf')
        
        for sid, info in self.CHARGING_STATIONS.items():
            edge = info.get('edge')
            if not edge:
                continue
            
            vs = self.vehicle_states.get(vid, {})
            if vs.get('routed_to') == sid:
                continue
            
            occupied = len(self.station_occupancy.get(sid, set()))
            if occupied >= info.get('capacity', 4):
                continue
            
            try:
                route_to = traci.simulation.findRoute(cur_edge, edge)
            except:
                continue
            
            if not route_to or not getattr(route_to, "edges", None) or edge not in route_to.edges:
                continue
            
            try:
                vroute = traci.vehicle.getRoute(vid)
                dest = vroute[-1] if vroute else None
            except:
                dest = None
            
            back_len = 0.0
            if dest:
                try:
                    rb = traci.simulation.findRoute(edge, dest)
                    back_len = rb.length if rb and hasattr(rb, 'length') else 0.0
                except:
                    pass
            
            total = getattr(route_to, "length", float('inf')) + back_len
            if total < best_len:
                best_len = total
                best = {'id': sid, 'info': info, 'route_to': route_to, 'route_back': None, 'total_length': total}
        
        return best
    
    def calculate_charge_time(self, batt, station):
        soc = batt.get('soc_percent', 0.0)
        cap = batt.get('capacity_Wh', 0.0)
        needed = max(0.0, (self.SOC_TARGET - soc) / 100.0 * cap)
        power = station.get('power_kW', 20.0) * 1000.0
        eff = station.get('efficiency', 0.95)
        
        if power * eff > 0 and needed > 0:
            time = (needed / (power * eff)) * 3600.0
        else:
            time = self.MIN_CHARGE_TIME
        
        return max(self.MIN_CHARGE_TIME, min(self.MAX_CHARGE_TIME, time))
    
    def reroute_and_schedule_charge(self, vid, choice, batt):
        try:
            sid = choice['id']
            info = choice['info']
            route_to = choice.get('route_to')
            
            charge_time = self.calculate_charge_time(batt, info)
            
            edges = list(route_to.edges) if route_to and hasattr(route_to, 'edges') else []
            if not edges:
                return False
            
            try:
                vroute = traci.vehicle.getRoute(vid)
                dest = vroute[-1] if vroute else None
                if dest:
                    rb = traci.simulation.findRoute(info['edge'], dest)
                    if rb and hasattr(rb, 'edges'):
                        back = rb.edges
                        if back and edges and back[0] == edges[-1]:
                            edges.extend(back[1:])
                        else:
                            edges.extend(back)
            except:
                pass
            
            cleaned = []
            for e in edges:
                if not cleaned or cleaned[-1] != e:
                    cleaned.append(e)
            
            traci.vehicle.setRoute(vid, cleaned)
            traci.vehicle.setParkingAreaStop(vid, sid, duration=charge_time)
            
            if sid not in self.station_occupancy:
                self.station_occupancy[sid] = set()
            self.station_occupancy[sid].add(vid)
            
            if vid not in self.vehicle_states:
                self.vehicle_states[vid] = {}
            self.vehicle_states[vid].update({
                'routed_to': sid,
                'routed_time': traci.simulation.getTime(),
                'scheduled_charge_time': charge_time,
                'charge_scheduled': True
            })
            
            print(f"🔌 {vid} → {sid} | {charge_time:.0f}s | {choice.get('total_length',0):.1f}m")
            return True
        except Exception as e:
            print(f"⚠ Route failed: {e}")
            return False
    
    def monitor_charging(self, t):
        try:
            vids = set(traci.vehicle.getIDList())
        except:
            return
        
        # Clean up departed vehicles
        for vid in list(self.vehicle_states.keys()):
            if vid not in vids:
                vs = self.vehicle_states[vid]
                s = vs.get('routed_to')
                if s and s in self.station_occupancy:
                    self.station_occupancy[s].discard(vid)
                    if not self.station_occupancy[s]:
                        del self.station_occupancy[s]
                self.currently_charging.pop(vid, None)
                del self.vehicle_states[vid]
        
        for vid in vids:
            cs = self.get_charging_station_id(vid)
            
            if cs:
                # Vehicle IS charging
                b = self.get_battery_info(vid)
                if not b:
                    continue
                
                self.currently_charging[vid] = cs
                
                if vid not in self.vehicle_states:
                    self.vehicle_states[vid] = {}
                
                if 'charging_start' not in self.vehicle_states[vid]:
                    self.vehicle_states[vid].update({
                        'charging_start': t,
                        'soc_start': b['soc_percent'],
                        'charging_station_active': cs
                    })
                    print(f"🔋 {vid} @ {cs} | {b['soc_percent']:.1f}%")
            else:
                # Vehicle NOT charging
                if vid in self.currently_charging:
                    del self.currently_charging[vid]
                
                if vid in self.vehicle_states and 'charging_start' in self.vehicle_states[vid]:
                    b = self.get_battery_info(vid)
                    if not b:
                        self.vehicle_states[vid].pop('charging_start', None)
                        continue
                    
                    vs = self.vehicle_states[vid]
                    start = vs.pop('charging_start')
                    soc0 = vs.pop('soc_start', 0)
                    station = vs.pop('charging_station_active', 'UNK')
                    dur = t - start
                    
                    self.charging_events.append({
                        'vehicle_id': vid,
                        'vehicle_type': traci.vehicle.getTypeID(vid),
                        'charging_station': station,
                        'start_time_sec': start,
                        'end_time_sec': t,
                        'duration_sec': round(dur, 1),
                        'soc_at_start_percent': round(soc0, 2),
                        'soc_at_end_percent': round(b['soc_percent'], 2),
                        'soc_gained_percent': round(b['soc_percent'] - soc0, 2)
                    })
                    
                    if station in self.station_occupancy:
                        self.station_occupancy[station].discard(vid)
                        if not self.station_occupancy[station]:
                            del self.station_occupancy[station]
                    
                    vs.pop('routed_to', None)
                    vs.pop('charge_scheduled', None)
                    
                    print(f"✅ {vid} @ {station} | {dur:.0f}s | {soc0:.1f}%→{b['soc_percent']:.1f}% (+{b['soc_percent']-soc0:.1f}%)")
    
    def capture_station_snapshot(self, t):
        """
        NEW: Capture detailed snapshot of all stations at current timestep
        Records: station ID, vehicle count, vehicle IDs, charging duration per vehicle, power load
        """
        for station_id, station_info in self.CHARGING_STATIONS.items():
            # Get vehicles currently at this station
            vehicles_at_station = []
            charging_times = []  # NEW: List to store charging times
            total_power_kW = 0.0
            
            for vid, charging_station in self.currently_charging.items():
                if charging_station == station_id:
                    vehicles_at_station.append(vid)
                    total_power_kW += station_info['power_kW']
                    
                    # Track individual vehicle charging duration
                    vs = self.vehicle_states.get(vid, {})
                    charge_start = vs.get('charging_start', t)
                    duration = t - charge_start
                    charging_times.append(round(duration, 1))  # NEW: Append charging time
                    
                    # Get battery info
                    batt = self.get_battery_info(vid)
                    soc = batt['soc_percent'] if batt else 0.0
                    
                    # Record detailed vehicle-station association
                    self.station_vehicle_history[station_id].append({
                        'timestep_sec': t,
                        'vehicle_id': vid,
                        'vehicle_type': traci.vehicle.getTypeID(vid),
                        'charging_duration_sec': round(duration, 1),
                        'current_soc_percent': round(soc, 2),
                        'power_consumption_kW': station_info['power_kW']
                    })
            
            # Create station snapshot
            snapshot = {
                'timestep_sec': t,
                'station_id': station_id,
                'station_edge': station_info['edge'].replace('-', 'NEG_') if station_info['edge'].startswith('-') else station_info['edge'],
                'station_capacity': station_info['capacity'],
                'vehicles_charging': len(vehicles_at_station),
                'vehicle_ids': ','.join(vehicles_at_station) if vehicles_at_station else 'NONE',
                'charging_times_sec': ','.join(map(str, charging_times)) if charging_times else 'NONE',  # NEW COLUMN
                'total_power_load_kW': round(total_power_kW, 3),
                'utilization_percent': round((len(vehicles_at_station) / station_info['capacity']) * 100, 1),
                'available_slots': station_info['capacity'] - len(vehicles_at_station)
            }
            
            self.station_snapshots.append(snapshot)
    
    def calculate_load(self, t):
        """Calculate system-wide load"""
        loads = {s: {'vehicles': 0, 'power_kW': 0.0} for s in self.CHARGING_STATIONS}
        total = 0.0
        
        for vid, station_id in self.currently_charging.items():
            if station_id in self.CHARGING_STATIONS:
                power = self.CHARGING_STATIONS[station_id]['power_kW']
                loads[station_id]['vehicles'] += 1
                loads[station_id]['power_kW'] += power
                total += power
        
        rec = {
            'timestep_sec': t,
            'total_vehicles_charging': sum(l['vehicles'] for l in loads.values()),
            'total_power_demand_kW': round(total, 3),
            'total_power_demand_MW': round(total / 1000, 6)
        }
        
        for s, d in loads.items():
            rec[f'{s}_vehicles'] = d['vehicles']
            rec[f'{s}_power_kW'] = round(d['power_kW'], 3)
        
        self.load_demand_data.append(rec)
    
    def collect_data(self, t):
        # Monitor charging FIRST
        self.monitor_charging(t)
        
        # Capture detailed station snapshot
        self.capture_station_snapshot(t)
        
        # Calculate load
        self.calculate_load(t)
        
        try:
            vids = traci.vehicle.getIDList()
        except:
            return
        
        for v in vids:
            try:
                b = self.get_battery_info(v)
                if not b:
                    continue
                
                if v not in self.initial_soc:
                    self.initial_soc[v] = b['soc_percent']
                
                vs = self.vehicle_states.get(v, {})
                if b['soc_percent'] < self.SOC_THRESHOLD and not vs.get('charge_scheduled'):
                    choice = self.find_nearest_reachable_station(v)
                    if choice:
                        self.low_soc_alerts.append({
                            'timestep_sec': t,
                            'vehicle_id': v,
                            'vehicle_type': traci.vehicle.getTypeID(v),
                            'current_soc_percent': round(b['soc_percent'], 2),
                            'nearest_station': choice['id'],
                            'route_length_m': round(choice.get('total_length', 0), 2)
                        })
                        self.reroute_and_schedule_charge(v, choice, b)
                
                try:
                    pos = traci.vehicle.getPosition(v)
                    spd = traci.vehicle.getSpeed(v)
                    dist = traci.vehicle.getDistance(v)
                    lane = traci.vehicle.getLaneID(v)
                    road = traci.vehicle.getRoadID(v)
                except:
                    pos, spd, dist, lane, road = (0,0), 0, 0, "UNK", "UNK"
                
                self.vehicle_data.append({
                    'timestep_sec': t,
                    'vehicle_id': v,
                    'vehicle_type': traci.vehicle.getTypeID(v),
                    'soc_percent': round(b['soc_percent'], 2),
                    'initial_soc_percent': round(self.initial_soc.get(v, b['soc_percent']), 2),
                    'soc_drop_percent': round(self.initial_soc.get(v, b['soc_percent']) - b['soc_percent'], 2),
                    'energy_consumed_Wh': round(b['energy_consumed_Wh'], 2),
                    'lane': str(lane),
                    'road_id': str(road),
                    'x_position': round(pos[0], 2),
                    'y_position': round(pos[1], 2),
                    'speed_ms': round(spd, 2),
                    'distance_m': round(dist, 2)
                })
            except:
                continue
    
    def run_simulation(self, gui=True, max_time=600):
        print(f"\n{'='*70}\nSTATION MONITORING SIMULATION\n{'='*70}")
        
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
                
                if int(t) == t:
                    self.collect_data(t)
                
                if int(t) % 30 == 0 and t > 0:
                    active = len(traci.vehicle.getIDList())
                    chrg = len(self.currently_charging)
                    occ = sum(len(v) for v in self.station_occupancy.values())
                    load = self.load_demand_data[-1]['total_power_demand_kW'] if self.load_demand_data else 0
                    print(f"⏱️ {int(t)}s | Active:{active} Charging:{chrg} Occupied:{occ} Load:{load:.1f}kW")
            
            traci.close()
            print(f"\n✓ Done at {t}s")
            return True
        except Exception as e:
            print(f"✗ Error: {e}")
            traceback.print_exc()
            try:
                traci.close()
            except:
                pass
            return False
    
    def export_results(self):
        print(f"\n{'='*70}\nEXPORTING RESULTS\n{'='*70}")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export station snapshots (NEW)
        if self.station_snapshots:
            df = pd.DataFrame(self.station_snapshots)
            f = os.path.join(self.output_folder, f'station_snapshots_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Station Snapshots: {f} ({len(df):,} records)")
            
            # Print station summary
            print("\n📊 STATION UTILIZATION SUMMARY:")
            for station_id in self.CHARGING_STATIONS.keys():
                station_data = df[df['station_id'] == station_id]
                if len(station_data) > 0:
                    avg_util = station_data['utilization_percent'].mean()
                    max_vehicles = station_data['vehicles_charging'].max()
                    total_vehicle_time = station_data['vehicles_charging'].sum()
                    print(f"  {station_id}: Avg {avg_util:.1f}% | Peak {int(max_vehicles)} vehicles | Total {int(total_vehicle_time)} vehicle-seconds")
        
        # Export vehicle-station history (NEW)
        if self.station_vehicle_history:
            all_records = []
            for station_id, records in self.station_vehicle_history.items():
                all_records.extend(records)
            
            if all_records:
                df = pd.DataFrame(all_records)
                f = os.path.join(self.output_folder, f'vehicle_station_history_{ts}.csv')
                df.to_csv(f, index=False)
                print(f"✓ Vehicle-Station History: {f} ({len(df):,} records)")
        
        # Export existing data
        if self.vehicle_data:
            df = pd.DataFrame(self.vehicle_data)
            f = os.path.join(self.output_folder, f'vehicle_tracking_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Vehicle Tracking: {f} ({len(df):,} records)")
        
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            f = os.path.join(self.output_folder, f'low_soc_alerts_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Low SOC Alerts: {f} ({len(df):,})")
        
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            f = os.path.join(self.output_folder, f'charging_events_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Charging Events: {f} ({len(df):,})")
            if len(df) > 0:
                print(f"  Avg Duration: {df['duration_sec'].mean():.1f}s")
                print(f"  Avg SOC Gain: {df['soc_gained_percent'].mean():.1f}%")
        
        if self.load_demand_data:
            df = pd.DataFrame(self.load_demand_data)
            f = os.path.join(self.output_folder, f'load_demand_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Load Demand: {f} ({len(df):,})")
            
            total_charging = df['total_vehicles_charging'].sum()
            if total_charging > 0:
                peak = df['total_power_demand_kW'].max()
                avg = df[df['total_power_demand_kW'] > 0]['total_power_demand_kW'].mean()
                energy = df['total_power_demand_kW'].sum() / 3600
                maxv = df['total_vehicles_charging'].max()
                
                print(f"\n💡 SYSTEM LOAD SUMMARY:")
                print(f"  Peak Power: {peak:.2f} kW")
                print(f"  Avg Power: {avg:.2f} kW")
                print(f"  Total Energy: {energy:.3f} kWh")
                print(f"  Max Simultaneous: {int(maxv)} vehicles")
        
        print(f"{'='*70}\n")


def main():
    SUMOCFG = 'Test1.sumocfg'
    OUTPUT = 'simulation_outputs'
    GUI = True
    MAX_TIME = 600
    
    if not os.path.exists(SUMOCFG):
        print(f"✗ ERROR: {SUMOCFG} not found!")
        return
    
    sim = SmartChargingStationMonitor(sumocfg=SUMOCFG, output_folder=OUTPUT)
    
    if sim.run_simulation(gui=GUI, max_time=MAX_TIME):
        sim.export_results()
        print("✓ COMPLETE!")
    else:
        print("✗ FAILED!")


if __name__ == "__main__":
    main()