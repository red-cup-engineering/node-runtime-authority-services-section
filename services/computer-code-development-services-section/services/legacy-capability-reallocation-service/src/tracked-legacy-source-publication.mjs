import {resolve} from 'node:path';

const makerName = '@red-cup-engineering/computer-systems-fabrication-engineering-services-section';

async function sourceReader() {
  const codec = await import('@red-cup-engineering/git-source-reading-service/git-command-codec');
  // Qualified internal supplier boundary: resolve the selected public maker,
  // then reuse its own sibling reader without copying its transport.
  const maker = import.meta.resolve(makerName + '/git/github-candidate');
  return {...codec, ...await import(new URL('./git-objects.mjs', maker).href)};
}

/** Capture fresh record destinations through the selected source reader. */
export async function prepareTrackedLegacyRecordSource({repositoryRoot, paths}) {
  const root = resolve(repositoryRoot);
  const {gitCommitPathsPlan, gitSync, entryAtSync, withSourceReadTransportSync} = await sourceReader();
  const plan = gitCommitPathsPlan.originBranchHead('main');
  const advertised = String(gitSync(root, plan.arguments, {input:plan.input, env:plan.environment})).trim();
  const match = /^([a-f0-9]{40})\s+refs\/heads\/main$/u.exec(advertised);
  if (!match) throw new TypeError('record preparation requires one advertised immutable origin/main');
  const reviewedSource = {revision:match[1], entries:paths.map(path => ({path, absent:true}))};
  await readTrackedLegacySourcePublicationRequest({paths, reviewedSource});
  withSourceReadTransportSync(root, [match[1]], source => {
    for (const path of paths) {
      if (entryAtSync(source, match[1], path) !== null) throw new TypeError('fresh batch record already exists at source: ' + path);
    }
  });
  return reviewedSource;
}

/** Use the publisher's canonical request contract before local effects. */
export async function readTrackedLegacySourcePublicationRequest({paths, reviewedSource}) {
  const {readGitCommitPathsRequest} = await import('@red-cup-engineering/git-source-reading-service/git-command-codec');
  return readGitCommitPathsRequest({
    paths, message: 'Retire reviewed Git-preserved legacy capabilities', push: true, reviewedSource
  });
}

/** Qualify only original remote metadata before local retirement effects.
 * The plan's local review identity is not asserted to exist at origin. */
export async function prepareTrackedLegacySourcePublication({result, previousPublication}) {
  if (result?.kind !== 'legacy-capability-retirement-result/v1' || result.apply !== false) throw new TypeError('source preparation requires the read-only retirement result');
  const root = resolve(result.repositoryRoot);
  const entries = result.outcomes.filter(row => ['eligible', 'absent'].includes(row.state))
    .map(row => ({path: (result.sourceLegacyRoot ?? result.legacyRoot) + '/' + row.path, mode: row.mode, type: row.type, sha: row.blob}));
  if (!entries.length) return undefined;
  const paths = entries.map(row => row.path);
  if (previousPublication?.candidate) {
    if (previousPublication.root !== root || JSON.stringify([...previousPublication.paths].sort()) !== JSON.stringify([...paths].sort())) throw new TypeError('retained source publication differs from this retirement cut');
    // The original candidate owns its existing lease and receiving obligations.
    // Its selected paths may already be absent remotely; never replace it.
    return undefined;
  }
  const {gitCommitPathsPlan, gitRepositoryObservationPlan, gitSync, entryAtSync, withSourceReadTransportSync} = await sourceReader();
  const read = plan => String(gitSync(root, plan.arguments, {input: plan.input, env: plan.environment})).trim();
  const origin = read(gitRepositoryObservationPlan.remoteUrl('origin'));
  const advertised = read(gitCommitPathsPlan.originBranchHead('main'));
  const match = /^([a-f0-9]{40})\s+refs\/heads\/main$/u.exec(advertised);
  if (!match) throw new TypeError('source preparation requires one advertised immutable origin/main');
  const revision = match[1];
  const request = await readTrackedLegacySourcePublicationRequest({paths, reviewedSource: {revision, entries}});
  withSourceReadTransportSync(root, [revision], source => {
    for (const entry of entries) {
      const actual = entryAtSync(source, revision, entry.path);
      if (!actual || actual.mode !== entry.mode || actual.type !== entry.type || actual.object !== entry.sha) throw new TypeError('source preimage differs: ' + entry.path);
    }
  });
  return {
    kind: 'legacy-retirement-source-preparation/v1',
    repositoryRoot: root, legacyRoot: result.legacyRoot,
    ...(result.sourceLegacyRoot === undefined ? {} : {sourceLegacyRoot:result.sourceLegacyRoot}),
    planRevision: result.revision, origin, ref: 'refs/heads/main',
    reviewedSource: request.reviewedSource
  };
}

/** Keep the original lease and identity when narrowing to actually retired paths. */
export async function reviewedSourceForTrackedLegacyRetirement(result, selected) {
  const prepared = result.sourcePreparation;
  if (prepared?.kind !== 'legacy-retirement-source-preparation/v1' || prepared.repositoryRoot !== resolve(result.repositoryRoot)
      || prepared.legacyRoot !== result.legacyRoot || prepared.planRevision !== result.revision
      || (prepared.sourceLegacyRoot ?? prepared.legacyRoot) !== (result.sourceLegacyRoot ?? result.legacyRoot)
      || !/^[a-f0-9]{40}$/u.test(prepared.reviewedSource?.revision ?? '') || !Array.isArray(prepared.reviewedSource.entries))
    throw new TypeError('qualified remote source preparation required before retirement publication');
  const {gitSync, gitRepositoryObservationPlan} = await sourceReader();
  const plan = gitRepositoryObservationPlan.remoteUrl('origin');
  const origin = String(gitSync(prepared.repositoryRoot, plan.arguments, {input: plan.input, env: plan.environment})).trim();
  if (origin !== prepared.origin) throw new TypeError('original source origin changed after retirement preparation');
  const qualified = new Map(prepared.reviewedSource.entries.map(entry => [entry.path, entry]));
  const entries = selected.map(row => {
    const path = (result.sourceLegacyRoot ?? result.legacyRoot) + '/' + row.path, entry = qualified.get(path);
    if (!entry || entry.mode !== row.mode || entry.type !== row.type || entry.sha !== row.blob)
      throw new TypeError('prepared source preimage differs from retirement: ' + path);
    return entry;
  });
  return {revision: prepared.reviewedSource.revision, entries};
}
