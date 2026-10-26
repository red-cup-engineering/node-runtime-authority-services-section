import assert from "node:assert/strict";
import test from "node:test";
import { openSync,closeSync,readFileSync,mkdtempSync,rmSync,fstatSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { executeJavascriptNodeCommand } from "../scripts/execute-javascript-node-command.mjs";

const command = (directory,program) => ({
  type:"JavascriptNodeCommandExecutionRequest",version:1,command:process.execPath,
  arguments:["-e",program],directory,environment:null,input:null,
});
test("private policy inherits fd3 without closing its parent descriptor or adding invocation fields",t=>{
  const root=mkdtempSync(join(tmpdir(),"command-fd-")); t.after(()=>rmSync(root,{recursive:true,force:true}));
  const path=join(root,"owned"),fd=openSync(path,"w+");
  try{
    const request=command(root,"require('node:fs').writeSync(3,'inherited'); process.stdout.write('out');");
    const receipt=executeJavascriptNodeCommand(request,{timeoutMilliseconds:1000,maximumOutputBytes:4096,inheritedFileDescriptors:[fd]});
    assert.equal(receipt.result.status,0,receipt.result.error);
    assert.equal(receipt.result.stdout,"out"); assert.equal(fstatSync(fd).isFile(),true); assert.equal(readFileSync(path,"utf8"),"inherited");
    assert.deepEqual(receipt.request,request); assert.equal(JSON.stringify(receipt).includes("inheritedFileDescriptors"),false);
  }finally{closeSync(fd);}
});
test("finite private output and time allocation produce unsuccessful complete receipts",()=>{
  const limited=executeJavascriptNodeCommand(command(tmpdir(),"process.stdout.write('x'.repeat(100000));"),
    {maximumOutputBytes:64,timeoutMilliseconds:1000});
  assert.notEqual(limited.result.error,"");
  const timed=executeJavascriptNodeCommand(command(tmpdir(),"setTimeout(()=>{},10000);"),{timeoutMilliseconds:20,maximumOutputBytes:64});
  assert.notEqual(timed.result.error,"");
});
test("invalid private policies refuse before spawning",()=>{
  for(const policy of [null,[],{timeoutMilliseconds:0},{maximumOutputBytes:Infinity},
    {maximumOutputBytes:0},{inheritedFileDescriptors:[-1]},{inheritedFileDescriptors:[undefined]},
    {inheritedFileDescriptors:[,]},{inheritedFileDescriptors:"3"},{stdio:"inherit"}])
    assert.throws(()=>executeJavascriptNodeCommand(command(tmpdir(),"throw Error('must not execute');"),policy),TypeError);
});
