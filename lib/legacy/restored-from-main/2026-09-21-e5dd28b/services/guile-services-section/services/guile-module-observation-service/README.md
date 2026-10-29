# Guile module observation service

This service asks Guile itself to read Guile and Guix source, then returns a
bounded module observation: the declared module name, used modules, exported
bindings, source path, byte length, and SHA-256 digest.

It does not evaluate the source. JavaScript does not parse Scheme. DREW remains
downstream: its existing `guixModuleClaims` adapter projects these witnessed
domain records into the shared relation web.

The runtime uses `guix repl`, which supplies Guile, the `(json)` module, and
Guix's `#~` / `#$` g-expression reader extensions. `observeGuileModuleSource`
accepts explicit source bytes; `observeGuileModuleFile` is the filesystem face.
