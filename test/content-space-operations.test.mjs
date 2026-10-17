import test from "node:test";
import assert from "node:assert/strict";
import { admit } from "@red-cup-engineering/signcell/type-system";
import { contentSpaceCapabilityOperations } from "../src/content-space-operations.mjs";

const ops=Object.fromEntries(contentSpaceCapabilityOperations.map(op=>[op.id,op]));

test("typed Code declarations share source-owned Data contracts, not a Systems/MCP-local schema",()=>{
  assert.deepEqual(Object.keys(ops),[
    "content-space-put-path","content-space-link-path",
    "content-space-link-batch","content-space-walk",
  ]);
  assert.ok(["content-space-put-path","content-space-link-path","content-space-link-batch"]
    .every(id=>ops[id].effects.includes("content-space.publish")));
  assert.deepEqual(ops["content-space-walk"].effects,["content-space.read"]);
  assert.ok(Object.values(ops).every(op=>op.body.kind==="capability-effect"));
  assert.equal(ops["content-space-put-path"].codomain,ops["content-space-link-path"].codomain);
  assert.notEqual(ops["content-space-walk"].codomain,ops["content-space-link-batch"].codomain);
});

test("input admission allows original JSON byte carrier and explicit expected-root CAS only",()=>{
  const put=ops["content-space-put-path"];
  const valid={name:"science/l-space",expected:null,path:["tiles","wang"],
    carrier:{mediaType:"text/plain",contentBase64:"b24="}};
  assert.equal(admit(put.domain,valid).ok,true);
  for(const invalid of [
    {...valid,principal:"admin"},
    {...valid,root:"/somewhere"},
    {...valid,expected:3},
    {...valid,carrier:{...valid.carrier,extra:true}},
  ]) {
    assert.equal(admit(put.domain,invalid).ok,false);
  }
  const link=ops["content-space-link-path"];
  assert.equal(admit(link.domain,{name:"engineering/source",expected:null,path:["source"],ni:"ni:///sha-256;candidate"}).ok,true);
  assert.equal(admit(link.domain,{name:"engineering/source",expected:null,path:["source"],ni:"n",credential:"forged"}).ok,false);
});


test("typed batch construction and immutable Merkle inventory reject injected authority and out-of-bounds work",()=>{
  const batch=ops["content-space-link-batch"];
  const walk=ops["content-space-walk"];
  const source={name:"science/l-space",expected:null,links:[
    {path:["weaving","bead"],ni:"ni:///sha-256;source1"},
    {path:["tiling","wang"],ni:"ni:///sha-256;source2"},
  ]};
  assert.equal(admit(batch.domain,source).ok,true);
  assert.equal(admit(walk.domain,{name:"science/l-space",maximumNodes:64,maximumDepth:2}).ok,true);
  for(const bad of [
    {...source,principal:"actor:admin"},
    {...source,root:"/var/private"},
    {...source,links:[]},
    {...source,links:[{path:["a"],ni:"ni:///sha-256;x",grant:"forge"}]},
    {...source,links:[{path:["a"],ni:"ni:///sha-256;x",auth:"true"}]},
    {...source,links:[{path:["a"],ni:"ni:///sha-256;x"},...new Array(128).fill({path:["b"],ni:"ni:///sha-256;x"})]},
  ])assert.equal(admit(batch.domain,bad).ok,false);
  for(const bad of [
    {name:"science/l-space",maximumNodes:0},
    {name:"science/l-space",maximumNodes:257},
    {name:"science/l-space",maximumDepth:17},
    {name:"science/l-space",principal:"admin"},
    {name:"science/l-space",ni:"ni:///sha-256;source"},
  ])assert.equal(admit(walk.domain,bad).ok,false);
});
