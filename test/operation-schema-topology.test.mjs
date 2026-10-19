import test from 'node:test';
import assert from 'node:assert/strict';
import { operationSchemaSlot, operationSchemaTopology, operationSchemaMesh } from '../src/operation-schema-topology.mjs';

const schema = id => ({ $ref:id });
const endpoint = (name, domain, codomain, contract) => ({
  name, ...(domain ? { domainSchema:schema(domain) } : {}),
  ...(codomain ? { codomainSchema:schema(codomain) } : {}),
  ...(contract ? {contract} : {}),
});
const S='https://example.org/schema/shared.json';

test('resolves original JSON Schema identity and refuses bare relative name matching', () => {
  assert.equal(operationSchemaSlot({$id:'https://example.org/path/source.json',$ref:'../schema/shared.json'}), S);
  assert.equal(operationSchemaSlot({$ref:'shared.json'}), undefined);
  assert.equal(operationSchemaSlot({$id:S}), S);
  assert.equal(operationSchemaSlot({}), undefined);
});

test('local candidate edges are directed, source-schema matched, and not claimed executed',()=>{
  const topology = operationSchemaTopology([
    endpoint('producer',undefined,S),
    endpoint('consumer',S),
    endpoint('different',undefined,'https://example.org/other.json'),
  ]);
  assert.deepEqual(topology.edges,[{from:'producer',to:'consumer',schema:S,relation:'codomain-domain-candidate'}]);
  assert.deepEqual(topology.incoming,[]);
  assert.deepEqual(topology.outgoing,[{schema:'https://example.org/other.json',operations:['different']}]);
  assert.ok(Object.isFrozen(topology.edges));
});

test('two different operation contracts remain candidate metadata, never a proof',()=>{
  const topo=operationSchemaTopology([
    endpoint('A',undefined,S,{contract:{id:'P'},reading:'held'}),
    endpoint('B',S,undefined,{contract:{id:'Q'},reading:'held'}),
  ]);
  assert.deepEqual(topo.edges,[{from:'A',to:'B',schema:S,relation:'schema-contract-composition-candidate',
    contractComposition:{producer:'P',producerReading:'held',consumer:'Q',consumerReading:'held'}}]);
  assert.equal('ok' in topo.edges[0],false);
});

test('duplicate operation and invented contract identities refuse',()=>{
  assert.throws(()=>operationSchemaTopology([endpoint('same',undefined,S),endpoint('same',S)]),/duplicate-component/);
  assert.throws(()=>operationSchemaTopology([
    endpoint('A',undefined,S,{contract:{},reading:'held'}),
    endpoint('B',S,undefined,{contract:{id:'Q'},reading:'held'}),
  ]),/invalid declared/);
});

test('cross-package candidates preserve direction, avoid self joining, expose true frontiers',()=>{
  const up=operationSchemaTopology([endpoint('produce',undefined,S)]);
  const down=operationSchemaTopology([endpoint('consume',S)]);
  const orphan=operationSchemaTopology([endpoint('other','https://example.org/missing.json')]);
  const actual=operationSchemaMesh([
    {package:'up',programs:[endpoint('produce',undefined,S)]},
    {package:'down',programs:[endpoint('consume',S)]},
    {package:'orphan',programs:[endpoint('other','https://example.org/missing.json')]},
  ]);
  assert.deepEqual(actual.edges,[{fromPackage:'up',from:'produce',toPackage:'down',to:'consume',schema:S,relation:'codomain-domain-candidate'}]);
  assert.deepEqual(actual.frontier.incoming,[{package:'orphan',schema:'https://example.org/missing.json',operations:['other']}]);
  assert.deepEqual(actual.frontier.outgoing,[]);
  assert.throws(()=>operationSchemaMesh([{package:'up',programs:[]},{package:'up',programs:[]}]),/distinct nonempty/);
});

test('Unicode operation names are stable in canonical byte order',()=>{
  const got=operationSchemaTopology([endpoint('é',S),endpoint('z',S),endpoint('🦉',S)]);
  assert.deepEqual(got.domains[0].operations,['z','é','🦉']);
});

test('a forged precomputed extrema surface cannot produce a candidate edge',()=>{
  assert.throws(()=>operationSchemaMesh([{package:'forge',domains:[{schema:S,operations:['P']}],codomains:[{schema:S,operations:['Q']}]}]),/operation programs must be an array/);
  const candidate=operationSchemaMesh([{package:'P',programs:[endpoint('P',undefined,S)]},{package:'Q',programs:[endpoint('Q',S)]}]);
  assert.equal(candidate.edges.length,1);
  assert.equal(Object.hasOwn(candidate.edges[0],'proof'),false);
});
