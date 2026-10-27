import { admitJsonSemanticContent, identifyProofPathWitness, readGenerativeProofPath, identifyJsonSemanticContent, PROOF_PATH_WITNESS_KIND, GENERATIVE_PROOF_PATH_PROFILE } from '@red-cup-engineering/computer-data-engineering-services-section/semiotic-expression-notation/semantic-content-identity';

const MAX_BYTES = 1048576;
const MIN_NODES = 1;
const MAX_NODES = 256;
const MAX_EDGES = 1024;
const MAX_PREDICATE_MAPS = 256;
const MAX_KEY_LENGTH = 1024;
const MAX_CELL_LENGTH = 4096;
const MAX_ENTRIES = 256;

const GENERATOR_KINDS = Object.freeze(['specialization', 'converse', 'subject-projection', 'object-projection']);
const GENERATOR_SEN_MAP = Object.freeze({
  specialization: 'specialization',
  converse: 'converse',
  'subject-projection': 'subjectProjection',
  'object-projection': 'objectProjection'
});

const STRUCTURE_KEYS = Object.freeze(['version', 'nodes', 'edges', 'predicateMaps']);
const NODE_KEYS = Object.freeze(['key', 'cell']);
const CELL_KEYS = Object.freeze(['subject', 'predicate', 'object']);
const MAP_KEYS = Object.freeze(['key', 'entries']);
const ENTRY_KEYS = Object.freeze(['from', 'to']);
const SIMPLE_EDGE_KEYS = Object.freeze(['from', 'generator', 'to']);
const SPECIALIZATION_EDGE_KEYS = Object.freeze(['from', 'generator', 'to', 'predicateMap']);

export const GENERATIVE_TO_SEN_MARK = Object.freeze(GENERATOR_SEN_MAP);

export const FINITE_GENERATIVE_STRUCTURE_KIND = 'semiotic-content.finite-generative-structure';

function refusal(code, message) {
  const error = new TypeError(message);
  error.code = code;
  return error;
}

function requireUint8Array(value, name) {
  if (!(value instanceof Uint8Array)) {
    throw refusal('unqualified-generative-proof-path', `${name} must be a Uint8Array`);
  }
  if (value.byteLength < 1 || value.byteLength > MAX_BYTES) {
    throw refusal('unqualified-generative-proof-path', `${name} length must be 1..${MAX_BYTES}`);
  }
}

function requireNonemptyString(value, name) {
  if (typeof value !== 'string' || value.length === 0) {
    throw refusal('unqualified-generative-proof-path', `${name} must be a non-empty string`);
  }
}

function requireExactKeys(value, allowedKeys, name) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw refusal('unqualified-generative-proof-path', `${name} must be an object`);
  }
  const actual = Object.keys(value).sort();
  const expected = [...allowedKeys].sort();
  if (actual.length !== expected.length || actual.some((k, i) => k !== expected[i])) {
    throw refusal('unqualified-generative-proof-path', `${name} must have exactly keys ${expected.join(',')}`);
  }
}

function requireStringRange(value, name, minLength, maxLength) {
  if (typeof value !== 'string' || value.length < minLength || value.length > maxLength) {
    throw refusal('unqualified-generative-proof-path', `${name} must be a string of length ${minLength}..${maxLength}`);
  }
}

function requireCanonicalKey(value, name) {
  requireStringRange(value, name, 1, MAX_KEY_LENGTH);
  if (value !== value.normalize('NFC')) {
    throw refusal('unqualified-generative-proof-path', name + ' must already be NFC');
  }
}

function isKnownNode(nodeLookup, key) {
  return typeof key === 'string' && nodeLookup.has(key);
}

function areCellsEqual(cellA, cellB) {
  return cellA.subject === cellB.subject &&
    cellA.predicate === cellB.predicate &&
    cellA.object === cellB.object;
}

