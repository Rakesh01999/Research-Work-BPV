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

import math
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
        self.ml_data = [] # New: Data for ML
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
        
        # NEW: Recommendation system
        self.recommendations = []
        self.recommendation_count = 0
        self.vehicle_last_recommendation = {}
        print(f"  ✓ Charging Recommendation System: Enabled")
    
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
    
    
    # ================= ML DATA COLLECTION HELPER METHODS =================
    
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
            # 'power_demand_kW': round(power_demand, 2),
            'queue_length': queue_length,
            'charging_slots_available': charging_slots_available,
            'waiting_slots_available': waiting_slots_available,
            'total_slots': config['charging_slots'] + config['waiting_slots'],
            'station_power_capacity_kW': config['power_kW'],
            'station_charging_capacity': config['charging_slots']
        }
    
    def calculate_system_features(self, timestep_sec):
        """Calculate system-wide features including detailed vehicle aggregates"""
        
        # Initialize aggregates
        total_vehicles = 0
        moving_vehicles = 0
        idle_vehicles = 0
        
        total_speed = 0.0
        total_accel = 0.0
        total_soc = 0.0
        
        moving_speed = 0.0
        moving_soc = 0.0
        
        charging_soc = 0.0
        charging_duration_sum = 0.0
        
        # Get all active vehicles
        try:
            vids = traci.vehicle.getIDList()
            total_vehicles = len(vids)
        except:
            vids = []

        total_vehicles_charging = 0
        total_vehicles_waiting = 0
        
        # Calculate vehicle-level metrics
        if vids:
            for vid in vids:
                try:
                    # Speed & Acceleration
                    speed = traci.vehicle.getSpeed(vid)
                    try:
                        accel = traci.vehicle.getAcceleration(vid)
                    except:
                        accel = 0.0
                    
                    # SOC
                    batt = self.get_battery_info(vid)
                    soc = batt['soc_percent'] if batt else 0.0
                    
                    # Accumulate totals
                    total_speed += speed
                    total_accel += abs(accel) # Use absolute acceleration (magnitude of change)
                    total_soc += soc
                    
                    # Categorize Vehicle
                    is_charging = vid in self.currently_charging
                    is_waiting = vid in self.currently_waiting
                    
                    if is_charging:
                        total_vehicles_charging += 1
                        charging_soc += soc
                        
                        # Calculate current charging duration
                        vs = self.vehicle_states.get(vid, {})
                        start = vs.get('charging_start', timestep_sec)
                        charging_duration_sum += (timestep_sec - start)
                        
                    elif is_waiting:
                        total_vehicles_waiting += 1
                        
                    elif speed > 0.1: # Moving threshold
                        moving_vehicles += 1
                        moving_speed += speed
                        moving_soc += soc
                    else:
                        idle_vehicles += 1
                        
                except Exception:
                    continue
        
        # Averages
        avg_speed = total_speed / total_vehicles if total_vehicles > 0 else 0
        avg_accel = total_accel / total_vehicles if total_vehicles > 0 else 0
        avg_soc = total_soc / total_vehicles if total_vehicles > 0 else 0
        
        avg_moving_speed = moving_speed / moving_vehicles if moving_vehicles > 0 else 0
        avg_moving_soc = moving_soc / moving_vehicles if moving_vehicles > 0 else 0
        
        avg_charging_soc = charging_soc / total_vehicles_charging if total_vehicles_charging > 0 else 0
        avg_charging_duration = charging_duration_sum / total_vehicles_charging if total_vehicles_charging > 0 else 0

        # Station Power Totals
        total_power_demand = 0
        for station_id in self.CHARGING_STATIONS.keys():
            vehicles_at_station = len(self.station_charging_slots[station_id])
            power = vehicles_at_station * self.CHARGING_STATIONS[station_id]['power_kW']
            total_power_demand += power
        
        # System Capacity
        total_charging_capacity = sum(s['charging_slots'] for s in self.CHARGING_STATIONS.values())
        total_waiting_capacity = sum(s['waiting_slots'] for s in self.CHARGING_STATIONS.values())
        
        system_utilization = (total_vehicles_charging / total_charging_capacity) * 100 if total_charging_capacity > 0 else 0
        
        return {
            # Counts
            'total_active_vehicles': total_vehicles,
            'total_moving_vehicles': moving_vehicles,
            'total_vehicles_charging': total_vehicles_charging,
            'total_vehicles_waiting': total_vehicles_waiting,
            'total_idle_vehicles': idle_vehicles,
            
            # Averages
            'system_avg_speed_ms': round(avg_speed, 2),
            'system_avg_accel_ms2': round(avg_accel, 2),
            'system_avg_soc_percent': round(avg_soc, 2),
            'system_avg_moving_speed_ms': round(avg_moving_speed, 2),
            'system_avg_moving_soc_percent': round(avg_moving_soc, 2),
            'system_avg_charging_soc_percent': round(avg_charging_soc, 2),
            'system_avg_current_charging_duration_sec': round(avg_charging_duration, 1),
            
            # Power & Capacity
            'total_power_demand_kW': round(total_power_demand, 2),
            'system_charging_utilization_percent': round(system_utilization, 2),
            'total_charging_capacity': total_charging_capacity,
            'total_waiting_capacity': total_waiting_capacity
        }
    
    def collect_ml_features(self, timestep_sec):
        """Collect comprehensive ML-ready data: ONE ROW PER VEHICLE PER TIMESTEP"""
        
        # 1. Get Global Context (Time & System)
        time_features = self.get_time_features(timestep_sec)
        system_features = self.calculate_system_features(timestep_sec)
        
        # 2. Pre-calculate all station features
        # We need this efficient lookup to attach station context to vehicles near/at stations
        all_station_features = {}
        for station_id in self.CHARGING_STATIONS.keys():
            all_station_features[station_id] = self.calculate_station_features(station_id, timestep_sec)
            
        # 3. Iterate ALL Vehicles to create dataset
        try:
            vids = traci.vehicle.getIDList()
        except:
            vids = []
            
        for vid in vids:
            try:
                # --- Vehicle Specific Data ---
                # Physics
                try:
                    speed = traci.vehicle.getSpeed(vid)
                    accel = traci.vehicle.getAcceleration(vid)
                    pos = traci.vehicle.getPosition(vid)
                    lane = traci.vehicle.getLaneID(vid)
                except:
                    speed = 0.0
                    accel = 0.0
                    pos = (0.0, 0.0)
                    lane = "unknown"
                
                # Battery
                batt = self.get_battery_info(vid)
                soc = batt['soc_percent'] if batt else 0.0
                energy_consumed = batt['energy_consumed_Wh'] if batt else 0.0
                
                # Status & Station Context
                status = 'driving'
                current_station_id = 'none'
                station_context = None
                
                if vid in self.currently_charging:
                    status = 'charging'
                    current_station_id = self.currently_charging[vid]
                    station_context = all_station_features.get(current_station_id)
                elif vid in self.currently_waiting:
                    status = 'waiting'
                    current_station_id = self.currently_waiting[vid]
                    station_context = all_station_features.get(current_station_id)
                elif speed < 0.1:
                    status = 'idle'
                
                # If driving, find nearest station context (optional, but good for ML)
                # For performance, we might skip full routing here and just use Euclidean distance if needed
                # For now, if not at a station, station context is empty/zeroed
                
                if not station_context:
                    # Provide default "zero" context if not at a station
                    station_context = {
                        'power_demand_kW': 0,
                        'vehicles_charging': 0, 
                        'vehicles_waiting': 0,
                        'charging_utilization_percent': 0,
                        'queue_length': 0
                    }
                
                # --- Construct Record ---
                record = {
                    # 1. Identity & Time
                    'timestep_sec': timestep_sec,
                    'minute_of_hour': time_features['minute_of_hour'],
                    'vehicle_id': traci.vehicle.getTypeID(vid),
                    # 'vehicle_type': removed as per user request, using type as ID
                    
                    # 2. Vehicle Metrics (The "Specific" Data)
                    'speed_ms': round(speed, 2),
                    'acceleration_ms2': round(accel, 2),
                    'soc_percent': round(soc, 2),
                    'energy_consumed_Wh': round(energy_consumed, 2),
                    'lane_id': str(lane).replace('-', 'NEG_') if str(lane).startswith('-') else str(lane),
                    'status': status,
                    
                    # 3. Station Context (Where the vehicle is)
                    'current_station_id': current_station_id,
                    'station_load_kW': station_context.get('power_demand_kW', 0),
                    'station_vehicles_charging': station_context.get('vehicles_charging', 0),
                    'station_queue_length': station_context.get('queue_length', 0),
                    'station_utilization_percent': station_context.get('charging_utilization_percent', 0),
                    
                    # 4. System Context (Global State)
                    'system_total_vehicles': system_features['total_active_vehicles'],
                    'system_moving_vehicles': system_features['total_moving_vehicles'],
                    'system_charging_vehicles': system_features['total_vehicles_charging'],
                    'system_waiting_vehicles': system_features['total_vehicles_waiting'],
                    # 'system_total_load_kW': system_features['total_power_demand_kW'], # Keep alias
                    'system_avg_speed_ms': system_features['system_avg_speed_ms'],
                    'system_avg_soc_percent': system_features['system_avg_soc_percent'],
                    'system_avg_moving_speed_ms': system_features['system_avg_moving_speed_ms'],
                    'system_avg_moving_soc_percent': system_features['system_avg_moving_soc_percent'],
                    'system_avg_charging_soc_percent': system_features['system_avg_charging_soc_percent'],
                    'system_avg_charging_duration_sec': system_features['system_avg_current_charging_duration_sec'],

                    # TARGET VARIABLE - Last Column
                    'system_total_load_kW': system_features['total_power_demand_kW'] # Keep alias
                    
                }
                
                self.ml_data.append(record)
                
            except Exception:
                continue
    

    # ==================== CHARGING RECOMMENDATION SYSTEM ====================
    
    def calculate_distance(self, pos1, pos2):
        """Calculate Euclidean distance"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def get_station_position(self, station_id):
        """Get station position"""
        try:
            station_info = self.CHARGING_STATIONS[station_id]
            lane_shape = traci.lane.getShape(station_info['lane'])
            if len(lane_shape) >= 2:
                mid_idx = len(lane_shape) // 2
                return lane_shape[mid_idx]
            return lane_shape[0] if lane_shape else (0, 0)
        except:
            return (0, 0)
    
    def get_station_occupancy_details(self, station_id):
        """Get detailed occupancy"""
        station_info = self.CHARGING_STATIONS[station_id]
        charging_occupied = len(self.station_charging_slots[station_id])
        waiting_occupied = len(self.station_waiting_queue[station_id])
        
        return {
            'charging_occupied': charging_occupied,
            'charging_capacity': station_info['charging_slots'],
            'charging_available': station_info['charging_slots'] - charging_occupied,
            'waiting_available': station_info['waiting_slots'] - waiting_occupied,
            'total_available': (station_info['charging_slots'] - charging_occupied) + (station_info['waiting_slots'] - waiting_occupied),
            'occupancy_rate': (charging_occupied / station_info['charging_slots'] * 100) if station_info['charging_slots'] > 0 else 100
        }
    
    def get_priority_level(self, soc):
        """Get priority"""
        if soc < 20.0:
            return "CRITICAL"
        elif soc < 30.0:
            return "HIGH"
        elif soc < 50.0:
            return "MEDIUM"
        return "LOW"
    
    def format_edge_lane(self, value):
        """Format edge/lane to use NEG_ prefix for negative values"""
        if value and str(value).startswith('-'):
            return 'NEG_' + str(value)[1:]  # Remove '-' and add 'NEG_'
        return str(value) if value else value

    def find_nearest_and_second_nearest_stations(self, vehicle_id):
        """Find nearest and 2nd nearest stations"""
        try:
            vehicle_pos = traci.vehicle.getPosition(vehicle_id)
            station_distances = []
            
            for station_id, station_info in self.CHARGING_STATIONS.items():
                station_pos = self.get_station_position(station_id)
                distance = self.calculate_distance(vehicle_pos, station_pos)
                occupancy = self.get_station_occupancy_details(station_id)
                
                station_distances.append({
                    'station_id': station_id,
                    'station_name': f"Station {station_id}",
                    'distance_m': distance,
                    'edge': station_info['edge'],
                    'lane': station_info['lane'],
                    'power_kw': station_info['power_kW'],
                    'charging_available': occupancy['charging_available'],
                    'waiting_available': occupancy['waiting_available'],
                    'total_available': occupancy['total_available'],
                    'occupancy_rate': occupancy['occupancy_rate'],
                    'charging_occupied': occupancy['charging_occupied']
                })
            
            station_distances.sort(key=lambda x: x['distance_m'])
            nearest = station_distances[0] if len(station_distances) > 0 else None
            second_nearest = station_distances[1] if len(station_distances) > 1 else None
            
            return nearest, second_nearest
        except:
            return None, None
    
    def make_charging_recommendation(self, vehicle_id, timestep):
        """Make recommendation with nearest + 2nd nearest"""
        try:
            battery_info = self.get_battery_info(vehicle_id)
            if not battery_info:
                return
            
            soc = battery_info['soc_percent']
            if soc >= 50.0:
                return
            
            last_rec_time = self.vehicle_last_recommendation.get(vehicle_id, -999)
            if timestep - last_rec_time < 30:
                return
            
            nearest, second_nearest = self.find_nearest_and_second_nearest_stations(vehicle_id)
            if not nearest:
                return
            
            vehicle_type = traci.vehicle.getTypeID(vehicle_id)
            vehicle_edge = traci.vehicle.getRoadID(vehicle_id)
            # vehicle_lane = traci.vehicle.getLaneID(vehicle_id)
            try:
                vehicle_lane = traci.vehicle.getLaneID(vehicle_id)
                if not vehicle_lane:
                    vehicle_lane = 'parked'
            except:
                vehicle_lane = 'parked'
            
            vehicle_speed = traci.vehicle.getSpeed(vehicle_id)        
            charge_time_nearest = self.calculate_charge_time(battery_info, nearest)
            charge_time_second = self.calculate_charge_time(battery_info, second_nearest) if second_nearest else None
            
            priority = self.get_priority_level(soc)
            
            # Select best station
            if nearest['charging_available'] > 0:
                recommended = nearest['station_name']
                reason = "Nearest with charging slots"
            elif second_nearest and second_nearest['charging_available'] > 0:
                recommended = second_nearest['station_name']
                reason = "2nd nearest has slots (nearest full)"
            elif nearest['waiting_available'] > 0:
                recommended = nearest['station_name']
                reason = "Nearest with waiting slots"
            else:
                recommended = nearest['station_name']
                reason = "Nearest (all busy)"
            
            recommendation = {
                'timestep_sec': timestep,
                'vehicle_id': vehicle_type,  # Changed: vehicle_type value goes here
                # 'vehicle_type': vehicle_type,  # Removed as requested
                'current_edge': self.format_edge_lane(vehicle_edge),  # NEG_ format
                'current_lane': self.format_edge_lane(vehicle_lane),  # NEG_ format
                'current_speed_ms': round(vehicle_speed, 2),
                'current_soc_percent': round(soc, 2),
                'battery_capacity_wh': battery_info['capacity_Wh'],
                'priority': priority,
                'nearest_station_id': nearest['station_id'],
                'nearest_station_name': nearest['station_name'],
                'nearest_distance_m': round(nearest['distance_m'], 2),
                'nearest_edge': self.format_edge_lane(nearest['edge']),  # NEG_ format
                'nearest_lane': self.format_edge_lane(nearest['lane']),  # NEG_ format
                'nearest_power_kw': nearest['power_kw'],
                'nearest_charging_available': nearest['charging_available'],
                'nearest_waiting_available': nearest['waiting_available'],
                'nearest_occupancy_rate': round(nearest['occupancy_rate'], 1),
                # 'nearest_est_charge_time_min': round(charge_time_nearest / 60, 1),  # Commented out
                '2nd_nearest_station_id': second_nearest['station_id'] if second_nearest else None,
                '2nd_nearest_station_name': second_nearest['station_name'] if second_nearest else None,
                '2nd_nearest_distance_m': round(second_nearest['distance_m'], 2) if second_nearest else None,
                '2nd_nearest_edge': self.format_edge_lane(second_nearest['edge']) if second_nearest else None,  # NEG_ format
                '2nd_nearest_lane': self.format_edge_lane(second_nearest['lane']) if second_nearest else None,  # NEG_ format
                '2nd_nearest_power_kw': second_nearest['power_kw'] if second_nearest else None,
                '2nd_nearest_charging_available': second_nearest['charging_available'] if second_nearest else None,
                '2nd_nearest_waiting_available': second_nearest['waiting_available'] if second_nearest else None,
                '2nd_nearest_occupancy_rate': round(second_nearest['occupancy_rate'], 1) if second_nearest else None,
                # '2nd_nearest_est_charge_time_min': round(charge_time_second / 60, 1) if charge_time_second else None,  # Commented out
                'recommended_station': recommended,
                'recommendation_reason': reason
            }            
            self.recommendations.append(recommendation)
            self.vehicle_last_recommendation[vehicle_id] = timestep
            self.recommendation_count += 1
            
            if priority in ['CRITICAL', 'HIGH']:
                print(f"\n{'='*80}")
                print(f"⚡ RECOMMENDATION #{self.recommendation_count}")
                print(f"{'='*80}")
                print(f"Time: {timestep}s | Vehicle: {vehicle_id} | Priority: {priority} | SOC: {soc:.1f}%")
                print(f"1️⃣  {nearest['station_name']}: {nearest['distance_m']:.0f}m, {nearest['charging_available']} slots")
                if second_nearest:
                    print(f"2️⃣  {second_nearest['station_name']}: {second_nearest['distance_m']:.0f}m, {second_nearest['charging_available']} slots")
                print(f"✅ RECOMMENDED: {recommended} - {reason}")
                print(f"{'='*80}\n")
        except:
            pass
    
    # =====================================================================

    def collect_data(self, t):
        # Monitor charging and queue management FIRST
        self.monitor_charging(t)
        
        # NEW: Make charging recommendations
        try:
            for vid in traci.vehicle.getIDList():
                self.make_charging_recommendation(vid, t)
        except:
            pass
        
        # Capture detailed station snapshot
        self.capture_station_snapshot(t)
        
        # Collect ML Features (Long Format)
        self.collect_ml_features(t)
        
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
                    # 'x_position': round(pos[0], 2),
                    # 'y_position': round(pos[1], 2),
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
            # while traci.simulation.getMinExpectedNumber() > 0 and t < max_time:
            while traci.simulation.getMinExpectedNumber() > 0 and t <= max_time:
                traci.simulationStep()
                t = traci.simulation.getTime()
                
                if int(t) == t:
                    self.collect_data(t)
                
                if int(t) % 30 == 0 and t > 0:
                    active = len(traci.vehicle.getIDList())
                    chrg = len(self.currently_charging)
                    wait = sum(len(q) for q in self.station_waiting_queue.values())
                    
                    # Get latest system load from ml_data if available
                    load = 0
                    if self.ml_data:
                        # power_demand is per station in ml_data, system load is redundant col
                        load = self.ml_data[-1]['system_total_load_kW']
                    
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
        
        # ==================================================================================
        # SINGLE CSV OUTPUT ONLY (ML-READY LONG FORMAT)
        # ==================================================================================
        
        if self.ml_data:
            df = pd.DataFrame(self.ml_data)
            
            # Sort for clarity
            df = df.sort_values(['timestep_sec', 'vehicle_id'])
            
            filename = f'EV_Charging_Load_Demand_Dataset_{ts}.csv'
            f = os.path.join(self.output_folder, filename)
            df.to_csv(f, index=False)
            print(f"✓ DATASET EXPORTED: {f}")
            print(f"  Records: {len(df):,}")
            print(f"  Format: Vehicle-Centric (1 row per vehicle per timestep)")
            
            if len(df) > 0:
                peak = df['system_total_load_kW'].max()
                avg = df['system_total_load_kW'].mean()
                
                # Calculate energy (Average power * duration / 3600)
                # Note: Data is per vehicle, so we must be careful not to sum system load multiple times
                # We need to take unique system loads per timestep
                system_df = df[['timestep_sec', 'system_total_load_kW']].drop_duplicates()
                energy = system_df['system_total_load_kW'].sum() / 3600
                
                maxv = df['system_charging_vehicles'].max()
                
                print(f"\n💡 SYSTEM LOAD SUMMARY:")
                print(f"  Peak Power: {peak:.2f} kW")
                print(f"  Avg Power: {avg:.2f} kW")
                print(f"  Total Energy: {energy:.3f} kWh")
                print(f"  Max Simultaneous Charging: {int(maxv)} vehicles")
        
        else:
            print("⚠ No load data collected to export.")


        # Export recommendations
        if self.recommendations:
            df_rec = pd.DataFrame(self.recommendations)
            filename = f'charging_recommendations_{ts}.csv'
            filepath = os.path.join(self.output_folder, filename)
            df_rec.to_csv(filepath, index=False)
            print(f"\n✅ RECOMMENDATIONS: {filepath}")
            print(f"   Total: {len(df_rec):,} | Priority: {dict(df_rec['priority'].value_counts())}")
        
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