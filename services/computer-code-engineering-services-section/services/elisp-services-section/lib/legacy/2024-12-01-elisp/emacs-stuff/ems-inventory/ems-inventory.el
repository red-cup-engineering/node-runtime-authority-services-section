#+TITLE: emsenn's Inventory Management Elisp Package
#+EXPORT_FILE_NAME: ems-inventory
#+HUGO_BASE_DIR: ~/dev/personal-website/
#+HUGO_SECTION: computer-instruction-sets
* emsenn's Inventory Management Elisp PackageH
#+begin_src elisp
;;; ems-inventory.el --- emsenn's package for handling physical property

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-inventory.el/
;; Version: 0.1.0
;; Package-Requires: ((emacs "26.1"))
;; Keywords: emsenn

;; This file is not part of GNU Emacs.

;;; Commentary:

;; This is my package for tracking some metadata about my
;; personal projects, and while it it is licensed for the good
;; of the commons, it probably shouldn't be used by anyone who
;; isn't me.


;;;; Installation

;;;;; Manual

;; Put this file in your load-path, and put this in your init
;; file:

;; (require 'ems-inventory)

;;;; Usage

;;;; Tips

;;;; Credits

;;;; Future Plans

;;; License:


;;; Code:

;;;; Requirements

(require 'ht)
;;;; Customization

(defgroup ems-inventory nil
  "Settings for `ems-inventory'."
  :link '(url-link "http://gitlab.com/emsenn/ems-inventory.el"))

;;;; Commands
(defun ems-inventory-add
;;;; Footer

(provide 'ems-inventory)

;;; ems-inventory.el ends here
#+end_src
