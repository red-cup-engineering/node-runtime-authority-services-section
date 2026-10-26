import argparse,difflib,hashlib,json,pathlib,subprocess,stat
R=pathlib.Path(__file__).resolve().parent
C=pathlib.Path('/var/tmp/engineering-abandoned-prs-20261020/packaging-github-intake/code23-source-bc494ee673f59fcdccc939a6102ae089fac1658b')
G='/var/tmp/engineering-abandoned-prs-20261020/packaging-github-intake/code23-git-bc494ee673f59fcdccc939a6102ae089fac1658b/0.git'
BASE='bc494ee673f59fcdccc939a6102ae089fac1658b'
a=argparse.ArgumentParser();a.add_argument('--label',required=True);a.add_argument('--manifest-sha256',required=True);a.add_argument('--lock-sha256',required=True);args=a.parse_args()
assert args.label.replace('-','').replace('.','').isalnum()
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((C/'package.json').read_bytes())==args.manifest_sha256
assert sha((C/'pnpm-lock.yaml').read_bytes())==args.lock_sha256
base=subprocess.check_output(['git','--git-dir='+G,'ls-tree','-r','--name-only',BASE],timeout=10).decode().splitlines()
selected={pathlib.Path(x['path']).relative_to(C).as_posix() for x in json.loads((R/'native-installed-source-guards.json').read_text())}
assert set(base)<=selected and len(selected)<=180
snapshots={}
for path in sorted(selected):
 p=C/path;s=p.lstat();assert stat.S_ISREG(s.st_mode)
 data=p.read_bytes();assert len(data)<=2**20
 snapshots[path]=(data,s.st_mode&0o777)
assert sum(len(x[0]) for x in snapshots.values())<=4*2**20
patch=[];changed=[]
for path,(data,mode) in snapshots.items():
 old=subprocess.check_output(['git','--git-dir='+G,'show',BASE+':'+path],stderr=subprocess.DEVNULL,timeout=10) if path in base else b''
 if data==old:continue
 patch.extend(difflib.unified_diff(old.decode().splitlines(True),data.decode().splitlines(True),fromfile='a/'+path if path in base else '/dev/null',tofile='b/'+path))
 changed.append({'path':path,'sha256':sha(data),'bytes':len(data),'mode':mode,'baseSHA256':sha(old) if path in base else None})
for path,(data,mode) in snapshots.items():assert (C/path).read_bytes()==data and ((C/path).lstat().st_mode&0o777)==mode
out=R/args.label;out.mkdir(mode=0o700)
for x in changed:
 p=out/x['path'];p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_bytes(snapshots[x['path']][0]);p.chmod(x['mode'])
b=''.join(patch).encode();pp=R/(args.label+'.patch')
with pp.open('xb') as f:f.write(b)
descriptor={'kind':'CodeNativeArtifactReceivingSourceProposal','base':BASE,'source':str(C),'frozenChangedSource':str(out),'patch':str(pp),'patchSHA256':sha(b),'patchBytes':len(b),'manifestSHA256':args.manifest_sha256,'lockSHA256':args.lock_sha256,'changedFiles':changed,'selectedSourceFiles':[{'path':p,'sha256':sha(d),'bytes':len(d),'mode':m} for p,(d,m) in snapshots.items()],'scope':'Combined Code13 and Code22 owner correction; source proposal, not publication or operating proof'}
p=R/(args.label+'.json')
with p.open('x') as f:json.dump(descriptor,f,indent=2);f.write('\n')
print(json.dumps({'descriptor':str(p),'descriptorSHA256':sha(p.read_bytes()),'patchSHA256':sha(b),'changedFiles':len(changed),'patchBytes':len(b)}))
