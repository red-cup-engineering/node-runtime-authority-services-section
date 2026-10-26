import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
const logs="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-code-fabrication-services-section/services/javascript-node-code-fabrication-services-section/services/jsnode-package-services-section/data/logs/pnpm-importer-recovery-20261022";
const record="/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-code-fabrication-services-section/services/javascript-node-code-fabrication-services-section/services/jsnode-package-services-section/data/records/2026-10-22-pnpm-importer-source-recovery.json";
const archives=JSON.parse(fs.readFileSync(path.join(logs,"qualified-archives.json")));
const gitBlob=file=>{const bytes=fs.readFileSync(file);return crypto.createHash("sha1").update(Buffer.from("blob "+bytes.length+"\0")).update(bytes).digest("hex");};
for(const archive of archives){
 archive.parserBlob=gitBlob(path.join(logs,archive.version,"package/src/workspace/pnpm-lockfile.mjs"));
 if(archive.version!=="0.2.4"){
  archive.originalParserBlobMatches=archive.parserBlob==="e1d1d559dc223c800df97a5270b29dbb67a1497b";
  archive.nativeTestBlob=gitBlob(path.join(logs,archive.version,"package/test/pnpm-lockfile-importers.test.mjs"));
  archive.originalNativeTestBlobMatches=archive.nativeTestBlob==="05a2e98cb64775b1b204eaa1df52fe9a1d275246";
  if(!archive.originalParserBlobMatches||!archive.originalNativeTestBlobMatches)throw new Error("original source mismatch "+archive.version);
 }
}
const receipt={
 kind:"jsnode-package.pnpm-importer-source-recovery",
 version:1,
 observedAt:new Date().toISOString(),
 outcome:"published-source-qualified",
 originalOwner:{repository:"red-cup-engineering/computer-code-engineering-services-section",
 commit:"eb455440c4da9c7c30d9c066a85476bdacb5a85b",
 sourcePath:"services/javascript-engineering-services-section/services/javascript-code-fabrication-services-section/services/javascript-node-code-fabrication-services-section/services/jsnode-package-services-section/src/workspace/pnpm-lockfile.mjs",
 localOwner:"/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section/services/javascript-engineering-services-section/services/javascript-code-fabrication-services-section/services/javascript-node-code-fabrication-services-section/services/jsnode-package-services-section",
 sourceBlob:"e1d1d559dc223c800df97a5270b29dbb67a1497b",
 testPath:"test/pnpm-lockfile-importers.test.mjs",testBlob:"05a2e98cb64775b1b204eaa1df52fe9a1d275246"},
 independentOwner:{repository:"red-cup-engineering/jsnode-package-services-section",preservedFixCommit:"9ee43564645aa8bac259ac37963aca8f3c52bd20",branchesInspected:["main","jsnode-0.5.0-front-matter"]},
 selectedRelease:"0.5.0",
 earliestStableQualified:"0.3.0",
 archives,
 evidence:JSON.parse(fs.readFileSync(path.join(logs,"test-results.json"))),
 consumer:{repository:"red-cup-engineering/agent-organization-engine",baselineCommit:"267f554",module:"lib/organizing/src/js-mark.mjs",test:"lib/organizing/test/workspace-coordination.test.mjs",baselineResult:{tests:6,pass:5,fail:1},qualifiedParserResult:{tests:6,pass:6,fail:0},method:"Unchanged native consumer test and implementation; Node registerHooks redirected only existing @red-cup-engineering/jsnode-package-services-section/workspace/pnpm-lockfile import to the SHA512-verified release source."},
 limits:["No dependency graph was installed or mutated.","Focused source qualification does not receive the complete 0.5.0 dependency graph; parent integration must bind the exact release in its manifest/lock and run normal consumer checks.","No source rewrite, new parser, upstream push, package publication or deployment was performed."],
 logs
};
fs.writeFileSync(record,JSON.stringify(receipt,null,2)+"\n");
console.log(JSON.stringify({record,selectedRelease:receipt.selectedRelease,originalOwner:receipt.originalOwner,qualifiedArchives:archives.map(a=>({version:a.version,originalParserBlobMatches:a.originalParserBlobMatches,originalNativeTestBlobMatches:a.originalNativeTestBlobMatches}))},null,2));

