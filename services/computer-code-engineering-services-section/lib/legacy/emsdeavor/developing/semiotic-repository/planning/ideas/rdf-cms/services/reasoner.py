import os
import time
import psycopg2
from rdflib import Graph
from owlrl import DeductiveClosure, OWLRL_Semantics
import requests

STORAGE_URL = os.environ.get("RDF_STORAGE_URL", "http://localhost:3000")
CHECK_INTERVAL = 10

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def get_last_processed_event_id():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reasoner_state (
            id INTEGER PRIMARY KEY DEFAULT 1,
            last_event_id INTEGER DEFAULT 0,
            CHECK (id = 1)
        )
    """)
    cur.execute("INSERT INTO reasoner_state (id, last_event_id) VALUES (1, 0) ON CONFLICT (id) DO NOTHING")
    cur.execute("SELECT last_event_id FROM reasoner_state WHERE id = 1")
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return result[0] if result else 0

def update_last_processed_event_id(event_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE reasoner_state SET last_event_id = %s WHERE id = 1", (event_id,))
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
        WHERE id > %s AND event_type IN ('triple.added', 'reason.requested')
        ORDER BY id ASC
    """, (last_id,))
    
    events = cur.fetchall()
    cur.close()
    conn.close()
    
    return events

def run_reasoning():
    try:
        response = requests.get(f"{STORAGE_URL}/graphs/default")
        if response.status_code != 200:
            print(f"Failed to fetch default graph: {response.status_code}")
            return
        
        default_data = response.json()
        graph = Graph()
        
        for triple in default_data.get("triples", []):
            from rdflib import URIRef, Literal
            s = URIRef(triple["subject"])
            p = URIRef(triple["predicate"])
            o = URIRef(triple["object"]) if triple["object_type"] == "uri" else Literal(triple["object"])
            graph.add((s, p, o))
        
        print(f"Loaded {len(graph)} triples from default graph")
        
        DeductiveClosure(OWLRL_Semantics).expand(graph)
        
        print(f"After reasoning: {len(graph)} triples")
        
        inference_triples = []
        for s, p, o in graph:
            inference_triples.append({
                "subject": str(s),
                "predicate": str(p),
                "object": str(o),
                "object_type": "uri" if str(o).startswith("http") else "literal"
            })
        
        update_response = requests.put(
            f"{STORAGE_URL}/graphs/inference",
            json=inference_triples
        )
        
        if update_response.status_code == 200:
            print(f"Updated inference graph with {len(inference_triples)} triples")
        else:
            print(f"Failed to update inference graph: {update_response.status_code}")
            
    except Exception as e:
        print(f"Reasoning error: {e}")

def main():
    print("Reasoner service starting...")
    
    while True:
        try:
            events = check_for_events()
            
            if events:
                print(f"Found {len(events)} new events, running reasoning...")
                run_reasoning()
                
                last_event_id = events[-1][0]
                update_last_processed_event_id(last_event_id)
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
