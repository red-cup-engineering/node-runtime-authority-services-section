#!/usr/bin/env python3
import asyncio
import json
from nats.aio.client import Client as NATS

async def main():
    nc = NATS()
    
    await nc.connect("nats://localhost:4222")
    print("Connected to NATS")
    
    print("Publishing test event to 'graph.updated'...")
    await nc.publish("graph.updated", json.dumps({
        "type": "triple_added",
        "subject": "http://example.org/kb/Statement1",
        "predicate": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
        "object": "http://example.org/kb/Statement"
    }).encode())
    
    print("Publishing validation request to 'validate.requested'...")
    await nc.publish("validate.requested", json.dumps({
        "graph": "http://example.org/kb/",
        "shapes": ["http://example.org/kb/StatementShape"]
    }).encode())
    
    await asyncio.sleep(1)
    
    await nc.close()
    print("Test events published successfully!")

if __name__ == "__main__":
    asyncio.run(main())
