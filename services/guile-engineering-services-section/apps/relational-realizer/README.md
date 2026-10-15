# Guile relational realizer — recovered Engineering source

This is a **Guile Scheme implementation**, not a new mathematics program. It preserves two distinct executable source families from the user's 2026 archive in their competent living Code Engineering owner.

## Source families and native entry points

- `source/` — original operational derivation/extraction files, named Scheme modules, and source S-expression foundations. From this directory, `guile -L . -c '(use-modules (derivations)) (display operational-list)'` loads the original module against the original local foundations.
- `modules/ritm/` — the original seven-module relational-topos prototype: `(ritm core)`, `(ritm category)`, `(ritm presheaf)`, `(ritm topology)`, `(ritm modality)`, `(ritm geometry)`, `(ritm analyze)`. The matching Guile module search root is `modules/`: `guile -L modules -c '(use-modules (ritm core) (ritm category))'`.

The original `source/system.scm` blob is **renamed** `source/relational-system.scm` because its declared Guile module is `(relational-system)`. The original `source/derivations.scm` is retained with one source-compatibility correction: export its existing `load-relational-system` function, which the `(relational-system)` consumer calls. No duplicate implementation/wrapper is introduced.

The original `library/toy-package/source/ritm.scm` declares the **same `(ritm core)` module** as `library/toy-package/source/ritm/core.scm` but is an alternative version. The latter is the native, path-conforming source selected for the living module; the former remains recoverable in the original Git archive, **not a second active core**.

## Science/custody boundary

This is historically called *relationality/RITM*. It is exploratory, source-preserved executable Guile Engineering, not independent proof of current Obsmetrologia theory. Mathematical conformance and any later equivalence to SignCell/Obsmetrologia are determined by Lenticule Science, not by filename or successful source import. The rest of the pre-existing Code Engineering repository is untouched.

Original source: `emsenn/emsenn-archive-code@3c69d5cf9d3bec484f1dc22067ed9623b1bab7c6:topical/science/mathematics/predication-categories/guile-relational-realizer/`. The six `source/` files and seven `ritm/` modules were compared by Git blob identity before promotion. The original archive and the deep historical Engineering snapshot remain intact as provenance. No test, runtime receiving, or deployment is implied.
