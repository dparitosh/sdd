"""
Query ExternalUnit and ExternalOwlClass nodes for AP243 integration
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.src.graph.connection import Neo4jConnection
from backend.src.utils.config import Config


def main():
    config = Config()
    conn = Neo4jConnection(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password
    )
    conn.connect()
    
    print("\n" + "="*70)
    print("AP243 REFERENCE DATA DISCOVERY")
    print("="*70)
    
    # 1. Query ExternalUnit nodes
    print("\n### 1. ExternalUnit Nodes (Measurement Units)")
    print("-" * 70)
    
    unit_query = """
    MATCH (u:ExternalUnit)
    WHERE u.ap_level = 'AP243'
    RETURN u.name AS name, u.symbol AS symbol, u.quantity AS quantity
    ORDER BY u.quantity, u.name
    LIMIT 30
    """
    
    units = conn.execute_query(unit_query)
    print(f"Total ExternalUnit nodes found: {len(units)}\n")
    
    # Group by quantity type
    by_quantity = {}
    for unit in units:
        qty = unit.get("quantity", "Unknown")
        if qty not in by_quantity:
            by_quantity[qty] = []
        by_quantity[qty].append(unit)
    
    for quantity, unit_list in sorted(by_quantity.items()):
        print(f"\n{quantity}:")
        for u in unit_list[:5]:  # Show first 5 per quantity
            print(f"  - {u['name']} ({u['symbol']})")
    
    # 2. Query ExternalOwlClass nodes (Ontologies)
    print("\n\n### 2. ExternalOwlClass Nodes (Domain Ontologies)")
    print("-" * 70)
    
    owl_query = """
    MATCH (o:ExternalOwlClass)
    WHERE o.ap_level = 'AP243'
    RETURN o.name AS name, o.domain AS domain, o.definition AS definition
    ORDER BY o.domain, o.name
    LIMIT 30
    """
    
    ontologies = conn.execute_query(owl_query)
    print(f"Total ExternalOwlClass nodes found: {len(ontologies)}\n")
    
    # Group by domain
    by_domain = {}
    for owl in ontologies:
        domain = owl.get("domain", "Unknown")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(owl)
    
    for domain, owl_list in sorted(by_domain.items()):
        print(f"\n{domain}:")
        for o in owl_list[:5]:  # Show first 5 per domain
            name = o.get("name", "N/A")
            definition = o.get("definition", "")
            if definition:
                definition = definition[:60] + "..." if len(definition) > 60 else definition
                print(f"  - {name}: {definition}")
            else:
                print(f"  - {name}")
    
    # 3. Query relevant units for simulation (power, torque, current, etc.)
    print("\n\n### 3. Simulation-Relevant Units")
    print("-" * 70)
    
    sim_units_query = """
    MATCH (u:ExternalUnit)
    WHERE u.ap_level = 'AP243' 
      AND (u.quantity IN ['Power', 'Torque', 'Current', 'Voltage', 'Temperature', 'Speed', 'Frequency']
           OR u.name CONTAINS 'watt'
           OR u.name CONTAINS 'newton'
           OR u.name CONTAINS 'ampere'
           OR u.name CONTAINS 'volt'
           OR u.name CONTAINS 'celsius'
           OR u.name CONTAINS 'hertz')
    RETURN u.name AS name, u.symbol AS symbol, u.quantity AS quantity
    ORDER BY u.quantity, u.name
    """
    
    sim_units = conn.query(sim_units_query)
    print(f"Simulation-relevant units found: {len(sim_units)}\n")
    
    for u in sim_units:
        print(f"  {u['quantity']:15} | {u['symbol']:10} | {u['name']}")
    
    # 4. Sample artifact-to-unit mapping strategy
    print("\n\n### 4. Artifact-to-Unit Mapping Strategy")
    print("-" * 70)
    print("""
Proposed mappings for SDD artifacts:
  
  Artifact A1 (Electromagnetic Analysis) → Power (W), Torque (N·m)
  Artifact B1 (Motor Efficiency Report)  → dimensionless (%) 
  Artifact C1 (Thermal Analysis)         → Temperature (°C)
  Artifact D1 (NVH Results)              → Frequency (Hz)
  Artifact E1 (Demagnetization Study)    → Temperature (°C), Magnetic Field (T)
  Artifact F1 (Endurance Certification)  → Time (hours)
  Artifact G1 (Manufacturing Files)      → dimensionless
  Artifact H1 (Test Data CSV)            → Multiple (Power, Current, Voltage, Speed)
    """)
    
    conn.close()
    print("\n" + "="*70)
    print("QUERY COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
