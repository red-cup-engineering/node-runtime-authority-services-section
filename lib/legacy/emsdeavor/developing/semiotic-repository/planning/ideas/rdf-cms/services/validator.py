import os
import time
import psycopg2
from rdflib import Graph
from pyshacl import validate
import requests

STORAGE_URL = os.environ.get("RDF_STORAGE_URL", "http://localhost:3000")
CHECK_INTERVAL = 10

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def get_last_processed_event_id():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS validator_state (
            id INTEGER PRIMARY KEY DEFAULT 1,
            last_event_id INTEGER DEFAULT 0,
            CHECK (id = 1)
        )
    """)
    cur.execute("INSERT INTO validator_state (id, last_event_id) VALUES (1, 0) ON CONFLICT (id) DO NOTHING")
    cur.execute("SELECT last_event_id FROM validator_state WHERE id = 1")
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result[0] if result else 0

def update_last_processed_event_id(event_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE validator_state SET last_event_id = %s WHERE id = 1", (event_id,))
    conn.commit()
    cur.close()
    conn.close()

def check_for_events():
    conn = get_db()
    cur = conn.cursor()
    last_id = get_last_processed_event_id()
    
    cur.execute("""
        SELECT id, event_type, graph_name, data 
        FROM events 
        WHERE id > %s AND event_type IN ('triple.added', 'validate.requested')
        ORDER BY id ASC
    """, (last_id,))
    
    events = cur.fetchall()
    cur.close()
    conn.close()
    
    return events

def run_validation():
    try:
        response = requests.get(f"{STORAGE_URL}/graphs/default")
        if response.status_code != 200:
            print(f"Failed to fetch default graph: {response.status_code}")
            return
        
        default_data = response.json()
        data_graph = Graph()
        shapes_graph = Graph()
        
        for triple in default_data.get("triples", []):
            from rdflib import URIRef, Literal, Namespace
            SH = Namespace("http://www.w3.org/ns/shacl#")
            
            s = URIRef(triple["subject"])
            p = URIRef(triple["predicate"])
            o = URIRef(triple["object"]) if triple["object_type"] == "uri" else Literal(triple["object"])
            
            if str(p).startswith(str(SH)) or "Shape" in str(s):
                shapes_graph.add((s, p, o))
            else:
                data_graph.add((s, p, o))
        
        print(f"Data graph: {len(data_graph)} triples, Shapes graph: {len(shapes_graph)} triples")
        
        if len(shapes_graph) == 0:
            print("No SHACL shapes found, skipping validation")
            return
        
        conforms, results_graph, results_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference='rdfs',
            abort_on_first=False,
        )
        
        print(f"Validation {'passed' if conforms else 'failed'}")
        print(f"Validation report: {len(results_graph)} triples")
        
        validation_triples = []
        for s, p, o in results_graph:
            validation_triples.append({
                "subject": str(s),
                "predicate": str(p),
                "object": str(o),
                "object_type": "uri" if str(o).startswith("http") else "literal"
            })
        
        update_response = requests.put(
            f"{STORAGE_URL}/graphs/validation",
            json=validation_triples
        )
        
        if update_response.status_code == 200:
            print(f"Updated validation graph with {len(validation_triples)} triples")
        else:
            print(f"Failed to update validation graph: {update_response.status_code}")
            
    except Exception as e:
        print(f"Validation error: {e}")

def main():
    print("Validator service starting...")
    
    while True:
        try:
            events = check_for_events()
            
            if events:
                print(f"Found {len(events)} new events, running validation...")
                run_validation()
                
                last_event_id = events[-1][0]
                update_last_processed_event_id(last_event_id)
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
