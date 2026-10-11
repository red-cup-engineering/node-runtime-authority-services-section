#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS
import requests
import os
from rdflib import Graph
from pyshacl import validate

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030/ds')
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')

def perform_shacl_validation():
    print("Fetching data graph via SPARQL CONSTRUCT...")
    
    data_query = """
        CONSTRUCT { ?s ?p ?o }
        WHERE { 
            ?s ?p ?o .
            FILTER(!CONTAINS(STR(?p), "shacl"))
            FILTER(!STRSTARTS(STR(?s), "http://www.w3.org/ns/shacl"))
        }
    """
    
    response = requests.post(
        f"{FUSEKI_URL}/query",
        data={"query": data_query},
        headers={"Accept": "text/turtle"}
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch data graph: {response.status_code}")
        return
    
    data_graph = Graph()
    data_graph.parse(data=response.text, format='turtle')
    print(f"Data graph loaded with {len(data_graph)} triples")
    
    print("Fetching SHACL shapes via SPARQL CONSTRUCT...")
    
    shapes_query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        
        CONSTRUCT { ?s ?p ?o }
        WHERE { 
            {
                ?s a sh:NodeShape .
                ?s ?p ?o .
            } UNION {
                ?s sh:property ?prop .
                ?s ?p ?o .
            } UNION {
                ?s sh:property ?prop .
                ?prop ?p2 ?o2 .
                BIND(?prop AS ?s)
                BIND(?p2 AS ?p)
                BIND(?o2 AS ?o)
            } UNION {
                ?s a sh:PropertyShape .
                ?s ?p ?o .
            }
        }
    """
    
    response = requests.post(
        f"{FUSEKI_URL}/query",
        data={"query": shapes_query},
        headers={"Accept": "text/turtle"}
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch shapes graph: {response.status_code}")
        return
    
    shapes_graph = Graph()
    shapes_graph.parse(data=response.text, format='turtle')
    print(f"SHACL shapes graph loaded with {len(shapes_graph)} triples")
    
    if len(shapes_graph) == 0:
        print("No SHACL shapes found in graph, skipping validation")
        return
    
    print("Running SHACL validation...")
    conforms, results_graph, results_text = validate(
        data_graph,
        shacl_graph=shapes_graph,
        inference='rdfs',
        abort_on_first=False,
        meta_shacl=False
    )
    
    print(f"Validation complete: {'CONFORMS' if conforms else 'VIOLATIONS FOUND'}")
    print(results_text)
    
    print("Writing validation report to dedicated validation graph...")
    
    report_turtle = results_graph.serialize(format='turtle')
    
    response = requests.put(
        f"{FUSEKI_URL}/data?graph=http://example.org/kb/validation/",
        data=report_turtle,
        headers={"Content-Type": "text/turtle"}
    )
    
    if response.status_code in [200, 201, 204]:
        print("Validation report written successfully to validation graph")
    else:
        print(f"Failed to write validation report: {response.status_code} - {response.text}")

async def run_validator():
    nc = NATS()
    
    await nc.connect(NATS_URL)
    print(f"Connected to NATS at {NATS_URL}")
    
    async def message_handler(msg):
        subject = msg.subject
        data = json.loads(msg.data.decode())
        print(f"Received message on {subject}: {data}")
        
        if subject in ["validate.requested", "graph.updated"]:
            perform_shacl_validation()
    
    await nc.subscribe("validate.requested", cb=message_handler)
    await nc.subscribe("graph.updated", cb=message_handler)
    
    print("Validator service listening for events...")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_validator())
