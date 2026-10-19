/**
 * Code-owned discovery of *candidate* typed operation compositions.
 * Schema IDs identify interface presentations; matching IDs do not establish
 * subtyping, a Hoare proof, a running host, authority or an external effect.
 * Systems/Networking may project these structures without computing their own
 * operation join, rewriting JSON Schema URI rules, or inventing evidence.
 */
import { bytesCompare, semanticBytes } from "@red-cup-engineering/computer-content-address-engineering-services-section/semiotic-content-address";
import { resolveSchemaUri } from "@red-cup-engineering/json-schema-services-section/validation";

const compare = (a, b) => bytesCompare(semanticBytes(a), semanticBytes(b));
const sorted = values => Object.freeze([...values].sort(compare));
const entries = map => Object.freeze([...map]
  .sort(([a], [b]) => compare(a, b))
  .map(([schema, operations]) => Object.freeze({ schema, operations: sorted(operations) })));

/** Resolve a full, source-declared JSON Schema slot, never match bare relative labels. */
export function operationSchemaSlot(schema) {
  const reference = schema?.$ref ?? schema?.$id;
  if (typeof reference !== "string" || reference.length === 0) return undefined;
  const base = typeof schema?.$id === "string" ? schema.$id : "";
  const resolved = resolveSchemaUri(base, reference);
  return typeof resolved === "string" && /^[a-z][a-z0-9+.-]*:/iu.test(resolved) ? resolved : undefined;
}

/** Extract the original operation names at each typed boundary. */
function slots(programs, side) {
  const bySchema = new Map();
  for (const program of programs) {
    const schema = operationSchemaSlot(side === "domain" ? program.domainSchema : program.codomainSchema);
    if (schema === undefined) continue;
    const operations = bySchema.get(schema) ?? [];
    operations.push(program.name);
    bySchema.set(schema, operations);
  }
  return bySchema;
}

/** One operation family's candidate compositions and unfinished type frontiers. */
export function operationSchemaTopology(programs) {
  if (!Array.isArray(programs)) throw new TypeError("operation programs must be an array");
  const names = new Set();
  for (const program of programs) {
    if (!program || typeof program.name !== "string" || !program.name)
      throw new TypeError("operation name must be a nonempty string");
    if (names.has(program.name)) throw new TypeError("duplicate-component: operation name appears twice");
    names.add(program.name);
  }
  const byName = new Map(programs.map(p => [p.name, p]));
  const domains = slots(programs, "domain");
  const codomains = slots(programs, "codomain");
  const edges = [];
  for (const [schema, producers] of codomains) {
    const consumers = domains.get(schema) ?? [];
    for (const from of producers) for (const to of consumers) {
      const producer = byName.get(from)?.contract;
      const consumer = byName.get(to)?.contract;
      const contractComposition = producer && consumer ? {
        producer: producer.contract?.id, producerReading: producer.reading,
        consumer: consumer.contract?.id, consumerReading: consumer.reading,
      } : undefined;
      if (contractComposition && (!contractComposition.producer || !contractComposition.consumer))
        throw new TypeError("invalid declared operation contract identity");
      edges.push(Object.freeze(contractComposition === undefined
        ? { from, to, schema, relation: "codomain-domain-candidate" }
        : { from, to, schema, relation: "schema-contract-composition-candidate",
            contractComposition: Object.freeze(contractComposition) }));
    }
  }
  edges.sort((a, b) => compare(a.schema, b.schema) || compare(a.from, b.from) || compare(a.to, b.to));
  return Object.freeze({
    domains: entries(domains), codomains: entries(codomains),
    incoming: entries(new Map([...domains].filter(([schema]) => !codomains.has(schema)))),
    outgoing: entries(new Map([...codomains].filter(([schema]) => !domains.has(schema)))),
    edges: Object.freeze(edges),
  });
}

/**
 * Cross-package candidates are derived FROM original declared operations, not
 * copied/read from independently supplied extrema metadata. Code reuses its
 * own operationSchemaTopology for each package; Systems interprets the result
 * into the same SignCells it uses locally. An interface match is not an effect
 * grant or proof that either operation was deployed.
 */
export function operationSchemaMesh(packages) {
  if (!Array.isArray(packages)) throw new TypeError("operation packages must be an array");
  const identities = new Set();
  const admitted = packages.map(pkg => {
    if (!pkg || typeof pkg.package !== "string" || !pkg.package || identities.has(pkg.package))
      throw new TypeError("distinct nonempty package identities are required");
    identities.add(pkg.package);
    // A derivative list of type slots is not authority to manufacture a match.
    const topology = operationSchemaTopology(pkg.programs);
    return Object.freeze({package: pkg.package, ...topology});
  });
  const producers = new Map(), consumers = new Map();
  for (const pkg of admitted) for (const [side, index] of [["codomains", producers], ["domains", consumers]]) {
    for (const extremum of pkg[side]) {
      const declared = index.get(extremum.schema) ?? [];
      for (const operation of extremum.operations)
        declared.push(Object.freeze({ package: pkg.package, operation }));
      index.set(extremum.schema, declared);
    }
  }
  const edges = [];
  for (const [schema, outputs] of producers) {
    for (const from of outputs) for (const to of (consumers.get(schema) ?? [])) {
      if (from.package === to.package) continue;
      edges.push(Object.freeze({
        fromPackage:from.package, from:from.operation,
        toPackage:to.package, to:to.operation,
        schema, relation:"codomain-domain-candidate",
      }));
    }
  }
  edges.sort((a,b) => compare(a.schema,b.schema)||compare(a.fromPackage,b.fromPackage)||
    compare(a.from,b.from)||compare(a.toPackage,b.toPackage)||compare(a.to,b.to));
  const frontier = side => {
    const missing = side === "incoming" ? producers : consumers;
    const result = [];
    for (const pkg of admitted) for (const extremum of pkg[side === "incoming" ? "domains" : "codomains"]) {
      if (!missing.has(extremum.schema)) result.push(Object.freeze({
        package:pkg.package, schema:extremum.schema, operations:extremum.operations,
      }));
    }
    return Object.freeze(result.sort((a,b)=>compare(a.schema,b.schema)||compare(a.package,b.package)));
  };
  return Object.freeze({edges:Object.freeze(edges),frontier:Object.freeze({incoming:frontier("incoming"),outgoing:frontier("outgoing")})});
}
