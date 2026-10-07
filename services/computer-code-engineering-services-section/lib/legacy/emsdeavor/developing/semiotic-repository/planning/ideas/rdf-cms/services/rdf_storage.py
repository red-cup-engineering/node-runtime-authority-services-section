import os
import psycopg2
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from typing import Optional
import json

app = FastAPI(title="RDF Storage Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EX = Namespace("http://example.org/")
SH = Namespace("http://www.w3.org/ns/shacl#")

default_graph = Graph()
inference_graph = Graph()
validation_graph = Graph()

default_graph.bind("ex", EX)
default_graph.bind("sh", SH)
default_graph.bind("owl", OWL)

def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            event_type VARCHAR(100),
            graph_name VARCHAR(100),
            data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rdf_triples (
            id SERIAL PRIMARY KEY,
            graph_name VARCHAR(100),
            subject TEXT,
            predicate TEXT,
            object TEXT,
            object_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(graph_name, subject, predicate, object, object_type)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_graphs_from_db():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT graph_name, subject, predicate, object, object_type FROM rdf_triples ORDER BY id")
    rows = cur.fetchall()
    
    for row in rows:
        graph_name, subject, predicate, obj, obj_type = row
        s = URIRef(subject)
        p = URIRef(predicate)
        o = URIRef(obj) if obj_type == "uri" else Literal(obj)
        
        if graph_name == "default":
            default_graph.add((s, p, o))
        elif graph_name == "inference":
            inference_graph.add((s, p, o))
        elif graph_name == "validation":
            validation_graph.add((s, p, o))
    
    cur.close()
    conn.close()
    print(f"Loaded from database - Default: {len(default_graph)}, Inference: {len(inference_graph)}, Validation: {len(validation_graph)} triples")

@app.on_event("startup")
async def startup_event():
    init_db()
    load_graphs_from_db()
    print("RDF Storage Service started")
    print(f"Default graph: {len(default_graph)} triples")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "default_graph_size": len(default_graph),
        "inference_graph_size": len(inference_graph),
        "validation_graph_size": len(validation_graph)
    }

@app.post("/sparql")
async def sparql_query(query: str = Body(..., embed=True)):
    try:
        results = default_graph.query(query)
        
        if results.type == "SELECT":
            bindings = []
            for row in results:
                binding = {}
                for var in results.vars:
                    value = row[var]
                    if value is not None:
                        binding[str(var)] = {
                            "type": "uri" if isinstance(value, URIRef) else "literal",
                            "value": str(value)
                        }
                bindings.append(binding)
            
            return {
                "head": {"vars": [str(v) for v in results.vars]},
                "results": {"bindings": bindings}
            }
        elif results.type == "ASK":
            return {"boolean": bool(results)}
        elif results.type == "CONSTRUCT":
            return {"triples": [{"s": str(s), "p": str(p), "o": str(o)} for s, p, o in results]}
        else:
            return {"results": str(results)}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graphs/{graph_name}")
async def get_graph(graph_name: str):
    if graph_name == "default":
        graph = default_graph
    elif graph_name == "inference":
        graph = inference_graph
    elif graph_name == "validation":
        graph = validation_graph
    else:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    triples = []
    for s, p, o in graph:
        triples.append({
            "subject": str(s),
            "predicate": str(p),
            "object": str(o),
            "object_type": "uri" if isinstance(o, URIRef) else "literal"
        })
    
    return {"graph": graph_name, "size": len(graph), "triples": triples}

@app.post("/triples")
async def add_triple(
    subject: str = Body(...),
    predicate: str = Body(...),
    object: str = Body(...),
    object_type: str = Body(default="literal")
):
    try:
        s = URIRef(subject)
        p = URIRef(predicate)
        o = URIRef(object) if object_type == "uri" else Literal(object)
        
        default_graph.add((s, p, o))
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO rdf_triples (graph_name, subject, predicate, object, object_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (graph_name, subject, predicate, object, object_type) DO NOTHING
        """, ("default", subject, predicate, object, object_type))
        
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("triple.added", "default", json.dumps({
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "object_type": object_type
        })))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Triple added",
            "triple": {"subject": subject, "predicate": predicate, "object": object}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/triples")
async def delete_triple(
    subject: str = Body(...),
    predicate: str = Body(...),
    object: str = Body(...),
    object_type: str = Body(default="literal")
):
    try:
        s = URIRef(subject)
        p = URIRef(predicate)
        o = URIRef(object) if object_type == "uri" else Literal(object)
        
        default_graph.remove((s, p, o))
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM rdf_triples 
            WHERE graph_name = 'default' AND subject = %s AND predicate = %s AND object = %s
        """, (subject, predicate, object))
        
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("triple.deleted", "default", json.dumps({
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "object_type": object_type
        })))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": "Triple deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/triples")
