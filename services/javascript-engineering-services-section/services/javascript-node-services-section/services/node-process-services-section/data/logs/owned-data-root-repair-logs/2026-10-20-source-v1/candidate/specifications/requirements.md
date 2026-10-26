# Process data-root requirements

Leader, 2026-10-20: “Additionally, nothing is meant to be stored under ~/.local/, that's a bug we've reported many times, data is meant to be colocated with its services section under data/”. Each services section also has its own properly named repository; Git topology cannot decide whether its data belongs beside it.

`processDataRootConfig` MUST resolve the existing owning `*-services-section` directory immediately above `data/`. The directory MUST be real, canonical and existing. Neither the owner nor its existing `data/` may redirect through a symlink. A `.local` component, `node_modules`, or the immutable `/gnu/store` is not a data owner. This applies equally inside and outside a Git checkout, including a service section that is itself a standalone checkout or worktree.

The resolver MUST preserve the public above-data result and config → environment → argv precedence, relative explicit inputs, absolute cwd-independent defaults, custom flags and config selectors, legacy-input refusal, duplicate/empty-flag refusal, configuration errors, frozen return values and unrelated process helpers. It MUST perform no writes.

An application or installed package identifies executable code, not its runtime data owner. Such a caller MUST select its owning section through its existing config, environment or argv input. The resolver MUST refuse an app/store/node_modules default that remains the selected data root. It MUST NOT guess a section from an executable's ancestors.

This mechanism checks path placement; the trusted caller and deployment configuration remain responsible for selecting the actual service jurisdiction. Each writer MUST separately receive the destination immediately before its effects and file logs/records/state under the owner's typed data tree. Validation here is not a persistent filesystem lock, deployment receipt, repository registration or permission grant.