function qualifyStructure(value) {
  requireExactKeys(value, STRUCTURE_KEYS, 'structure');
  if (value.version !== 1) {
    throw refusal('unqualified-generative-proof-path', 'structure version must be 1');
  }

  const { nodes, edges, predicateMaps } = value;

  if (!Array.isArray(nodes) || nodes.length < MIN_NODES || nodes.length > MAX_NODES) {
    throw refusal('unqualified-generative-proof-path', `nodes count must be ${MIN_NODES}..${MAX_NODES}`);
  }
  if (!Array.isArray(edges) || edges.length > MAX_EDGES) {
    throw refusal('unqualified-generative-proof-path', `edges count must be 0..${MAX_EDGES}`);
  }
  if (!Array.isArray(predicateMaps) || predicateMaps.length > MAX_PREDICATE_MAPS) {
    throw refusal('unqualified-generative-proof-path', `predicateMaps count must be 0..${MAX_PREDICATE_MAPS}`);
  }

  const nodeLookup = new Map();
  const nodeCells = new Map();
  for (const node of nodes) {
    requireExactKeys(node, NODE_KEYS, 'node');
    requireCanonicalKey(node.key, 'node.key');
    requireExactKeys(node.cell, CELL_KEYS, 'node.cell');
    requireStringRange(node.cell.subject, 'node.cell.subject', 1, MAX_CELL_LENGTH);
    requireStringRange(node.cell.predicate, 'node.cell.predicate', 1, MAX_CELL_LENGTH);
    requireStringRange(node.cell.object, 'node.cell.object', 1, MAX_CELL_LENGTH);
    if (nodeLookup.has(node.key)) {
      throw refusal('unqualified-generative-proof-path', `duplicate node key: ${node.key}`);
    }
    nodeLookup.set(node.key, node.cell);
    nodeCells.set(node.key, node.cell);
  }

  const mapLookup = new Map();
  for (const map of predicateMaps) {
    requireExactKeys(map, MAP_KEYS, 'predicateMap');
    requireCanonicalKey(map.key, 'predicateMap.key');
    if (!Array.isArray(map.entries) || map.entries.length < 1 || map.entries.length > MAX_ENTRIES) {
      throw refusal('unqualified-generative-proof-path', `predicateMap entries count must be 1..${MAX_ENTRIES}`);
    }
    if (mapLookup.has(map.key)) {
      throw refusal('unqualified-generative-proof-path', `duplicate predicateMap key: ${map.key}`);
    }
    const fromSet = new Set();
    for (const entry of map.entries) {
      requireExactKeys(entry, ENTRY_KEYS, 'predicateMap entry');
      requireStringRange(entry.from, 'predicateMap entry.from', 1, MAX_CELL_LENGTH);
      requireStringRange(entry.to, 'predicateMap entry.to', 1, MAX_CELL_LENGTH);
      if (fromSet.has(entry.from)) {
        throw refusal('unqualified-generative-proof-path', `duplicate predicateMap from: ${entry.from}`);
      }
      fromSet.add(entry.from);
    }
    mapLookup.set(map.key, map.entries);
  }

  const edgeSet = new Set();
  const edgeMap = new Map();
  for (const edge of edges) {
    if (edge === null || typeof edge !== 'object' || Array.isArray(edge)) {
      throw refusal('unqualified-generative-proof-path', 'edge must be an object');
    }
    if (!GENERATOR_KINDS.includes(edge.generator)) {
      throw refusal('unqualified-generative-proof-path', `unknown edge generator: ${edge.generator}`);
    }
    if (edge.generator === 'specialization') {
      requireExactKeys(edge, SPECIALIZATION_EDGE_KEYS, 'specialization edge');
    } else {
      requireExactKeys(edge, SIMPLE_EDGE_KEYS, 'generative edge');
    }

    if (!isKnownNode(nodeLookup, edge.from)) {
      throw refusal('unqualified-generative-proof-path', `edge from unknown node: ${edge.from}`);
    }
    if (!isKnownNode(nodeLookup, edge.to)) {
      throw refusal('unqualified-generative-proof-path', `edge to unknown node: ${edge.to}`);
    }
    if (edge.generator === 'specialization') {
      if (!mapLookup.has(edge.predicateMap)) {
        throw refusal('unqualified-generative-proof-path', `specialization references unknown predicateMap: ${edge.predicateMap}`);
      }
    }

    const lookupKey = JSON.stringify([edge.from, edge.generator, edge.to]);
    if (edgeSet.has(lookupKey)) {
      throw refusal('unqualified-generative-proof-path', `duplicate edge: ${lookupKey}`);
    }
    edgeSet.add(lookupKey);
    edgeMap.set(lookupKey, edge);
  }

  // Qualify every declared edge.
  for (const edge of edges) {
    const sourceCell = nodeLookup.get(edge.from);
    const targetCell = nodeLookup.get(edge.to);

    switch (edge.generator) {
      case 'converse':
        if (!areCellsEqual(targetCell, { subject: sourceCell.object, predicate: sourceCell.predicate, object: sourceCell.subject })) {
          throw refusal('unqualified-generative-proof-path', `converse edge cell mismatch: ${edge.from} -> ${edge.to}`);
        }
        break;
      case 'subject-projection':
        if (!areCellsEqual(targetCell, { subject: sourceCell.subject, predicate: sourceCell.predicate, object: sourceCell.subject })) {
          throw refusal('unqualified-generative-proof-path', `subject-projection edge cell mismatch: ${edge.from} -> ${edge.to}`);
        }
        break;
      case 'object-projection':
        if (!areCellsEqual(targetCell, { subject: sourceCell.object, predicate: sourceCell.predicate, object: sourceCell.object })) {
          throw refusal('unqualified-generative-proof-path', `object-projection edge cell mismatch: ${edge.from} -> ${edge.to}`);
        }
        break;
      case 'specialization': {
        const entries = mapLookup.get(edge.predicateMap);
        const entry = entries.find(e => e.from === sourceCell.predicate);
        if (!entry) {
          throw refusal('unqualified-generative-proof-path', `specialization predicateMap missing image for ${sourceCell.predicate}`);
        }
        if (!areCellsEqual(targetCell, { subject: sourceCell.subject, predicate: entry.to, object: sourceCell.object })) {
          throw refusal('unqualified-generative-proof-path', `specialization edge cell mismatch: ${edge.from} -> ${edge.to}`);
        }
        break;
      }
    }
  }

  return { nodeLookup, nodeCells, edgeMap };
}

