"""
Enhanced Smart Charging Simulation with Queue Management
Features: Separate charging and waiting slots, intelligent queue management
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


class SmartChargingStationMonitor:
    
    # ========== Configuration ==========
    SOC_THRESHOLD = 30.0
    SOC_TARGET = 70.0
    MIN_CHARGE_TIME = 30
    MAX_CHARGE_TIME = 300
    
    # Charging stations (matching your XML with separate charging/waiting slots)
    # Charging stations with separate charging and waiting parking areas
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
        
        # Existing data structures
        self.vehicle_data = []
        self.charging_events = []
        self.low_soc_alerts = []
        self.load_demand_data = []
        self.vehicle_states = {}
        self.initial_soc = {}
        
        # NEW: Enhanced station tracking with separate charging/waiting
        self.station_charging_slots = {}  # {station_id: set(vehicle_ids)}
        self.station_waiting_queue = {}   # {station_id: deque(vehicle_ids)} - FIFO queue
        self.currently_charging = {}      # {vehicle_id: station_id}
        self.currently_waiting = {}       # {vehicle_id: station_id}
        
        # Initialize station tracking
        for station_id in self.CHARGING_STATIONS.keys():
            self.station_charging_slots[station_id] = set()
            self.station_waiting_queue[station_id] = deque()
        
        # Detailed monitoring
        self.station_snapshots = []
        self.station_vehicle_history = defaultdict(list)
        self.queue_events = []  # NEW: Track queue join/leave events
        
        print("✓ Enhanced Charging Station Monitor with Queue Management Initialized")
        print(f"  SOC: {self.SOC_THRESHOLD}% → {self.SOC_TARGET}%")
        total_charging = sum(s['charging_slots'] for s in self.CHARGING_STATIONS.values())
        total_waiting = sum(s['waiting_slots'] for s in self.CHARGING_STATIONS.values())
        print(f"  Stations: {len(self.CHARGING_STATIONS)} ({total_charging} charging slots + {total_waiting} waiting slots)")
    
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
        """Detect if vehicle is at a charging station (charging or waiting area)"""
        # Check if already tracked
        if vid in self.currently_charging:
            return self.currently_charging[vid]
        if vid in self.currently_waiting:
            return self.currently_waiting[vid]
        
        # Check stops to see which parking area vehicle is at
        try:
            stops = traci.vehicle.getStops(vid)
            if stops:
                for stop in stops:
                    if hasattr(stop, 'stoppingPlaceID'):
                        place_id = stop.stoppingPlaceID
                        
                        # Check if it's a charging or waiting area
                        for station_id, info in self.CHARGING_STATIONS.items():
                            if place_id == info.get('charging_area') or place_id == info.get('waiting_area'):
                                speed = traci.vehicle.getSpeed(vid)
                                if speed < 0.5:
                                    return station_id
        except:
            pass
        
        return None
    
    def is_station_available(self, station_id, check_waiting=True):
        """
        Check if station has availability
        Returns: 'charging' if charging slot available, 'waiting' if only waiting slot available, None if full
        """
        station_info = self.CHARGING_STATIONS[station_id]
        charging_occupied = len(self.station_charging_slots[station_id])
        waiting_occupied = len(self.station_waiting_queue[station_id])
        
        # Check charging slots first
        if charging_occupied < station_info['charging_slots']:
            return 'charging'
        
        # Check waiting slots if charging is full
        if check_waiting and waiting_occupied < station_info['waiting_slots']:
            return 'waiting'
        
        return None
    
    def find_nearest_reachable_station(self, vid):
        try:
            cur_edge = traci.vehicle.getRoadID(vid)
            if not cur_edge or cur_edge.startswith(':'):
                return None
        except:
            return None

        candidates = []

        # Collect all reachable stations
        for sid, info in self.CHARGING_STATIONS.items():
            try:
                route = traci.simulation.findRoute(cur_edge, info['edge'])
                if route and route.length > 0:
                    candidates.append((route.length, sid, info, route))
            except:
                continue

        if not candidates:
            return None

        # Sort by distance
        candidates.sort(key=lambda x: x[0])

        # ---------- RULE 1: Nearest → CHARGING ONLY ----------
        dist1, sid1, info1, route1 = candidates[0]
        if self.is_station_available(sid1, check_waiting=False) == 'charging':
            return {
                'id': sid1,
                'info': info1,
                'route_to': route1,
                'availability': 'charging',
                'total_length': dist1
            }

        # ---------- RULE 2–5: Second nearest ----------
        if len(candidates) < 2:
            return None

        dist2, sid2, info2, route2 = candidates[1]
        availability2 = self.is_station_available(sid2, check_waiting=True)

        # Rule 3
        if availability2 == 'charging':
            return {
                'id': sid2,
                'info': info2,
                'route_to': route2,
                'availability': 'charging',
                'total_length': dist2
            }

        # Rule 4
        if availability2 == 'waiting':
            return {
                'id': sid2,
                'info': info2,
                'route_to': route2,
                'availability': 'waiting',
                'total_length': dist2
            }

        # Rule 5: Do NOT route anywhere
        return None

    
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
        """Route vehicle to station and assign to charging or waiting slot"""
        try:
            sid = choice['id']
            info = choice['info']
            route_to = choice.get('route_to')
            availability = choice.get('availability')
            
            charge_time = self.calculate_charge_time(batt, info)
            
            # Build route
            edges = list(route_to.edges) if route_to and hasattr(route_to, 'edges') else []
            if not edges:
                return False
            
            # Add return route
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
            
            # Clean route
            cleaned = []
            for e in edges:
                if not cleaned or cleaned[-1] != e:
                    cleaned.append(e)
            
            # Set route and stop
            # Set route and stop - route to appropriate parking area
            if availability == 'charging':
                parking_area = info['charging_area']
            elif availability == 'waiting':
                parking_area = info['waiting_area']
                # charge_time = 999999  # Long wait for waiting area
            else:
                parking_area = info.get('charging_area', sid)

            traci.vehicle.setRoute(vid, cleaned)
            traci.vehicle.setParkingAreaStop(vid, parking_area, duration=charge_time)
            
            # Update vehicle state
            if vid not in self.vehicle_states:
                self.vehicle_states[vid] = {}
            self.vehicle_states[vid].update({
                'routed_to': sid,
                'routed_time': traci.simulation.getTime(),
                'scheduled_charge_time': charge_time,
                'charge_scheduled': True,
                'expected_slot': availability  # 'charging' or 'waiting'
            })
            
            print(f"🔌 {vid} → {sid} [{availability}] | {charge_time:.0f}s | {choice.get('total_length',0):.1f}m")
            return True
        except Exception as e:
            print(f"⚠ Route failed: {e}")
            return False
    
    def assign_vehicle_to_slot(self, vid, station_id, t):
        """Assign vehicle to charging or waiting parking area based on availability"""
        availability = self.is_station_available(station_id, check_waiting=True)
        station_info = self.CHARGING_STATIONS[station_id]
        
        if availability == 'charging':
            # Assign to CHARGING parking area
            charging_area_id = station_info['charging_area']
            
            self.station_charging_slots[station_id].add(vid)
            self.currently_charging[vid] = station_id
            
            if vid not in self.vehicle_states:
                self.vehicle_states[vid] = {}
            
            batt = self.get_battery_info(vid)
            soc = batt['soc_percent'] if batt else 0.0
            
            self.vehicle_states[vid].update({
                'charging_start': t,
                'soc_start': soc,
                'charging_station_active': station_id,
                'slot_type': 'charging',
                'parking_area': charging_area_id
            })
            
            print(f"🔋 {vid} @ {station_id} [CHARGING AREA] | {soc:.1f}%")
            return True
            
        elif availability == 'waiting':
            # Assign to WAITING parking area
            waiting_area_id = station_info['waiting_area']
            
            self.station_waiting_queue[station_id].append(vid)
            self.currently_waiting[vid] = station_id
            
            if vid not in self.vehicle_states:
                self.vehicle_states[vid] = {}
            
            self.vehicle_states[vid].update({
                'waiting_start': t,
                'waiting_station': station_id,
                'slot_type': 'waiting',
                'parking_area': waiting_area_id
            })
            
            queue_pos = len(self.station_waiting_queue[station_id])
            print(f"⏳ {vid} @ {station_id} [WAITING AREA] | Queue pos: {queue_pos}")
            
            # Log queue event
            self.queue_events.append({
                'timestep_sec': t,
                'vehicle_id': vid,
                'station_id': station_id,
                'event': 'joined_queue',
                'queue_position': queue_pos
            })
            return True
        
        else:
            print(f"❌ {vid} @ {station_id} - STATION FULL!")
            return False
    
    
    def promote_waiting_vehicles(self, station_id, t):
        """Move vehicles from waiting area to charging area when slots available"""
        promoted_count = 0
        station_info = self.CHARGING_STATIONS[station_id]
        
        while self.station_waiting_queue[station_id]:
            # Check if charging slot available
            if self.is_station_available(station_id, check_waiting=False) != 'charging':
                break
            
            # Get next vehicle from queue
            vid = self.station_waiting_queue[station_id].popleft()
            
            # Check if vehicle still exists
            try:
                if vid not in traci.vehicle.getIDList():
                    self.currently_waiting.pop(vid, None)
                    continue
            except:
                self.currently_waiting.pop(vid, None)
                continue
            
            # Remove from waiting tracking
            self.currently_waiting.pop(vid, None)
            
            # Calculate charge time
            batt = self.get_battery_info(vid)
            if not batt:
                continue
            charge_time = self.calculate_charge_time(batt, station_info)
            
            # MOVE from WAITING area to CHARGING area
            try:
                charging_area_id = station_info['charging_area']
                
                # Resume vehicle and reroute to charging area
                traci.vehicle.resume(vid)
                traci.vehicle.setParkingAreaStop(vid, charging_area_id, duration=charge_time)
                
            except Exception as e:
                print(f"⚠ Could not promote {vid} to charging area: {e}")
                continue
            
            # Add to charging slot
            self.station_charging_slots[station_id].add(vid)
            self.currently_charging[vid] = station_id
            
            # Update vehicle state
            vs = self.vehicle_states.get(vid, {})
            wait_start = vs.pop('waiting_start', t)
            wait_time = t - wait_start
            
            soc = batt['soc_percent']
            
            vs.update({
                'charging_start': t,
                'soc_start': soc,
                'charging_station_active': station_id,
                'slot_type': 'charging',
                'wait_time_sec': wait_time,
                'parking_area': charging_area_id
            })
            
            print(f"⬆️ {vid} @ {station_id} [WAITING→CHARGING] | Waited {wait_time:.0f}s | {soc:.1f}%")
            
            # Log queue event
            self.queue_events.append({
                'timestep_sec': t,
                'vehicle_id': vid,
                'station_id': station_id,
                'event': 'promoted_to_charging',
                'wait_time_sec': round(wait_time, 1)
            })
            
            promoted_count += 1
        
        return promoted_count
    
    
    def monitor_charging(self, t):
        """Monitor charging and waiting vehicles, manage queue promotions"""
        try:
            vids = set(traci.vehicle.getIDList())
        except:
            return
        
        # Clean up departed vehicles
        for vid in list(self.vehicle_states.keys()):
            if vid not in vids:
                self.cleanup_departed_vehicle(vid)
        
        # Track vehicles at stations
        for vid in vids:
            cs = self.get_charging_station_id(vid)
            
            if cs and cs in self.CHARGING_STATIONS:
                # Vehicle is at a station
                vs = self.vehicle_states.get(vid, {})
                
                # Check if vehicle just arrived
                if vid not in self.currently_charging and vid not in self.currently_waiting:
                    # New arrival - assign to slot
                    self.assign_vehicle_to_slot(vid, cs, t)
            
            else:
                # Vehicle not at station - check if it was charging/waiting
                if vid in self.currently_charging:
                    self.handle_charging_complete(vid, t)
                elif vid in self.currently_waiting:
                    self.handle_waiting_left(vid, t)
        
        # Promote waiting vehicles to charging slots
        for station_id in self.CHARGING_STATIONS.keys():
            if self.station_waiting_queue[station_id]:
                self.promote_waiting_vehicles(station_id, t)
    
    def cleanup_departed_vehicle(self, vid):
        """Clean up tracking for departed vehicle"""
        vs = self.vehicle_states.get(vid, {})
        station = vs.get('routed_to') or vs.get('charging_station_active') or vs.get('waiting_station')
        
        # Remove from charging slots
        if vid in self.currently_charging:
            if station and station in self.station_charging_slots:
                self.station_charging_slots[station].discard(vid)
            self.currently_charging.pop(vid, None)
        
        # Remove from waiting queue
        if vid in self.currently_waiting:
            if station and station in self.station_waiting_queue:
                try:
                    self.station_waiting_queue[station].remove(vid)
                except ValueError:
                    pass
            self.currently_waiting.pop(vid, None)
        
        # Remove vehicle state
        self.vehicle_states.pop(vid, None)
    
    def handle_charging_complete(self, vid, t):
        """Handle vehicle leaving charging slot"""
        station = self.currently_charging[vid]
        vs = self.vehicle_states.get(vid, {})
        
        # Get charging stats
        start = vs.get('charging_start', t)
        soc0 = vs.get('soc_start', 0)
        wait_time = vs.get('wait_time_sec', 0)
        
        batt = self.get_battery_info(vid)
        if not batt:
            # Cleanup
            self.station_charging_slots[station].discard(vid)
            del self.currently_charging[vid]
            vs.pop('charging_start', None)
            return
        
        dur = t - start
        
        # Log charging event
        self.charging_events.append({
            'vehicle_id': vid,
            'vehicle_type': traci.vehicle.getTypeID(vid),
            'charging_station': station,
            'start_time_sec': start,
            'end_time_sec': t,
            'duration_sec': round(dur, 1),
            'wait_time_sec': round(wait_time, 1),
            'soc_at_start_percent': round(soc0, 2),
            'soc_at_end_percent': round(batt['soc_percent'], 2),
            'soc_gained_percent': round(batt['soc_percent'] - soc0, 2)
        })
        
        # Cleanup
        self.station_charging_slots[station].discard(vid)
        del self.currently_charging[vid]
        
        vs.pop('charging_start', None)
        vs.pop('soc_start', None)
        vs.pop('charging_station_active', None)
        vs.pop('routed_to', None)
        vs.pop('charge_scheduled', None)
        vs.pop('slot_type', None)
        vs.pop('wait_time_sec', None)
        
        print(f"✅ {vid} @ {station} | {dur:.0f}s charge | {soc0:.1f}%→{batt['soc_percent']:.1f}% (+{batt['soc_percent']-soc0:.1f}%)")
    
    def handle_waiting_left(self, vid, t):
        """Handle vehicle leaving waiting queue"""
        station = self.currently_waiting[vid]
        vs = self.vehicle_states.get(vid, {})
        
        wait_start = vs.get('waiting_start', t)
        wait_time = t - wait_start
        
        # Log queue event
        self.queue_events.append({
            'timestep_sec': t,
            'vehicle_id': vid,
            'station_id': station,
            'event': 'left_queue',
            'wait_time_sec': round(wait_time, 1)
        })
        
        # Cleanup
        try:
            self.station_waiting_queue[station].remove(vid)
        except ValueError:
            pass
        
        del self.currently_waiting[vid]
        
        vs.pop('waiting_start', None)
        vs.pop('waiting_station', None)
        vs.pop('slot_type', None)
        
        print(f"❌ {vid} left waiting @ {station} | Waited {wait_time:.0f}s")
    
    def capture_station_snapshot(self, t):
        """Capture detailed snapshot of all stations"""
        for station_id, station_info in self.CHARGING_STATIONS.items():
            # Charging vehicles
            charging_vids = list(self.station_charging_slots[station_id])
            charging_times = []
            total_power_kW = 0.0
            
            for vid in charging_vids:
                vs = self.vehicle_states.get(vid, {})
                charge_start = vs.get('charging_start', t)
                duration = t - charge_start
                charging_times.append(round(duration, 1))
                total_power_kW += station_info['power_kW']
                
                # Track vehicle history
                batt = self.get_battery_info(vid)
                soc = batt['soc_percent'] if batt else 0.0
                
                self.station_vehicle_history[station_id].append({
                    'timestep_sec': t,
                    'vehicle_id': vid,
                    'vehicle_type': traci.vehicle.getTypeID(vid),
                    'slot_type': 'charging',
                    'charging_duration_sec': round(duration, 1),
                    'current_soc_percent': round(soc, 2),
                    'power_consumption_kW': station_info['power_kW']
                })
            
            # Waiting vehicles
            waiting_vids = list(self.station_waiting_queue[station_id])
            waiting_times = []
            
            for vid in waiting_vids:
                vs = self.vehicle_states.get(vid, {})
                wait_start = vs.get('waiting_start', t)
                duration = t - wait_start
                waiting_times.append(round(duration, 1))
                
                # Track vehicle history
                self.station_vehicle_history[station_id].append({
                    'timestep_sec': t,
                    'vehicle_id': vid,
                    'vehicle_type': traci.vehicle.getTypeID(vid),
                    'slot_type': 'waiting',
                    'waiting_duration_sec': round(duration, 1),
                    'current_soc_percent': 0,
                    'power_consumption_kW': 0
                })
            
            # Create snapshot
            snapshot = {
                'timestep_sec': t,
                'station_id': station_id,
                'station_edge': station_info['edge'].replace('-', 'NEG_') if station_info['edge'].startswith('-') else station_info['edge'],
                'charging_capacity': station_info['charging_slots'],
                'waiting_capacity': station_info['waiting_slots'],
                'vehicles_charging': len(charging_vids),
                'vehicles_waiting': len(waiting_vids),
                'charging_vehicle_ids': ','.join(charging_vids) if charging_vids else 'NONE',
                'waiting_vehicle_ids': ','.join(waiting_vids) if waiting_vids else 'NONE',
                'charging_times_sec': ','.join(map(str, charging_times)) if charging_times else 'NONE',
                'waiting_times_sec': ','.join(map(str, waiting_times)) if waiting_times else 'NONE',
                'total_power_load_kW': round(total_power_kW, 3),
                'charging_utilization_percent': round((len(charging_vids) / station_info['charging_slots']) * 100, 1),
                'waiting_utilization_percent': round((len(waiting_vids) / station_info['waiting_slots']) * 100, 1) if station_info['waiting_slots'] > 0 else 0,
                'available_charging_slots': station_info['charging_slots'] - len(charging_vids),
                'available_waiting_slots': station_info['waiting_slots'] - len(waiting_vids)
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
            'total_vehicles_waiting': sum(len(q) for q in self.station_waiting_queue.values()),
            'total_power_demand_kW': round(total, 3),
            'total_power_demand_MW': round(total / 1000, 6)
        }
        
        for s, d in loads.items():
            rec[f'{s}_vehicles'] = d['vehicles']
            rec[f'{s}_power_kW'] = round(d['power_kW'], 3)
        
        self.load_demand_data.append(rec)
    
    def collect_data(self, t):
        # Monitor charging and queue management FIRST
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
                
                # Check if needs charging
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
                            'route_length_m': round(choice.get('total_length', 0), 2),
                            'slot_availability': choice.get('availability', 'unknown')
                        })
                        self.reroute_and_schedule_charge(v, choice, b)
                
                # Collect vehicle tracking data
                try:
                    pos = traci.vehicle.getPosition(v)
                    spd = traci.vehicle.getSpeed(v)
                    dist = traci.vehicle.getDistance(v)
                    lane = traci.vehicle.getLaneID(v)
                    road = traci.vehicle.getRoadID(v)
                except:
                    pos, spd, dist, lane, road = (0,0), 0, 0, "UNK", "UNK"
                
                # Determine vehicle status
                status = 'driving'
                if v in self.currently_charging:
                    status = 'charging'
                elif v in self.currently_waiting:
                    status = 'waiting'
                
                self.vehicle_data.append({
                    'timestep_sec': t,
                    'vehicle_id': v,
                    'vehicle_type': traci.vehicle.getTypeID(v),
                    'status': status,
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
        print(f"\n{'='*70}\nENHANCED QUEUE MANAGEMENT SIMULATION\n{'='*70}")
        
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
                    wait = sum(len(q) for q in self.station_waiting_queue.values())
                    load = self.load_demand_data[-1]['total_power_demand_kW'] if self.load_demand_data else 0
                    print(f"⏱️ {int(t)}s | Active:{active} Charging:{chrg} Waiting:{wait} Load:{load:.1f}kW")
            
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
        
        # Export queue events (NEW)
        if self.queue_events:
            df = pd.DataFrame(self.queue_events)
            f = os.path.join(self.output_folder, f'queue_events_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Queue Events: {f} ({len(df):,} events)")
            
            # Queue statistics
            joined = df[df['event'] == 'joined_queue']
            promoted = df[df['event'] == 'promoted_to_charging']
            if len(promoted) > 0:
                avg_wait = promoted['wait_time_sec'].mean()
                max_wait = promoted['wait_time_sec'].max()
                print(f"  Avg Wait: {avg_wait:.1f}s | Max Wait: {max_wait:.1f}s")
        
        # Export station snapshots
        if self.station_snapshots:
            df = pd.DataFrame(self.station_snapshots)
            f = os.path.join(self.output_folder, f'station_snapshots_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Station Snapshots: {f} ({len(df):,} records)")
            
            # Station summary
            print("\n📊 STATION UTILIZATION SUMMARY:")
            for station_id in self.CHARGING_STATIONS.keys():
                station_data = df[df['station_id'] == station_id]
                if len(station_data) > 0:
                    avg_chrg_util = station_data['charging_utilization_percent'].mean()
                    avg_wait_util = station_data['waiting_utilization_percent'].mean()
                    max_chrg = station_data['vehicles_charging'].max()
                    max_wait = station_data['vehicles_waiting'].max()
                    print(f"  {station_id}:")
                    print(f"    Charging: Avg {avg_chrg_util:.1f}% | Peak {int(max_chrg)} vehicles")
                    print(f"    Waiting:  Avg {avg_wait_util:.1f}% | Peak {int(max_wait)} vehicles")
        
        # Export vehicle-station history
        if self.station_vehicle_history:
            all_records = []
            for station_id, records in self.station_vehicle_history.items():
                all_records.extend(records)
            
            if all_records:
                df = pd.DataFrame(all_records)
                f = os.path.join(self.output_folder, f'vehicle_station_history_{ts}.csv')
                df.to_csv(f, index=False)
                print(f"✓ Vehicle-Station History: {f} ({len(df):,} records)")
        
        # Export vehicle tracking
        if self.vehicle_data:
            df = pd.DataFrame(self.vehicle_data)
            f = os.path.join(self.output_folder, f'vehicle_tracking_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Vehicle Tracking: {f} ({len(df):,} records)")
        
        # Export low SOC alerts
        if self.low_soc_alerts:
            df = pd.DataFrame(self.low_soc_alerts)
            f = os.path.join(self.output_folder, f'low_soc_alerts_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Low SOC Alerts: {f} ({len(df):,})")
        
        # Export charging events
        if self.charging_events:
            df = pd.DataFrame(self.charging_events)
            f = os.path.join(self.output_folder, f'charging_events_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Charging Events: {f} ({len(df):,})")
            if len(df) > 0:
                print(f"  Avg Charge Duration: {df['duration_sec'].mean():.1f}s")
                print(f"  Avg Wait Time: {df['wait_time_sec'].mean():.1f}s")
                print(f"  Avg SOC Gain: {df['soc_gained_percent'].mean():.1f}%")
        
        # Export load demand
        if self.load_demand_data:
            df = pd.DataFrame(self.load_demand_data)
            f = os.path.join(self.output_folder, f'load_demand_{ts}.csv')
            df.to_csv(f, index=False)
            print(f"✓ Load Demand: {f} ({len(df):,})")
            
            if len(df) > 0:
                peak = df['total_power_demand_kW'].max()
                avg = df[df['total_power_demand_kW'] > 0]['total_power_demand_kW'].mean()
                energy = df['total_power_demand_kW'].sum() / 3600
                maxv = df['total_vehicles_charging'].max()
                
                print(f"\n💡 SYSTEM LOAD SUMMARY:")
                print(f"  Peak Power: {peak:.2f} kW")
                print(f"  Avg Power: {avg:.2f} kW")
                print(f"  Total Energy: {energy:.3f} kWh")
                print(f"  Max Simultaneous Charging: {int(maxv)} vehicles")
        
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