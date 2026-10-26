import json,os,subprocess,hashlib,time,signal,resource,datetime
from pathlib import Path
Q=Path(__file__).parent;assert Q.resolve()==Q
C=Q/'candidate-v3';P=json.loads((Q/'source-proposal-v3.json').read_text())
assert hashlib.sha256((Q/'source-proposal-v3.json').read_bytes()).hexdigest()=='770e0bb3294f2342e22760ae980252adfaf0d1ffbba3fa5560f18265d6c3abdc'
files={x['path']:x for x in P['unchangedPaths']}
for x in P['changedPaths']:files[x['path']]={'path':x['path'],**x['after']}
def guard():
 for rel,row in files.items():
  path=C/rel;assert path.resolve()==path and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],rel
 return len(files)
assert guard()==25
D=Q/'source-native-v4';D.mkdir(mode=0o700);assert D.resolve()==D
for name in ['fixtures','compile-cache']:(D/name).mkdir(mode=0o700)
N='/gnu/store/kba00zrnc1d1cg9bkx0krpvc2sp7wzrh-node-24.18.0/bin/node'
args=[N,'--max-old-space-size=96','--test','--test-concurrency=1','test/config.test.mjs','test/command.test.mjs','test/environment.test.mjs','test/entrypoint.test.mjs','test/owned-data-admission.test.mjs']
def save(name,x):
 p=D/name
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o600)
env={name:os.environ[name] for name in ('HOME','CODEX_HOME') if name in os.environ}
env.update({'PATH':str(Path(N).parent)+':/usr/bin:/bin','TMPDIR':str(D/'fixtures'),'NODE_COMPILE_CACHE':str(D/'compile-cache'),'LANG':'C.UTF-8'})
assert all(env.get(name)==os.environ.get(name) for name in ('HOME','CODEX_HOME'))
save('intent.json',{'kind':'OriginalDirectNodeSourceFamilyAttempt','source':str(C),'sourceProposalSHA256':hashlib.sha256((Q/'source-proposal-v3.json').read_bytes()).hexdigest(),'argv':args,'cwd':str(C),'environmentNames':list(env),'actualHomeAndCodexHomeInheritedUnchanged':True,'inheritedEnvironmentDigests':{name:hashlib.sha256(env[name].encode()).hexdigest() for name in ('HOME','CODEX_HOME') if name in env},'timeoutSeconds':60,'sourceFilesGuarded':25,'expectedTests':62,'scope':'original512MiB source-only fixture/log envelope; no install/graph/network/Guix','at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
proc=None;timed=False;t=time.monotonic()
def childLimits():resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
try:
 with (D/'stdout').open('xb') as out,(D/'stderr').open('xb') as err:
  proc=subprocess.Popen(args,cwd=C,env=env,stdout=out,stderr=err,start_new_session=True,preexec_fn=childLimits)
  save('started.json',{'pid':proc.pid,'processGroup':proc.pid,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  try:code=proc.wait(timeout=60)
  except subprocess.TimeoutExpired:
   timed=True;os.killpg(proc.pid,signal.SIGTERM)
   try:code=proc.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);code=proc.wait(timeout=5)
  out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
 try:os.killpg(proc.pid,0);absent=False
 except ProcessLookupError:absent=True
 assert guard()==25
 result={'kind':'OriginalDirectNodeSourceFamilyResult','code':code,'timedOut':timed,'seconds':time.monotonic()-t,'sourceUnchanged':True,'guardedFiles':25,'processGroupAbsent':absent,'stdoutBytes':(D/'stdout').stat().st_size,'stderrBytes':(D/'stderr').stat().st_size,'stdoutSHA256':hashlib.sha256((D/'stdout').read_bytes()).hexdigest(),'stderrSHA256':hashlib.sha256((D/'stderr').read_bytes()).hexdigest(),'childMaxRSSKiB':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'packageOrInstalledConsumerQualification':False}
 save('result.json',result);print(json.dumps(result));raise SystemExit(0 if code==0 and absent else 1)
except BaseException as e:
 if proc is not None and proc.poll() is None:
  try:os.killpg(proc.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  proc.wait(timeout=5)
 if not(D/'result.json').exists():save('uncertain-terminal.json',{'kind':'SourceFamilyActualFailure','errorType':type(e).__name__,'childMayHaveStarted':proc is not None,'sourceGuardAfter':guard(),'noAutomaticRetry':True})
 raise
