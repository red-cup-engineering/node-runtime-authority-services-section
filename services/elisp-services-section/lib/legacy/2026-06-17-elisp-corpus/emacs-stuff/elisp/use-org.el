(use-package org
  :mode (("\\.org$" . org-mode) ("\\.inc$" . org-mode))
  :ensure org-plus-contrib

:bind (("C-c l" . org-store-link)
       ("C-c c" . org-capture)
       ("C-c a" . org-agenda)
       ("C-c b" . org-iswitchb)
       ("C-c C-w" . org-refile)
       ("C-c j" . org-clock-goto)
       ("C-c C-x C-o" . org-clock-out))

:config
(progn

(setq org-log-done t)
(setq org-log-into-drawer "LOGBOOK")

(setq org-image-actual-width nil)

(setq org-hide-emphasis-markers t)

(setq org-ellipsis "→")

(set-face-attribute 'org-level-1 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-2 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-3 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-4 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-5 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-6 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-7 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-8 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-document-title nil :height 140 :family "IBM Plex Sans")

;;  (add-hook 'text-mode-hook
;;            (lambda ()
;;              (variable-pitch-mode 1)))

(add-hook 'org-mode-hook
'visual-line-mode)

(setq org-agenda-custom-commands
      '(("A" "Agenda and TODO"
         ((agenda "" )
          (alltodo "" )))))
(setq org-agenda-todo-ignore-scheduled 'all)
(setq org-agenda-files '("~/org/personal/src/index.org"))

(setq org-link-abbrev-alist '(
                              ("ems-domestic-manual" . "file:~/org/src/domestic-manual.org::#%s")))

(setq org-export-allow-bind-keywords t)
(setq org-export-with-sub-superscripts nil)
(setq org-export-with-special-strings nil)
(setq org-export-with-smart-quotes nil)
(setq org-export-with-section-numbers nil)
(setq org-export-with-toc nil)
(setq org-export-with-todo-keywords nil)
(setq org-export-headline-levels 10)
(setq org-html-style-default nil)

(setq org-todo-keywords
'((sequence "DRAFT" "EDIT" "|" "DONE")
  (sequence "|" "CANCELED")))

(setq org-capture-templates
      '(("s" "New Source File" plain (file "~/org/triage/source-capture.org")
	 "#+SETUPFILE: ~/org/templates/setupfile0.org\n#+TITLE: %^{TITLE}\n#+EXPORT_FILE_NAME: ../pub/%^{SLUG}\n* Introduction\n%?\n#+INCLUDE: \"./eli.org::#draft\"\n#+INCLUDE: \"./eli.org::#eli\"\n* %\\1\n  :PROPERTIES:\n  :CUSTOM_ID: contents\n  :END:\n* Supplements\n#+INCLUDE: \"./mit-license.org::#license\"")
	("l" "New Log Entry" entry (file+olp+datetime "~/org/personal.org" ["Logs"])
	 ""
	 )
	("a" "Activity" item (file+datetree "~/org/projects/personal-data/activities.org")
	 "%U :: %?")
        ("b" "Bibliography" entry (file+olp "~/org/projects/emacs-configuration/source.org" "Emacs Configuration" "Packages" "Org-mode" "Macros" "Bibliography Macros")
         "* %^{TITLE}\n#+begin_src elisp\n(\"%^{SLUG}-title\" . \"%\\1\")\n(\"%\\2-author\" . \"%^{AUTHOR}\")\n(\"%\\2-source\" . \"%^{SOURCE}\")\n(\"%\\2-opinion\" . \"%^{OPINION}\")\n#+end_src")))

(setq org-publish-project-alist
      '(
        ("state-of-iranian-communication"
         :base-directory "~/org/projects/state-of-iranian-communication/src/"
         :base-extension "org"
         :publishing-directory "~/org/projects/state-of-iranian-communication/"
         :publishing-function (org-html-publish-to-html org-latex-export-to-pdf org-org-export-to-org)
         )
        ("personal-dictionary"
         :base-directory "~/org/projects/personal-dictionary/"
         :base-extension ""
         :include "source.org"
         :makeindex t
         :publishing-directory "~/org/projects/personal-dictionary/"
         :publishing-function (org-html-publish-to-html)
         )
        ("30-days-of-world-building-summer-2019"
         :base-directory "~/org/projects/30-days-of-world-building-summer-2019/src/"
         :base-extension "org"
         :publishing-directory "~/org/projects/30-days-of-world-building-summer-2019/"
         :publishing-function org-html-publish-to-html)
        ("public-html"
         :base-directory "~/"
         :base-extension "org"
         :recursive t
         :exclude "pr.org"
         :makeindex t
         :auto-sitemap t
         :publishing-directory "~/public-html/"
         :publishing-function (org-html-publish-to-html))))

(setq org-export-global-macros
      '(

("source" .
 "(eval (concat \"See [[\"(ems-read-dict-source \"$1\") \"]].\"))")
("define" .
 "(eval (ems-read-dict-definition $1))")
("Define" .
 "(eval (ems-cap-first-char (ems-read-dict-definition $1)))")
("ref" .
 "{{{Define($1)}}} {{{source($1)}}}")

("document-type" .
 "document")
("doc" .
 "{{{document-type}}}")
("document-eli" .
 "(eval (ems-build-document-eli $1))")

("bow-character-template" .
 "(eval (ems-bow-build-character-template $1))")
("bow-adventure-brief" . "*/{{{title}}}/* is a /tabletop role-playing *{{{doc}}}*/ in which {{{property(adventure-inwhich)}}}, usually taking between {{{property(adventure-length)}}} to complete.")))

