#!/bin/bash

echo "Loading RDF vocabularies into Fuseki..."

FUSEKI_URL=${FUSEKI_URL:-"http://localhost:3030/ds"}

# Wait for Fuseki to be ready
echo "Waiting for Fuseki to be available..."
until curl -sf ${FUSEKI_URL} > /dev/null; do
    echo "Fuseki not ready, waiting..."
    sleep 2
done

echo "Fuseki is ready. Loading ontology..."
curl -X POST \
  -H "Content-Type: text/turtle" \
  --data-binary @vocabularies/ontology.ttl \
  ${FUSEKI_URL}/data

echo "Loading SHACL shapes..."
curl -X POST \
  -H "Content-Type: text/turtle" \
  --data-binary @vocabularies/shapes.ttl \
  ${FUSEKI_URL}/data

echo "Vocabularies loaded successfully!"
