import xml.etree.ElementTree as ET
import os
import time
import sys

def read_fcd_data(file_path):
    """Read Floating Car Data (FCD) - contains position, speed, angle data"""
    if not os.path.exists(file_path):
        print(f"FCD file not found: {file_path}")
        return
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print("\n" + "="*80)
        print("VEHICLE REAL-TIME DATA (Speed, Position, Angle)")
        print("="*80)
        
        current_time = None
        for timestep in root.findall('timestep'):
            step_time = float(timestep.get('time'))
            
            # Print time header
            if current_time != step_time:
                print(f"\n⏰ Time: {step_time:.1f}s")
                print("-" * 60)
                current_time = step_time
            
            # Print vehicle data for this timestep
            for vehicle in timestep.findall('vehicle'):
                veh_id = vehicle.get('id')
                veh_type = vehicle.get('type', 'unknown')  # Fixed: use vehicle instead of tripinfo
                x = float(vehicle.get('x'))
                y = float(vehicle.get('y'))
                speed = float(vehicle.get('speed'))
                angle = float(vehicle.get('angle'))
                
                print(f"🚗 {veh_id:8} [{veh_type:8}] Speed: {speed:5.1f}m/s  Pos: ({x:6.1f}, {y:6.1f})  Angle: {angle:6.1f}°")
                
    except Exception as e:
        print(f"Error reading FCD data: {e}")

def read_tripinfo_data(file_path):
    """Read Trip Info - contains trip statistics, distance, duration"""
    if not os.path.exists(file_path):
        print(f"Trip info file not found: {file_path}")
        return
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print("\n" + "="*80)
        print("TRIP SUMMARY DATA (Distance, Duration, Speed)")
        print("="*80)
        
        for tripinfo in root.findall('tripinfo'):
            veh_id = tripinfo.get('id')
            veh_type = tripinfo.get('vType')
            depart = float(tripinfo.get('depart'))
            arrival = float(tripinfo.get('arrival'))
            duration = float(tripinfo.get('duration'))
            route_length = float(tripinfo.get('routeLength'))
            max_speed = float(tripinfo.get('maxSpeed'))
            
            avg_speed = route_length / duration if duration > 0 else 0
            
            print(f"🚗 {veh_id:8} [{veh_type:8}]")
            print(f"   📍 Distance: {route_length:8.1f}m")
            print(f"   ⏱️  Duration: {duration:8.1f}s")
            print(f"   🏃 Avg Speed: {avg_speed:6.1f}m/s")
            print(f"   🚀 Max Speed: {max_speed:6.1f}m/s")
            print(f"   🕐 Depart: {depart:6.1f}s → Arrive: {arrival:6.1f}s")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error reading trip info: {e}")

def read_battery_data(file_path):
    """Read Battery Data - contains battery levels, charging info"""
    if not os.path.exists(file_path):
        print(f"Battery file not found: {file_path}")
        return
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print("\n" + "="*80)
        print("BATTERY DATA (Charge Levels, Energy Consumption)")
        print("="*80)
        
        for timestep in root.findall('timestep'):
            step_time = float(timestep.get('time'))
            
            vehicles_with_battery = timestep.findall('vehicle')
            if vehicles_with_battery:
                print(f"\n🔋 Time: {step_time:.1f}s")
                print("-" * 60)
                
                for vehicle in vehicles_with_battery:
                    veh_id = vehicle.get('id')
                    energy_consumed = float(vehicle.get('energyConsumed', 0))
                    battery_capacity = float(vehicle.get('actualBatteryCapacity', 0))
                    max_capacity = float(vehicle.get('maximumBatteryCapacity', 100000))

                    battery_percent = (battery_capacity / max_capacity) * 100 if max_capacity > 0 else 0
                    
                    print(f"⚡ {veh_id:8} Battery: {battery_percent:5.1f}% ({battery_capacity:8.0f}Wh) Energy Used: {energy_consumed:8.1f}Wh")
                    
    except ET.ParseError as e:
        print(f"⚠️ Skipping {file_path} (incomplete XML): {e}")
    except Exception as e:
        print(f"Error reading battery data: {e}")

def read_charging_stations_data(file_path):
    """Read Charging Station Data - contains station usage, power output"""
    if not os.path.exists(file_path):
        print(f"Charging stations file not found: {file_path}")
        return
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print("\n" + "="*80)
        print("CHARGING STATION DATA (Usage, Power Output)")
        print("="*80)
        
        for timestep in root.findall('timestep'):
            step_time = float(timestep.get('time'))
            
            stations_active = timestep.findall('chargingStation')
            if stations_active:
                print(f"\n🔌 Time: {step_time:.1f}s")
                print("-" * 60)
                
                for station in stations_active:
                    station_id = station.get('id')
                    power_output = float(station.get('totalEnergyCharged', 0))
                    occupancy = int(station.get('chargingVehicles', 0))

                    print(f"🏪 {station_id:12} Power: {power_output:8.1f}W  Vehicles: {occupancy}")
                    
    except Exception as e:
        print(f"Error reading charging station data: {e}")

def monitor_simulation_live():
    """Monitor simulation files in real-time"""
    print("🚀 SUMO Vehicle Data Monitor Started")
    print("📁 Monitoring files in current directory...")
    print("📊 Press Ctrl+C to stop monitoring\n")
    
    files_to_monitor = {
        'fcd.xml': 'last_fcd_size',
        'tripinfo.xml': 'last_trip_size',
        'chargingstations.xml': 'last_charging_size'
    }
    
    # Initialize file sizes
    file_sizes = {}
    for filename in files_to_monitor:
        file_sizes[files_to_monitor[filename]] = 0
    
    try:
        while True:
            # Check each file for changes
            for filename, size_key in files_to_monitor.items():
                if os.path.exists(filename):
                    current_size = os.path.getsize(filename)
                    if current_size > file_sizes[size_key]:
                        file_sizes[size_key] = current_size
                        
                        print(f"\n📄 Updated: {filename}")
                        
                        if filename == 'fcd.xml':
                            read_fcd_data(filename)
                        elif filename == 'tripinfo.xml':
                            read_tripinfo_data(filename)
                        elif filename == 'chargingstations.xml':
                            read_charging_stations_data(filename)
            
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")

def read_all_files():
    """Read all available output files at once"""
    print("📊 SUMO SIMULATION DATA ANALYSIS")
    print("=" * 80)
    
    # Read all data files
    read_fcd_data('fcd.xml')
    read_tripinfo_data('tripinfo.xml')
    read_charging_stations_data('chargingstations.xml')
    
    print("\n" + "="*80)
    print("✅ DATA ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--live":
            monitor_simulation_live()
        elif sys.argv[1] == "--help":
            print("SUMO Vehicle Data Reader")
            print("Usage:")
            print("  python vehicle_monitor.py          # Read all files once")
            print("  python vehicle_monitor.py --live   # Monitor files in real-time")
            print("  python vehicle_monitor.py --help   # Show this help")
        else:
            print("Unknown option. Use --help for usage information.")
    else:
        read_all_files()