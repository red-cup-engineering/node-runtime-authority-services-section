#!/bin/bash

echo "Starting RDF Knowledge Graph System..."

echo "0. Installing Python dependencies..."
pip3 install -r requirements.txt

echo "1. Starting Docker services..."
docker-compose up -d

echo "2. Waiting for services to be ready..."
sleep 10

echo "3. Loading RDF vocabularies..."
./scripts/load-vocabularies.sh

echo "4. Testing NATS event bus..."
python3 scripts/test-nats.py

echo ""
echo "=== RDF Knowledge Graph System Started ==="
echo "Fuseki UI:      http://localhost:3030"
echo "MinIO Console:  http://localhost:9001"
echo "NATS Monitor:   http://localhost:8222"
echo "Frontend UI:    http://localhost:5000"
echo ""
echo "Run 'docker-compose logs -f' to view service logs"
