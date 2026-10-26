#!/usr/bin/env node
import {readFile,writeFile} from 'node:fs/promises';
import {produceRegistryRuntime} from '../src/produce-registry-runtime.mjs';
const [consumerPath,receivingFile,destination,receiptPath,mode,...extra]=process.argv.slice(2);
if(!consumerPath||!receivingFile||!destination||!receiptPath||extra.length||(mode!==undefined&&mode!=='--transfer-installation'))throw new TypeError('expected consumer, frozen receiving receipt, runtime destination and result receipt');
const receiving=JSON.parse(await readFile(receivingFile,'utf8'));
const receipt=await produceRegistryRuntime({consumerPath,receiving,destination,transferInstallation:mode==='--transfer-installation'});
await writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