function qualifyWitness(value) {
  requireNonemptyString(value.sourceKey, 'sourceKey');
  requireNonemptyString(value.targetKey, 'targetKey');
  requireNonemptyString(value.path, 'witness path');
  return readGenerativeProofPath({
    sourceKey: value.sourceKey,
    targetKey: value.targetKey,
    path: value.path
  });
}

export function identifyFiniteGenerativeStructure({ value, witnessRoot } = {}) {
  qualifyStructure(value);
  return identifyJsonSemanticContent({ objectKind: FINITE_GENERATIVE_STRUCTURE_KIND, value, witnessRoot });
}
export function qualifyGenerativeProofPath({ structureBytes, structureRoot, witnessBytes, witnessRoot } = {}) {
  requireUint8Array(structureBytes, 'structureBytes');
  requireUint8Array(witnessBytes, 'witnessBytes');
  requireNonemptyString(structureRoot, 'structureRoot');
  requireNonemptyString(witnessRoot, 'witnessRoot');

  const s = admitJsonSemanticContent({ bytes: structureBytes, token: structureRoot, objectKind: FINITE_GENERATIVE_STRUCTURE_KIND });
  const w = admitJsonSemanticContent({ bytes: witnessBytes, token: witnessRoot, objectKind: PROOF_PATH_WITNESS_KIND });

  const rebuiltWitness = identifyProofPathWitness({ ...w.value, witnessRoot: w.envelope.witnessRoot });
  if (rebuiltWitness.bytes.length !== w.bytes.length || !rebuiltWitness.bytes.every((b, i) => b === w.bytes[i])) {
    throw refusal('unqualified-generative-proof-path', 'witness bytes do not match rebuilt witness');
  }

  if (s.id !== structureRoot || w.value.structureRoot !== s.id) {
    throw refusal('unqualified-generative-proof-path', 'structure root mismatch');
  }
  if (w.id !== witnessRoot) {
    throw refusal('unqualified-generative-proof-path', 'witness root mismatch');
  }

  const structure = qualifyStructure(s.value);
  const witness = qualifyWitness(w.value);

  const route = witness;

  if (!structure.nodeLookup.has(route.sourceKey)) {
    throw refusal('unqualified-generative-proof-path', 'route source key is not a known node');
  }
  if (!structure.nodeLookup.has(route.targetKey)) {
    throw refusal('unqualified-generative-proof-path', 'route target key is not a known node');
  }

  const qualifiedSteps = route.steps.map(step => {
    const lookupKey = JSON.stringify([step.from, step.generator, step.to]);
    if (!structure.edgeMap.has(lookupKey)) {
      throw refusal('unqualified-generative-proof-path', `requested step not a declared qualified edge: ${lookupKey}`);
    }
    return Object.freeze({
      ...step,
      senGenerator: GENERATIVE_TO_SEN_MARK[step.generator]
    });
  });

  return Object.freeze({
    type: 'QualifiedGenerativeProofPath',
    proofProfile: GENERATIVE_PROOF_PATH_PROFILE,
    structureRoot: s.id,
    witnessRoot: w.id,
    sourceKey: w.value.sourceKey,
    targetKey: w.value.targetKey,
    sourceCell: structure.nodeCells.get(route.sourceKey),
    targetCell: structure.nodeCells.get(route.targetKey),
    steps: Object.freeze(qualifiedSteps)
  });
}