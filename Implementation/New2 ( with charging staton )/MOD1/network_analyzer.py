import xml.etree.ElementTree as ET
import math

def analyze_network(net_file):
    """Analyze SUMO network file to extract node connections and distances"""
    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        
        print("="*80)
        print("SUMO NETWORK ANALYSIS")
        print("="*80)
        
        # Extract nodes
        nodes = {}
        junctions = root.findall('junction')
        for junction in junctions:
            node_id = junction.get('id')
            x = float(junction.get('x', 0))
            y = float(junction.get('y', 0))
            nodes[node_id] = {'x': x, 'y': y}
        
        print(f"\nFound {len(nodes)} nodes:")
        for node_id, coords in nodes.items():
            print(f"  {node_id}: ({coords['x']:.2f}, {coords['y']:.2f})")
        
        # Extract edges and calculate distances
        edges = root.findall('edge')
        connections = []
        
        print("\nEDGE CONNECTIONS AND DISTANCES:")
        print("-" * 60)
        print(f"{'Edge ID':<8} {'From':<6} {'To':<6} {'Length (m)':<12} {'Calculated':<12}")
        print("-" * 60)
        
        for edge in edges:
            edge_id = edge.get('id')
            from_node = edge.get('from')
            to_node = edge.get('to')
            
            # Skip internal edges
            if edge_id and edge_id.startswith(':'):
                continue
                
            if from_node and to_node and from_node in nodes and to_node in nodes:
                # Get length from lane definition
                lane = edge.find('lane')
                declared_length = 0
                if lane is not None:
                    declared_length = float(lane.get('length', 0))
                
                # Calculate geometric distance
                x1, y1 = nodes[from_node]['x'], nodes[from_node]['y']
                x2, y2 = nodes[to_node]['x'], nodes[to_node]['y']
                calculated_length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                
                connections.append({
                    'edge': edge_id,
                    'from': from_node,
                    'to': to_node,
                    'declared': declared_length,
                    'calculated': calculated_length
                })
                
                print(f"{edge_id:<8} {from_node:<6} {to_node:<6} {declared_length:<12.1f} {calculated_length:<12.1f}")
        
        # Summary statistics
        print("\n" + "="*80)
        print("DISTANCE VERIFICATION SUMMARY")
        print("="*80)
        
        total_declared = sum(conn['declared'] for conn in connections)
        total_calculated = sum(conn['calculated'] for conn in connections)
        
        print(f"Total network length (declared): {total_declared:.1f}m")
        print(f"Total network length (calculated): {total_calculated:.1f}m")
        print(f"Difference: {abs(total_declared - total_calculated):.1f}m")
        
        # Check for large discrepancies
        print("\nDISCREPANCY ANALYSIS:")
        print("-" * 40)
        for conn in connections:
            diff = abs(conn['declared'] - conn['calculated'])
            if diff > 10:  # More than 10m difference
                print(f"⚠️  {conn['edge']}: {diff:.1f}m difference")
        
        # Route analysis
        print("\nROUTE DISTANCE ANALYSIS:")
        print("-" * 40)
        
        # Main route: Node1 → Node2 → Node3 → Node4 → Node13
        main_route = ['E0', 'E1', 'E2', 'E3']
        main_distance = sum(conn['declared'] for conn in connections if conn['edge'] in main_route)
        print(f"Main route (E0→E1→E2→E3): {main_distance:.1f}m")
        
        # Alternative route: Node1 → Node5 → Node6 → Node2 → Node3 → Node4 → Node13
        alt_route = ['E4', 'E11', 'E10', 'E1', 'E2', 'E3']
        alt_distance = sum(conn['declared'] for conn in connections if conn['edge'] in alt_route)
        print(f"Alternative route (E4→E11→E10→E1→E2→E3): {alt_distance:.1f}m")
        
        return connections
        
    except ET.ParseError as e:
        print(f"Error parsing network file: {e}")
        return None
    except Exception as e:
        print(f"Error analyzing network: {e}")
        return None

def compare_with_diagram(connections):
    """Compare network distances with your hand-drawn diagram"""
    print("\n" + "="*80)
    print("COMPARISON WITH YOUR DIAGRAM")
    print("="*80)
    
    # Expected distances from your diagram
    expected = {
        'E0': 860,   # N1→N2
        'E1': 900,   # N2→N3
        'E2': 940,   # N3→N4
        'E3': 1300,  # N4→N13
        'E4': 410,   # N1→N5
        'E11': 260,  # N5→N6
        'E10': 120,  # N6→N2
        'E17': 260,  # N5→N7
        'E18': 700,  # N7→N8
        'E14': 900,  # N8→N12
        'E15': 750,  # N12→N13
        'E12': 650,  # N10→N11
        'E16': 750,  # N11→N12
        'E7': 130,   # N8→N9
        'E8': 480,   # N9→N10
    }
    
    print(f"{'Edge':<6} {'Expected':<10} {'Actual':<10} {'Difference':<12} {'Status'}")
    print("-" * 60)
    
    for conn in connections:
        edge_id = conn['edge']
        actual = conn['declared']
        
        if edge_id in expected:
            exp = expected[edge_id]
            diff = actual - exp
            status = "✓ Match" if abs(diff) < 10 else "⚠️ Mismatch"
            print(f"{edge_id:<6} {exp:<10.0f} {actual:<10.1f} {diff:+12.1f} {status}")

def create_distance_update_guide(connections):
    """Create a guide for updating distances to match your diagram"""
    print("\n" + "="*80)
    print("DISTANCE UPDATE GUIDE")
    print("="*80)
    
    print("To update your network to match the exact distances:")
    print("1. Use SUMO netedit to modify edge lengths")
    print("2. Or manually edit the XML (not recommended)")
    print("3. Or use netconvert with custom edge lengths")
    
    print("\nNETEDIT Steps:")
    print("1. Open: netedit Test1.net.xml")
    print("2. Select edge inspection mode")
    print("3. Click on each edge and modify 'length' parameter")
    print("4. Save the network")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        net_file = sys.argv[1]
    else:
        net_file = "Test1.net.xml"
    
    print(f"Analyzing network file: {net_file}")
    connections = analyze_network(net_file)
    
    if connections:
        compare_with_diagram(connections)
        create_distance_update_guide(connections)
    else:
        print("Failed to analyze network file.")