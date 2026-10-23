;;; gnoponemacs.el --- historical native Emacs package selection -*- lexical-binding: t; -*-

;; Recovered from the 2026-08-17 VPS snapshot. This declaration selects
;; dependencies for native package.el; it neither installs nor activates them.
;; Exact upstream descriptors and source identity: gnoponemacs.json.

(setq package-selected-packages
      '(macaulay2 yasnippet yasnippet-snippets yaml-mode yaml compat cond-let with-editor
        vertico typescript-mode treesit-auto treepy llama transient s dash
        f shrink-path rust-mode restclient popper password-store paredit orderless
        no-littering magit-section nix-mode nerd-icons nerd-icons-dired nerd-icons-completion multiple-cursors modus-themes
        markdown-mode markdown-toc marginalia magit json-snatcher json-mode jq-mode inheritenv
        elisp-refs helpful gptel ghub emacsql closql forge expand-region
        envrc embark consult embark-consult eat doom-modeline dockerfile-mode diminish
        diff-hl dape corfu consult-dir cape avy apheleia ace-window))

(provide 'gnoponemacs-package-selection)
