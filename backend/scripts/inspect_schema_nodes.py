
from src.web.services import get_neo4j_service

def inspect():
    neo4j = get_neo4j_service()
    
    print("--- Uppercase Class Nodes ---")
    query_upper = "MATCH (n:Class) WHERE n.name = toUpper(n.name) RETURN n.name as Name LIMIT 5"
    results = neo4j.execute_query(query_upper)
    print(f"Found {len(results)} uppercase classes")
    for r in results:
        print(r)

if __name__ == "__main__":
    inspect()
