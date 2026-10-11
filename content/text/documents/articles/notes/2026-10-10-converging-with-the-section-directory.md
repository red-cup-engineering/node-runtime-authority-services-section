# Converging this repository with the section directory

Dated 2026-10-10. The superrepo directory
`lib/emsenn/services/561-group/services/engineering-services-section/services/computer-engineering-services-section/services/computer-code-engineering-services-section`
is the authoritative layout. This repository is that section, mounted at its
directory, so its layout is the directory's layout relative to the section root.

## Layout

- The section package that lived at `services/computer-code-engineering-services-section/`
  is the repository root (README, `content/`, `src/`, `test/`, `lib/legacy`, `package.json`).
- Every shared package sits at the directory's path relative to the section root.
  The flat `services/<name>/` and the `services/javascript-services-section/...`
  nesting are gone; the JavaScript line lives under
  `services/javascript-engineering-services-section/`.
- Packages only the directory holds were carried at their paths, with their committed
  files (`lib/legacy`, `node_modules` and `dist` excluded).
- `services/computer-code-development-services-section/services/version-control-services-section/services/git-services-section`
  is a gitlink (submodule) of `red-cup-engineering/git-services-section` at its `main`,
  declared in `.gitmodules`; its files are not copied.
- `services/lean-engineering/` holds two unpackaged files and has no directory
  counterpart; it stays where it was.

## Conflict decisions

| Conflict | Decision |
| --- | --- |
| disk-package-observation-app (`src/`, `scripts/`) | Directory code: it uses the consolidated filepath section and the shared argv helper and inlines the type slicing, so the two micro-packages (`path-walking-service`, `file-type-slicing-service`) are no longer needed. |
| disk-package-observation-app `package.json` (waves 1 and 2) | Directory manifest (public, `files`, `publishConfig`, version 0.1.0) plus this repository's `check` and `verify` scripts. Dependencies are the two packages the code imports, as `workspace:*`. |
| javascript-node-services-section `data/records/house-layers.json` | Directory file: newer (2026-10-10), names `lib/signstuff/*` paths that exist, and its provenance text is coherent; this repository's copy named paths that do not exist and had garbled provenance text. |
| npm-package-tree-discovery-service (`package.json`, `src/`, `scripts/`, `test/`) | Directory: the schema is version 2, the script uses the shared argv helper, and the manifest exports and binds the decommissioned-package and replicated-copy modules. Exports and bins were extended so every module and script that exists is addressable. |
| npm-registry-service (`package.json`, `test/registry-graph.test.mjs`) | Directory facade over `npm-registry-graph-services-section` and `npm-registry-snapshot-publication-service`. The old monolith (`src/package-registry.mjs`, `src/registry-graph.mjs`, the four old scripts and `test/package-registry.test.mjs`) was removed: its graph, read-server, receipt-recovery and build capabilities each have one implementation in the successor packages (graph section, read service, semiotic registry section's receipt recovery, snapshot assembly and publication). |
| npm-workspace-publication-service (seven files) | This repository's side. It is a strict superset: it resolves `workspace:*` at publication (`publicationManifest`, `WORKSPACE_SPECIFICATION`, `wearPublishedManifest`) which the directory side lacks. The stale `main` was dropped, the exports now cover every `src/` module, and `recover-demanded-versions` is a bin. `test/dependency-policy.test.mjs` was updated to the policy it tests: a source manifest may name a sibling as `workspace:*`; a published manifest may not. |
| services-section-form-services-section `package.json` | This repository's side: a superset (adds `derive-services-section-path` export and bin) and already `workspace:*`. |
| execute-javascript-node-command-service `package.json` | `jsonl-services-section` is imported only by a test, so it is a `devDependency` (`workspace:*`) only; the duplicate pinned `dependencies` entry the merge added was removed. |

Merged manifests: the directory's extra pinned dependencies that no code imports
(for example in javascript-node-services-section and npm-workspace-publication-service)
were dropped; real ones were kept.

## Packages only this repository held

| Package | Disposition |
| --- | --- |
| registry-drift-observation-app | Folded into the directory's `npm-registry-drift-observation-service` (same capability, same source, stronger CLI). |
| jsnode-package-manifest-normalization-service | Folded into `npm-package-manifest-normalization-service`, which holds `normalizeJsnodePackageManifest` and refuses to invent a version. The one consumer, jsnode-package-body-normalization-app, imports the successor and keeps its own 0.1.0 default for an unversioned package. |
| regenerating-package-lock-service | Folded into `project-npm-package-lock-regeneration-command-service` and `apply-npm-package-lock-regeneration-command` (same `npm install --package-lock-only --ignore-scripts`). |
| programming-language-javascript-services-section (`services/javascript-services-section`) | Folded into `javascript-engineering-services-section`. |
| jsnode-package-body-normalization-app and its atomic services (cross-package-module-edge, body-observation, dependency, identity, identity-reference, owner-projection) | `javascript-normalization-services-section` (app under `apps/`, services under `services/`), the directory's home for normalizing JavaScript packages. |
| jsnode-package-check-service | `javascript-normalization-services-section/services/`, beside the directory's `review-jsnode-package` script. |
| jsnode-package-scaffold-service | `javascript-code-fabrication-services-section/services/javascript-node-code-fabrication-services-section/services/`, beside `jsnode-package-services-section`. |
| npm-registry-a2a-projection-service, package-installation-check-service | `npm-registry-services-section/services/`, where the section README already places them. |

## Other changes

- `solidity-search-path-for-relations` was renamed `search-path-for-relations` to equal its directory basename.
- `project-npm-package-lock-regeneration-command-service` imported a nonexistent relative path into the data section; it imports `@red-cup-engineering/json-services-section` (`freezeJson`) and `@red-cup-engineering/jsonl-services-section` instead.
- Every house dependency the workspace provides is `workspace:*`; registry-only packages (`semver`, `@a2a-js/sdk`, `verdaccio`, `esbuild`, `@red-cup-engineering/feltos`, the a2a and rmn packages) stay pinned.

## Section-level files

Only `package.json` differed outside the packages; this repository's is newer by commit date and is kept.
