# Elisp services section

Holds Emacs Lisp material: personal Emacs configuration and package
declarations, small utility packages (`ems-dict`, `ems-fortunes`,
`ems-inventory`, `ems-library`, `ems-profile`, `ems-projects`, `ems-ros`),
an old `suros`/`saros` HTTP server prototype and its Mustache templates, and
a dated proposal for a "data asset manifest" format. Everything under
`lib/legacy` is archived as-is from earlier snapshots of this material and
is kept for reference rather than active development.

The [gnoponemacs package declarations](data/records/emacs-package-records/gnoponemacs.json)
retain the 63 upstream package descriptors and both native startup package selections
from the VPS snapshot. Native Emacs package management can reconstruct those
dependencies; their downloaded distributions and generated quickstart files are
retired from the Group legacy intake. The snapshot contained no Group startup
configuration source. User history, places, auto-save session and package trust
data remain separately held, and an active Emacs consumer has not been verified.
The accompanying [native package selection](data/records/emacs-package-records/gnoponemacs.el)
loads through Emacs `package.el`: it selects the 64 recorded dependencies without
installing them. GNU Emacs batch receiving loaded it and read all 64 selections.
