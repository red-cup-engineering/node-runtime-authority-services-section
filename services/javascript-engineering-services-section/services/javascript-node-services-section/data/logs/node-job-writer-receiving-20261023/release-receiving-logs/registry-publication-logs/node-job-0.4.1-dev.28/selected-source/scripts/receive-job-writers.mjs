#!/usr/bin/env node
/** One private source-bound selection; observe only, never invoke a job. */
import {constants,openSync,closeSync,fstatSync,readSync,realpathSync} from 'node:fs';
import {isAbsolute,resolve} from 'node:path';
import {receiveNodeJobWriters} from '../src/selected-job-writer-receiving.mjs';
let fd;
try {
 if(process.argv.length!==3)throw Error('input-required');
 const file=process.argv[2];if(!isAbsolute(file)||resolve(file)!==file||realpathSync(file)!==file)throw Error('private-input-required');
 fd=openSync(file,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);const st=fstatSync(fd);
 if(!st.isFile()||st.uid!==process.getuid()||(st.mode&0o077)||st.size>131072)throw Error('private-input-required');
 const chunks=[];let total=0;for(;;){const chunk=Buffer.allocUnsafe(Math.min(65536,131073-total)),n=readSync(fd,chunk,0,chunk.length,null);if(!n)break;total+=n;if(total>131072)throw Error('input-byte-budget');chunks.push(chunk.subarray(0,n));}
 const after=fstatSync(fd);if(st.dev!==after.dev||st.ino!==after.ino||st.size!==after.size||st.mtimeMs!==after.mtimeMs||st.ctimeMs!==after.ctimeMs)throw Error('input-changed');
 const bytes=Buffer.concat(chunks,total);
 const input=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 console.log(JSON.stringify(receiveNodeJobWriters(input)));
} catch(error) {
 const allowed=new Set(['source-digest-required','source-changed','redirected-path','installed-selection-required','finite-declarations-required','declaration-selection-mismatch','incomplete-declaration-selection','producer-binding-required','producer-resolution-changed','producer-version-changed','native-provider-required','linux-provider-required','invalid-allocation','native-boot-required']);
 console.log(JSON.stringify({type:'SelectedNodeJobWriterReceivingRefused',reason:allowed.has(error.code)?error.code:'selected-reading-unavailable'}));process.exitCode=1;
} finally {if(fd!==undefined)closeSync(fd);}