async def upsert_triple(
    subject: str = Body(...),
    predicate: str = Body(...),
    object: str = Body(...),
    object_type: str = Body(default="literal")
):
    try:
        s = URIRef(subject)
        p = URIRef(predicate)
        o_new = URIRef(object) if object_type == "uri" else Literal(object)
        
        default_graph.remove((s, p, None))
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM rdf_triples 
            WHERE graph_name = 'default' AND subject = %s AND predicate = %s
        """, (subject, predicate))
        
        default_graph.add((s, p, o_new))
        
        cur.execute("""
            INSERT INTO rdf_triples (graph_name, subject, predicate, object, object_type)
            VALUES (%s, %s, %s, %s, %s)
        """, ("default", subject, predicate, object, object_type))
        
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("triple.upserted", "default", json.dumps({
            "subject": subject,
            "predicate": predicate,
            "object": object,
            "object_type": object_type
        })))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Triple upserted",
            "triple": {"subject": subject, "predicate": predicate, "object": object}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/graphs/inference")
async def update_inference_graph(triples: list = Body(...)):
    try:
        inference_graph.remove((None, None, None))
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM rdf_triples WHERE graph_name = 'inference'")
        
        for triple in triples:
            s = URIRef(triple["subject"])
            p = URIRef(triple["predicate"])
            o = URIRef(triple["object"]) if triple.get("object_type") == "uri" else Literal(triple["object"])
            inference_graph.add((s, p, o))
            
            cur.execute("""
                INSERT INTO rdf_triples (graph_name, subject, predicate, object, object_type)
                VALUES (%s, %s, %s, %s, %s)
            """, ("inference", triple["subject"], triple["predicate"], triple["object"], triple.get("object_type", "literal")))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": f"Inference graph updated with {len(triples)} triples"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/graphs/validation")
async def update_validation_graph(triples: list = Body(...)):
    try:
        validation_graph.remove((None, None, None))
        
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM rdf_triples WHERE graph_name = 'validation'")
        
        for triple in triples:
            s = URIRef(triple["subject"])
            p = URIRef(triple["predicate"])
            o = URIRef(triple["object"]) if triple.get("object_type") == "uri" else Literal(triple["object"])
            validation_graph.add((s, p, o))
            
            cur.execute("""
                INSERT INTO rdf_triples (graph_name, subject, predicate, object, object_type)
                VALUES (%s, %s, %s, %s, %s)
            """, ("validation", triple["subject"], triple["predicate"], triple["object"], triple.get("object_type", "literal")))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": f"Validation graph updated with {len(triples)} triples"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/load/ontology")
async def load_ontology(content: str = Body(..., embed=True)):
    try:
        temp_graph = Graph()
        temp_graph.parse(data=content, format="turtle")
        
        conn = get_db()
        cur = conn.cursor()
        
        for s, p, o in temp_graph:
            default_graph.add((s, p, o))
            
            cur.execute("""
                INSERT INTO rdf_triples (graph_name, subject, predicate, object, object_type)
                VALUES (%s, %s, %s, %s, %s)
            """, ("default", str(s), str(p), str(o), "uri" if isinstance(o, URIRef) else "literal"))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"success": True, "message": "Ontology loaded", "graph_size": len(default_graph)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/reasoning")
async def trigger_reasoning():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("reason.requested", "default", json.dumps({"timestamp": "now", "source": "ui"})))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "Reasoning triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/validation")
async def trigger_validation():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (event_type, graph_name, data)
            VALUES (%s, %s, %s)
        """, ("validate.requested", "default", json.dumps({"timestamp": "now", "source": "ui"})))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "Validation triggered"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