(org-babel-do-load-languages
 'org-babel-load-languages
 '((crystal . t)
   (ledger . t)
   (shell . t)))))

(use-package org
  :mode (("\\.org$" . org-mode) ("\\.inc$" . org-mode))
  :ensure org-plus-contrib
:bind (("C-c l" . org-store-link)
       ("C-c c" . org-capture)
       ("C-c a" . org-agenda)
       ("C-c b" . org-iswitchb)
       ("C-c C-w" . org-refile)
       ("C-c j" . org-clock-goto)
       ("C-c C-x C-o" . org-clock-out))
:config
(progn
(setq org-log-done t)
(setq org-log-into-drawer "LOGBOOK")
(setq org-image-actual-width nil)
(setq org-hide-emphasis-markers t)
(setq org-ellipsis "→")
(set-face-attribute 'org-level-1 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-2 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-3 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-4 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-5 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-6 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-7 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-level-8 nil :height 140 :family "IBM Plex Sans")
(set-face-attribute 'org-document-title nil :height 140 :family "IBM Plex Sans")

(add-hook 'org-mode-hook
'visual-line-mode)
(setq org-agenda-custom-commands
      '(("A" "Agenda and TODO"
         ((agenda "" )
          (alltodo "" )))))
(setq org-agenda-todo-ignore-scheduled 'all)
(setq org-agenda-files '("~/org/personal/src/index.org"))

(setq org-link-abbrev-alist '(
                              ("ems-domestic-manual" . "file:~/org/src/domestic-manual.org::#%s")))
(setq org-export-allow-bind-keywords t)
(setq org-export-with-sub-superscripts nil)
(setq org-export-with-special-strings nil)
(setq org-export-with-smart-quotes nil)
(setq org-export-with-section-numbers nil)
(setq org-export-with-toc nil)
(setq org-export-with-todo-keywords nil)
(setq org-export-headline-levels 10)
(setq org-html-style-default nil)

(setq org-todo-keywords
'((sequence "DRAFT" "EDIT" "|" "DONE")
  (sequence "|" "CANCELED")))

(setq org-capture-templates
      '(("s" "New Source File" plain (file "~/org/triage/source-capture.org")
	 "#+SETUPFILE: ~/org/templates/setupfile0.org\n#+TITLE: %^{TITLE}\n#+EXPORT_FILE_NAME: ../pub/%^{SLUG}\n* Introduction\n%?\n#+INCLUDE: \"./eli.org::#draft\"\n#+INCLUDE: \"./eli.org::#eli\"\n* %\\1\n  :PROPERTIES:\n  :CUSTOM_ID: contents\n  :END:\n* Supplements\n#+INCLUDE: \"./mit-license.org::#license\"")
	("l" "New Log Entry" entry (file+olp+datetime "~/org/personal.org" ["Logs"])
	 ""
	 )
	("a" "Activity" item (file+datetree "~/org/projects/personal-data/activities.org")
	 "%U :: %?")
        ("b" "Bibliography" entry (file+olp "~/org/projects/emacs-configuration/source.org" "Emacs Configuration" "Packages" "Org-mode" "Macros" "Bibliography Macros")
         "* %^{TITLE}\n#+begin_src elisp\n(\"%^{SLUG}-title\" . \"%\\1\")\n(\"%\\2-author\" . \"%^{AUTHOR}\")\n(\"%\\2-source\" . \"%^{SOURCE}\")\n(\"%\\2-opinion\" . \"%^{OPINION}\")\n#+end_src")))

(setq org-publish-project-alist
      '(
        ("state-of-iranian-communication"
         :base-directory "~/org/projects/state-of-iranian-communication/src/"
         :base-extension "org"
         :publishing-directory "~/org/projects/state-of-iranian-communication/"
         :publishing-function (org-html-publish-to-html org-latex-export-to-pdf org-org-export-to-org)
         )
        ("personal-dictionary"
         :base-directory "~/org/projects/personal-dictionary/"
         :base-extension ""
         :include "source.org"
         :makeindex t
         :publishing-directory "~/org/projects/personal-dictionary/"
         :publishing-function (org-html-publish-to-html)
         )
        ("30-days-of-world-building-summer-2019"
         :base-directory "~/org/projects/30-days-of-world-building-summer-2019/src/"
         :base-extension "org"
         :publishing-directory "~/org/projects/30-days-of-world-building-summer-2019/"
         :publishing-function org-html-publish-to-html)
        ("public-html"
         :base-directory "~/"
         :base-extension "org"
         :recursive t
         :exclude "pr.org"
         :makeindex t
         :auto-sitemap t
         :publishing-directory "~/public-html/"
         :publishing-function (org-html-publish-to-html))))
(setq org-export-global-macros
      '(
("source" .
 "(eval (concat \"See [[\"(ems-read-dict-source \"$1\") \"]].\"))")
("define" .
 "(eval (ems-read-dict-definition $1))")
("Define" .
 "(eval (ems-cap-first-char (ems-read-dict-definition $1)))")
("ref" .
 "{{{Define($1)}}} {{{source($1)}}}")
("document-type" .
 "document")
("doc" .
 "{{{document-type}}}")
("document-eli" .
 "(eval (ems-build-document-eli $1))")
("bow-character-template" .
 "(eval (ems-bow-build-character-template $1))")
("bow-adventure-brief" . "*/{{{title}}}/* is a /tabletop role-playing *{{{doc}}}*/ in which {{{property(adventure-inwhich)}}}, usually taking between {{{property(adventure-length)}}} to complete.")))
(org-babel-do-load-languages
 'org-babel-load-languages
 '((crystal . t)
   (ledger . t)
   (shell . t)))))
