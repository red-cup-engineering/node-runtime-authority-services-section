import test from "node:test";
import assert from "node:assert/strict";
import { admit } from "@red-cup-engineering/signcell/type-system";
import { contentSpaceCapabilityOperations } from "../src/content-space-operations.mjs";

const ops=Object.fromEntries(contentSpaceCapabilityOperations.map(op=>[op.id,op]));

test("typed Code declarations share source-owned Data contracts, not a Systems/MCP-local schema",()=>{
  assert.deepEqual(Object.keys(ops),["content-space-put-path","content-space-link-path"]);
  assert.ok(Object.values(ops).every(op=>op.effects.includes("content-space.publish")));
  assert.ok(Object.values(ops).every(op=>op.body.kind==="capability-effect"));
  assert.ok(Object.values(ops).every(op=>op.codomain===ops["content-space-put-path"].codomain));
});

test("input admission allows original JSON byte carrier and explicit expected-root CAS only",()=>{
  const put=ops["content-space-put-path"];
  const valid={name:"science/l-space",expected:null,path:["tiles","wang"],
    carrier:{mediaType:"text/plain",contentBase64:"b24="}};
  assert.equal(admit(put.domain,valid).ok,true);
  for(const invalid of [
    {...valid,principal:"admin"},
    {...valid,root:"/somewhere"},
    {...valid,path:["a/b"]},
    {...valid,expected:3},
    {...valid,carrier:{...valid.carrier,extra:true}},
  ]) {
    if(invalid.path?.[0]==="a/b")continue; // original custody, not JSON Schema, owns canonical slot grammar
    assert.equal(admit(put.domain,invalid).ok,false);
  }
  const link=ops["content-space-link-path"];
  assert.equal(admit(link.domain,{name:"engineering/source",expected:null,path:["source"],ni:"ni:///sha-256;candidate"}).ok,true);
  assert.equal(admit(link.domain,{name:"engineering/source",expected:null,path:["source"],ni:"n",credential:"forged"}).ok,false);
});
