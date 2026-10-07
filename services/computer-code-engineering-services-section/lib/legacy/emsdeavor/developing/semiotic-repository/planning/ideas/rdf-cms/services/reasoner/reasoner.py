#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS
import requests
import os
from rdflib import Graph
from owlrl import DeductiveClosure, RDFS_OWLRL_Semantics

FUSEKI_URL = os.getenv('FUSEKI_URL', 'http://localhost:3030/ds')
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')

def perform_owl_reasoning():
    print("Fetching base data from default graph (bypassing union) via graph store API...")
    
    response = requests.get(
        f"{FUSEKI_URL}/get?default",
        headers={"Accept": "text/turtle"}
    )
    
    if response.status_code != 200:
        print(f"Failed to fetch default graph: {response.status_code}")
        return
    
    g = Graph()
    if response.text.strip():
        g.parse(data=response.text, format='turtle')
    
    initial_triples = set(g)
    initial_size = len(initial_triples)
    print(f"Base data graph (default only) has {initial_size} triples before reasoning")
    
    DeductiveClosure(RDFS_OWLRL_Semantics).expand(g)
    
    final_triples = set(g)
    final_size = len(final_triples)
    
    inferred_triples = final_triples - initial_triples
    inferred_count = len(inferred_triples)
    print(f"Reasoning complete: {inferred_count} new triples inferred from base data")
    
    inferred_graph = Graph()
    
    for triple in inferred_triples:
        inferred_graph.add(triple)
    
    print(f"Writing {len(inferred_graph)} inferred triples to inference graph...")
    
    inferred_turtle = inferred_graph.serialize(format='turtle')
    
    response = requests.put(
        f"{FUSEKI_URL}/data?graph=http://example.org/kb/inferred/",
        data=inferred_turtle,
        headers={"Content-Type": "text/turtle"}
    )
    
    if response.status_code in [200, 201, 204]:
        print(f"Successfully wrote {len(inferred_graph)} inferred triples to inference graph")
    else:
        print(f"Failed to write inferred triples: {response.status_code} - {response.text}")

async def run_reasoner():
    nc = NATS()
    
    await nc.connect(NATS_URL)
    print(f"Connected to NATS at {NATS_URL}")
    
    async def message_handler(msg):
        subject = msg.subject
        data = json.loads(msg.data.decode())
        print(f"Received message on {subject}: {data}")
        
        if subject in ["graph.updated", "reason.requested"]:
            perform_owl_reasoning()
    
    await nc.subscribe("graph.updated", cb=message_handler)
    await nc.subscribe("reason.requested", cb=message_handler)
    
    print("Reasoner service listening for events...")
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_reasoner())
