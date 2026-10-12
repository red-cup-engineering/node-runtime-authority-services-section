import assert from 'node:assert/strict';
import test from 'node:test';
import {canonical} from '@red-cup-engineering/json-services-section';
import {senProjector} from '../src/semiotic-expression-notation/projector.mjs';
import {parseSen} from '../src/semiotic-expression-notation/reader.mjs';
import {jsonProjector} from '@red-cup-engineering/computer-content-engineering-services-section/json-projector';
const term=['app',['lam',['var',0]],['mark','fixture']];
test('SEN representation is a strict parser over unreduced admitted syntax',()=>{
 const source=JSON.stringify(term),resource={path:'fixture',content:source};
 assert.equal(senProjector.rung,'strict');assert.equal(senProjector.corner,'assertion');assert.equal(senProjector.parent,jsonProjector);
 assert.deepEqual(senProjector.read(resource),[term]);assert.deepEqual(parseSen(source),term);
 assert.equal(senProjector.write([term]),canonical(term)+'\n');
 assert.equal(senProjector.write([]),'');
});
test('recognition cannot substitute for actual read and write admission',()=>{
 for(const value of [{plain:true},['var',0],['app',['mark','a'],['mark','b']]]){
  const resource={path:'fixture',content:JSON.stringify(value)};
  assert.equal(senProjector.recognize(resource),false);assert.throws(()=>senProjector.read(resource));assert.throws(()=>senProjector.write([value]));
 }
});
