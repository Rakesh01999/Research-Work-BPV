"""
SUMO TraCI Script for Conditional EV Charging
----------------------------------------------
Implements battery-based conditional charging for EVs:
- Monitors battery SOC (State of Charge) for all vehicles
- When SOC < 30%, vehicle diverts to nearest charging station
- Charges until SOC >= 60%, then resumes original route
- Handles multiple vehicle types and routes dynamically

Usage: python conditional_charging.py
"""

import os
import sys
import traci
import math

# Check if SUMO_HOME is set
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")


class ChargingStation:
    """Represents a charging station in the network"""
    def __init__(self, station_id, lane, start_pos, end_pos):
        self.id = station_id
        self.lane = lane
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.edge = lane.split('_')[0]  # Extract edge from lane
        

class VehicleChargingState:
    """Tracks charging state for each vehicle"""
    def __init__(self, vehicle_id, original_route):
        self.vehicle_id = vehicle_id
        self.original_route = original_route
        self.is_charging = False
        self.needs_charging = False
        self.target_station = None
        self.charging_route = []
        self.route_after_charging = []
        self.charging_start_time = None


# Define charging stations based on your configuration
CHARGING_STATIONS = [
    ChargingStation("pa_2", "E0_0", 745.11, 765.11),
    ChargingStation("pa_3", "E1_0", 727.99, 747.99),
    ChargingStation("pa_6", "E5_0", 241.24, 251.24),
    ChargingStation("pa_7", "E6_0", 420.48, 440.48),
    ChargingStation("pa_8", "E7_0", 830.91, 850.91),
]

# Configuration parameters
SOC_LOW_THRESHOLD = 30.0  # Battery % to trigger charging
SOC_TARGET = 60.0  # Battery % to stop charging  
CHARGING_CHECK_INTERVAL = 10  # Steps between battery checks
MAX_CHARGING_TIME = 300  # Maximum charging time in simulation steps (30 seconds)

# Global state tracking
vehicle_states = {}
simulation_step = 0


def get_battery_soc(vehicle_id):
    """Get battery State of Charge (SOC) percentage for a vehicle"""
    try:
        actual = traci.vehicle.getParameter(vehicle_id, "device.battery.actualBatteryCapacity")
        maximum = traci.vehicle.getParameter(vehicle_id, "device.battery.maximumBatteryCapacity")
        
        if actual and maximum:
            actual_val = float(actual)
            maximum_val = float(maximum)
            if maximum_val > 0:
                soc = (actual_val / maximum_val) * 100
                return soc
    except Exception as e:
        print(f"Error getting SOC for {vehicle_id}: {e}")
    return 100.0  # Default to full if error


def find_nearest_charging_station(vehicle_id):
    """Find the nearest charging station based on current route"""
    try:
        current_edge = traci.vehicle.getRoadID(vehicle_id)
        route = traci.vehicle.getRoute(vehicle_id)
        
        # Find stations on current route
        stations_on_route = []
        for station in CHARGING_STATIONS:
            if station.edge in route:
                # Get index in route
                try:
                    idx = route.index(station.edge)
                    current_idx = route.index(current_edge) if current_edge in route else 0
                    
                    # Only consider stations ahead on route
                    if idx >= current_idx:
                        stations_on_route.append((station, idx))
                except ValueError:
                    continue
        
        if stations_on_route:
            # Return nearest station (lowest index)
            stations_on_route.sort(key=lambda x: x[1])
            return stations_on_route[0][0]
        
        # If no station on route, return first available
        return CHARGING_STATIONS[0] if CHARGING_STATIONS else None
        
    except Exception as e:
        print(f"Error finding station for {vehicle_id}: {e}")
        return None


def create_route_to_station(vehicle_id, station):
    """Create a route from current position to charging station"""
    try:
        current_edge = traci.vehicle.getRoadID(vehicle_id)
        current_route = traci.vehicle.getRoute(vehicle_id)
        
        # Skip if on internal edge (inside junction)
        if current_edge.startswith(':'):
            return None, None
        
        # Find station edge in route
        if station.edge in current_route:
            try:
                current_idx = current_route.index(current_edge)
                station_idx = current_route.index(station.edge)
                
                # Route to station (including station edge)
                route_to_station = list(current_route[current_idx:station_idx + 1])
                
                # Route after station (from station edge to end)
                route_after = list(current_route[station_idx:])
                
                return route_to_station, route_after
            except ValueError:
                # Current edge not in route, use full route
                return list(current_route), list(current_route)
        else:
            # Station not on current route, keep original route
            return list(current_route), list(current_route)
            
    except Exception as e:
        print(f"Error creating route for {vehicle_id}: {e}")
        return None, None


