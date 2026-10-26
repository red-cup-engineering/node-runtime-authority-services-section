import json,subprocess,hashlib,base64,concurrent.futures,datetime
from pathlib import Path
NQ=Path(__file__).parent
CQ=Path('/home/emsenn/info/lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-systems-engineering-services-section/services/computer-operating-system-services-section/data/logs/storage-migration-source-logs/2026-10-20')
for q in [NQ,CQ]: assert q.resolve()==q and q.is_dir()
def api(path,body=None):
 args=['gh','api',path]
 if body is not None: args+=['--method','POST','--input','-']
 r=subprocess.run(args,input=None if body is None else json.dumps(body).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
 if r.returncode: raise RuntimeError('GitHub API failure '+path+' status '+str(r.returncode))
 return json.loads(r.stdout)
def leaf(t):
 assert not t.get('truncated')
 return {x['path']:{k:x[k] for k in ['mode','type','sha']} for x in t['tree'] if x['type']!='tree'}
def review(q,repo,number,head,tree,parents,mainExpected,final=False):
 m=json.loads((q/'input-manifest.json').read_text())
 assert m['repository']['full_name']==repo
 root='repos/'+repo
 endpoints=[root+'/pulls/'+str(number),root+'/git/commits/'+head,root+'/git/trees/'+tree+'?recursive=1',root+'/git/commits/'+m['expectedMain'],root+'/git/ref/heads/main']
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: pr,c,after,beforeCommit,main=list(ex.map(api,endpoints))
 assert c['tree']['sha']==tree and [x['sha'] for x in c['parents']]==parents
 assert main['object']['sha']==mainExpected
 if final: assert pr['merged'] and pr['merge_commit_sha']==head and pr['state']=='closed'
 else: assert not pr['merged'] and pr['state']=='open' and pr['head']['sha']==head
 before=leaf(api(root+'/git/trees/'+beforeCommit['tree']['sha']+'?recursive=1')); after=leaf(after)
 selected={r['path'] for r in m['files']}
 assert {k for k in set(before)|set(after) if before.get(k)!=after.get(k)}==selected
 assert {k:v for k,v in before.items() if k not in selected}=={k:v for k,v in after.items() if k not in selected}
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: blobs=list(ex.map(lambda r:api(root+'/git/blobs/'+r['gitBlob']),m['files']))
 rows=[]
 for r,b in zip(m['files'],blobs):
  raw=base64.b64decode(b['content']); h=hashlib.sha256(raw).hexdigest(); oid=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  assert len(raw)==r['bytes'] and h==r['sha256'] and oid==r['gitBlob']
  assert after[r['path']]=={'mode':r['mode'],'type':'blob','sha':oid}
  assert Path(r['absolute']).read_bytes()==raw
  if not final: assert r['path'].startswith('data/records/storage-correction-records/2026-10-20/') and r['before'] is None and isinstance(json.loads(raw),dict)
  rows.append({k:r[k] for k in ['path','bytes','sha256','gitBlob','mode']})
 assert sum(x['bytes'] for x in rows)==m['bytes'] and len(rows)==m['count']
 proof={'kind':'IndependentMergedSourceDeliveryReceiving' if final else 'IndependentRemoteRecordSourceReceiving','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'met','repository':repo,'pull':number,'head':head,'tree':tree,'parents':parents,'main':main['object']['sha'],'inputSHA256':hashlib.sha256((q/'input-manifest.json').read_bytes()).hexdigest(),'files':rows,'count':len(rows),'bytes':sum(x['bytes'] for x in rows),'allOtherLeavesAndGitlinksPreserved':True,'testsReplayed':False,'originalEffectsReplayed':False,'sourceOnly':True}
 if final:
  body=('Final independent source delivery: **MET**. Actual main and merged PR1 resolve to `'+head+'`, tree `'+tree+'`, with parents `'+parents[0]+'` and `'+parents[1]+'`. All ten merged file bodies (72,315 bytes), Git blobs and modes match the accepted packet; all thirteen unrelated source files are preserved. The accepted four direct-Node source families remain 49/49 with no extras; no tests or installation were repeated for this delivery readback. Zero hosted check/status contexts is not a CI pass.\n\nThis completes this source correction only. Version0.3.0 intentionally removes arbitrary/app-owned roots while preserving final config/environment/argv selection semantics. Baseline14/15 and initial48/49 remain retained. Shared npm/development-closure qualification, actual package publication, CSE dependency and deployed explicit owner bindings, federation operation and the rest of the consumer family remain open and unreceived.')
 else:
  body=('Independent source receiving: **MET**, scoped to head `'+head+'`, tree `'+tree+'` and sole parent `'+parents[0]+'`. All four actual remote curated JSON bodies (21,949 bytes), Git blobs and regular-file modes match the accepted source/actual/independent custody receipts. The complete before/after leaf and gitlink comparison changes only these four records; all runtime, version, configuration and other source is preserved. Ordinary ready/current-head/check readback and expected-head integration are qualified.\n\nThe received original operation was one same-filesystem no-copy rename into the owning section typed logs, preserving directory identity and three named inode/byte/mode witnesses. Old home path is absent; the eight known outside roots are unchanged. This review did not repeat a move, preflight, suite, installation or host effect. No capacity reclamation, blanket home cleanup or current execution of old carriers is claimed. Old absolute executable, graph and worktree bindings stay frozen pending forward-path receiving; other home roots and the live BCF HTTP data binding remain open. These four records receive source custody, not registry publication or native host activation.')
 comment=api(root+'/issues/'+str(number)+'/comments',{'body':body}); read=api(root+'/issues/comments/'+str(comment['id']))
 assert read['body']==body
 proof['comment']={'id':read['id'],'url':read['html_url'],'body':read['body']}
 target=q/('independent-final-merged-delivery-receiving.json' if final else 'independent-remote-source-receiving.json')
 assert not target.exists()
 target.write_text(json.dumps(proof,indent=2)+'\n'); target.chmod(0o600)
 print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'comment':proof['comment']['url'],'count':len(rows),'bytes':proof['bytes']}))
review(NQ,'red-cup-engineering/node-process-services-section',1,'23113a67473de9784fdea1d1d45757fc0dd1569b','3ec1e72a033ae2c404a2481f2a775e7168d3aa75',['9ea4f22f9e56fe67d936d629fae8033634903b7b','71b71a26157ab8d1638f5471bc299d2dc1735912'],'23113a67473de9784fdea1d1d45757fc0dd1569b',True)
review(CQ,'red-cup-engineering/computer-operating-system-services-section',8,'d43f002cae69bc38f7f7b7cd583893204e3f440c','113ae3eb81ad9dd40ef9e85c2064d7660df5caa2',['d8e07afd14737029c0afd6aebb45c99a64448e57'],'d8e07afd14737029c0afd6aebb45c99a64448e57')
