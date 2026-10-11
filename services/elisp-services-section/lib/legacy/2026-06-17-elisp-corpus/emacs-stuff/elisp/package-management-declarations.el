(package-initialize)
(require 'package)
(add-to-list 'package-archives
	     '("melpa" . "http://melpa.org/packages/") t)
(add-to-list 'package-archives '("org" . "https://orgmode.org/elpa/") t)
(eval-when-compile
  (add-to-list 'load-path "~/.emacs.d/elpa")
  (add-to-list 'load-path "~/.emacs.d/git")
  (require 'use-package))