def handle_charging_logic(vehicle_id):
    """Main logic for handling vehicle charging behavior"""
    global vehicle_states
    
    # Check if vehicle has battery device
    try:
        has_battery = traci.vehicle.getParameter(vehicle_id, "has.battery.device")
        if has_battery != "true":
            return
    except:
        return
    
    # Initialize vehicle state if new
    if vehicle_id not in vehicle_states:
        original_route = traci.vehicle.getRoute(vehicle_id)
        vehicle_states[vehicle_id] = VehicleChargingState(vehicle_id, original_route)
    
    state = vehicle_states[vehicle_id]
    soc = get_battery_soc(vehicle_id)
    
    # Check if vehicle is currently stopped at a parking area
    is_stopped = traci.vehicle.isStopped(vehicle_id)
    
    # State machine for charging behavior
    if state.is_charging:
        # Vehicle is charging
        charging_duration = simulation_step - state.charging_start_time
        
        # Force resume if charging too long OR target reached
        if soc >= SOC_TARGET or charging_duration >= MAX_CHARGING_TIME:
            reason = "complete" if soc >= SOC_TARGET else "timeout"
            print(f"[{simulation_step}] {vehicle_id}: Charging {reason}! SOC: {soc:.1f}%")
            
            # CRITICAL: Force stop removal first
            try:
                traci.vehicle.resume(vehicle_id)
                print(f"  -> Vehicle resumed from parking")
            except Exception as e:
                print(f"  -> Resume error: {e}")
            
            # Resume route after charging
            if state.route_after_charging and len(state.route_after_charging) > 0:
                try:
                    traci.vehicle.setRoute(vehicle_id, state.route_after_charging)
                    print(f"  -> Route restored with {len(state.route_after_charging)} edges")
                except Exception as e:
                    print(f"  -> Route restoration error: {e}")
            
            state.is_charging = False
            state.needs_charging = False
            state.target_station = None
            
        else:
            # Still charging
            if simulation_step % 100 == 0:  # Log every 10 seconds
                print(f"[{simulation_step}] {vehicle_id}: Charging... SOC: {soc:.1f}%")
    
    elif state.needs_charging:
        # Vehicle is en route to charging station
        current_edge = traci.vehicle.getRoadID(vehicle_id)
        
        if state.target_station and current_edge == state.target_station.edge:
            # Arrived at charging station lane
            position = traci.vehicle.getLanePosition(vehicle_id)
            
            # Check if within station bounds
            if state.target_station.start_pos <= position <= state.target_station.end_pos:
                print(f"[{simulation_step}] {vehicle_id}: Arrived at station {state.target_station.id}")
                
                # Stop for charging
                try:
                    # Set parking stop with limited duration
                    traci.vehicle.setParkingAreaStop(vehicle_id, state.target_station.id, 
                                                     duration=300)  # 30 seconds max
                    state.is_charging = True
                    state.charging_start_time = simulation_step
                    print(f"  -> Started charging at {state.target_station.id}")
                except Exception as e:
                    print(f"  -> Error setting parking stop: {e}")
    
    else:
        # Normal operation - check if charging needed
        if soc < SOC_LOW_THRESHOLD and not state.needs_charging:
            print(f"[{simulation_step}] {vehicle_id}: Low battery! SOC: {soc:.1f}%")
            
            # Find nearest charging station
            station = find_nearest_charging_station(vehicle_id)
            
            if station:
                print(f"  -> Diverting to station: {station.id} on {station.edge}")
                
                # Create route to station
                route_to, route_after = create_route_to_station(vehicle_id, station)
                
                if route_to:
                    state.needs_charging = True
                    state.target_station = station
                    state.charging_route = route_to
                    state.route_after_charging = route_after
                    
                    # Update vehicle route to go to station
                    try:
                        traci.vehicle.setRoute(vehicle_id, route_to)
                        print(f"  -> Route updated with {len(route_to)} edges")
                    except Exception as e:
                        print(f"  -> Error updating route: {e}")


def run_simulation():
    """Main simulation loop"""
    global simulation_step
    
    # Start SUMO
    sumo_binary = "sumo-gui"  # Use "sumo" for non-GUI
    sumo_config = "Test1.sumocfg"
    
    traci.start([sumo_binary, "-c", sumo_config, 
                 "--step-length", "0.1",
                 "--device.battery.explicit", "true"])
    
    print("\n" + "="*60)
    print("CONDITIONAL EV CHARGING SIMULATION")
    print("="*60)
    print(f"Low SOC Threshold: {SOC_LOW_THRESHOLD}%")
    print(f"Target SOC: {SOC_TARGET}%")
    print(f"Charging Stations: {len(CHARGING_STATIONS)}")
    print("="*60 + "\n")
    
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            simulation_step += 1
            
            # Check charging needs every N steps
            if simulation_step % CHARGING_CHECK_INTERVAL == 0:
                # Get all vehicles in simulation
                vehicle_ids = traci.vehicle.getIDList()
                
                # Process each vehicle
                for vehicle_id in vehicle_ids:
                    handle_charging_logic(vehicle_id)
            
            # Log summary every 100 steps (10 seconds)
            if simulation_step % 100 == 0:
                charging_count = sum(1 for s in vehicle_states.values() if s.is_charging)
                enroute_count = sum(1 for s in vehicle_states.values() if s.needs_charging and not s.is_charging)
                
                if charging_count > 0 or enroute_count > 0:
                    print(f"\n[{simulation_step}] Status: {charging_count} charging, {enroute_count} en route to stations")
    
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    
    finally:
        traci.close()
        
        # Print final statistics
        print("\n" + "="*60)
        print("SIMULATION SUMMARY")
        print("="*60)
        print(f"Total vehicles tracked: {len(vehicle_states)}")
        
        charged_vehicles = [v for v in vehicle_states.values() if v.charging_start_time is not None]
        print(f"Vehicles that charged: {len(charged_vehicles)}")
        
        if charged_vehicles:
            print("\nCharging Events:")
            for v in charged_vehicles:
                print(f"  - {v.vehicle_id}: Started at step {v.charging_start_time}")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    run_simulation()