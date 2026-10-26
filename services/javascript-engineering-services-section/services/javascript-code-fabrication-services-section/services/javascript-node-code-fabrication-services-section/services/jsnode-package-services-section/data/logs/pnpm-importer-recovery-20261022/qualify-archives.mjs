import fs from "node:fs";
import crypto from "node:crypto";
import path from "node:path";
import {spawnSync} from "node:child_process";
const root=path.dirname(new URL(import.meta.url).pathname);
const metadata=JSON.parse(fs.readFileSync(path.join(root,"registry-metadata.json")));
const receipts=[];
for(const version of ["0.2.4","0.2.5-dev.615","0.3.0","0.5.0"]){
 const published=metadata.versions[version];
 const response=await fetch(published.dist.tarball);
 if(!response.ok)throw new Error(String(response.status));
 const archive=Buffer.from(await response.arrayBuffer());
 const integrity="sha512-"+crypto.createHash("sha512").update(archive).digest("base64");
 if(integrity!==published.dist.integrity)throw new Error("integrity mismatch "+version);
 const target=path.join(root,version);fs.mkdirSync(target,{recursive:true});
 const archivePath=path.join(target,"release.tgz");fs.writeFileSync(archivePath,archive);
 const list=spawnSync("tar",["-tzf",archivePath],{encoding:"utf8"});
 if(list.status)throw new Error(list.stderr);
 const selected=list.stdout.trim().split("\n").filter(name=>[
 "package/package.json","package/src/workspace/pnpm-lockfile.mjs","package/test/pnpm-lockfile-importers.test.mjs"
 ].includes(name));
 const extract=spawnSync("tar",["-xzf",archivePath,"-C",target,...selected],{encoding:"utf8"});
 if(extract.status)throw new Error(extract.stderr);
 receipts.push({version,gitHead:published.gitHead??null,tarball:published.dist.tarball,integrity,bytes:archive.length,extracted:selected});
}
fs.writeFileSync(path.join(root,"qualified-archives.json"),JSON.stringify(receipts,null,2)+"\n");
console.log(JSON.stringify(receipts,null,2));

