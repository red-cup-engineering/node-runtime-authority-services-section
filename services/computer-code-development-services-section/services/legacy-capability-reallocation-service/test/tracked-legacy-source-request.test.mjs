import assert from 'node:assert/strict';
import test from 'node:test';
import {readTrackedLegacySourcePublicationRequest} from '../src/tracked-legacy-source-publication.mjs';

test('source preparation admits exact publisher request before any repository effect', async () => {
  const path = String.raw`lib/legacy/"First Steps \360\237.md"`;
  const reviewedSource = {revision:'a'.repeat(40),entries:[{path,mode:'100644',type:'blob',sha:'b'.repeat(40)}]};
  const request = await readTrackedLegacySourcePublicationRequest({paths:[path],reviewedSource});
  assert.deepEqual(request,{paths:[path],message:'Retire reviewed Git-preserved legacy capabilities',
    push:true,dryRun:false,reviewedSource});
});

test('supplier path, scope and object refusals are available without a local retirement', async () => {
  for (const path of [String.raw`a\..\b`, 'a/./b', 'a/\u001bfile']) {
    await assert.rejects(readTrackedLegacySourcePublicationRequest({paths:[path],
      reviewedSource:{revision:'a'.repeat(40),entries:[{path,absent:true}]}}), TypeError);
  }
  await assert.rejects(readTrackedLegacySourcePublicationRequest({paths:['a'],
    reviewedSource:{revision:'a'.repeat(40),entries:[{path:'foreign',absent:true}]}}), TypeError);
  await assert.rejects(readTrackedLegacySourcePublicationRequest({paths:['a'],
    reviewedSource:{revision:'a'.repeat(40),entries:[{path:'a',mode:'100644',type:'commit',sha:'b'.repeat(40)}]}}), TypeError);
});
