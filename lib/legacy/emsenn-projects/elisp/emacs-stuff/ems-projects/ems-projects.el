;;; ems-projects.el --- emsenn's package for handling project metadata

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-projects.el/
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

;; (require 'ems-projects)

;;;; Usage

;;;; Tips

;;;; Credits

;;;; Future Plans

;;; License:


;;; Code:

;;;; Requirements

(require 'ht)
(require 'mustache)
;;;; Customization

(defgroup ems-projects nil
  "Settings for `ems-projects'."
  :link '(url-link "http://gitlab.com/emsenn/ems-projects.el"))

(setq ems-projects-table
  (ht
   ('teraum
    (ht
     (:name "Teraum")
     (:author "emsenn")
     (:type "fiction")
     (:origin-country "United States")
     (:local-source "/home/emsenn/src/teraum/")
     (:description "a tragically funny fantasy world")
     (:license "commonist")))
   ('ems-library
    (ht
     (:name "ems-library.el")
     (:author "emsenn")
     (:type "collection of elisp declarations")
     (:origin-country "United States")
     (:local-source "/home/emsenn/src/ems-library/")
     (:license "commonist")))
   ('ems-projects
    (ht
     (:name "ems-projects.el")
     (:author "emsenn")
     (:type "collection of elisp declarations")
     (:origin-country "United States")
     (:local-source "/home/emsenn/src/ems-projects")
     (:license "commonist")))))
(setq ems-projects-rosian-object-formers
      (ht
       ('text-brief
	(lambda (object)
	  (let* ((this-object object)
		 (data (ht-get this-object :data)))
	    (ht-set!
	     (ht-get
	      this-object
	      :renderings)
	     :text-brief (format
			  "%s is %s."
			  (ht-get data :project-title)
			  (ht-get
			   data
			   :project-description)))
	    this-object)))))
(setq ems-projects-licenses
      '(("commonist" . "This {{type}} was written by me, {{author}}, in the {{origin-country}}, for the good of the commons. To the extent possible under law, I have waived all copyright and related or neighboring rights to this {{type}}.")))
;;;; Functions
;;;;; Basic functions
;;;;;;;; read license
(defun ems-projects-read-license (license)
  (cdr (assoc license ems-projects-licenses)))
;;;;;;;; read project from symbol
(defun ems-projects-read-project-from-symbol (symbol)
  (ht-get ems-projects-table symbol))
;;;;;;;; make project license
(defun ems-projects-make-project-license (project)
(let* ((project (ems-projects-read-project-from-symbol 'teraum))
       (project-license (ems-projects-read-license (ht-get project :license)))
       (context (ht-create)))
(ht-map
 (lambda (key value)
   (ht-set! context (substring (format "%s" key) 1) value))
 project)
(mustache-render project-license context)))
;;;;; Rosian object functions
;;;;;; Make rosian objects
;;;;;;;; make rosian object from symbol
(defun ems-projects-make-rosian-object-from-symbol (object symbol)
  (let* ((object (ht-copy object))
	 (object-data (ht-get object :data))
	 (project (ems-projects-read-project-from-symbol
		   symbol)))
    (ht-map
     (lambda (key value)
       ;; project name
       ;; --> object title, project-title
       (cond ((equal key :name)
	      (mapcar
	       (lambda (object-key)
		 (ht-set!
		  object-data
		  object-key
		  value))
	       (list :title :project-title)))
	     ;; project description
	     ;; --> object description, project-description
	     ((equal key :description)
	      (mapcar
	       (lambda (object-key)
		 (ht-set!
		  object-data
		  object-key
		  value))
	       (list
		:description :project-description)))
	     ;; project license
	     ;; made then --> object project-license
	     ((equal key :license)
	      (ht-set!
	       object-data
	       :project-license
	       (ems-projects-make-project-license project)))
	     ;; otherwise, project key/value
	     ;; --> object key/value
	     (t
	      (ht-set! object-data key value))))
     project)
    object))
;;;;;; Form rosian objects
;;;;;;;; form rosian object from symbol
(defun ems-projects-form-rosian-object-from-symbol (object symbol)
  (let* ((this-object object)
	 (data (ht-get this-object :data))
	 (renderings (ht-get
		      this-object
		      :renderings))
	 (former (ems-projects-read-rosian-object-former-from-symbol
		  symbol)))
    (funcall former object)))
;;;;;;;; read rosian object former from symbol
(defun ems-projects-read-rosian-object-former-from-symbol (symbol)
  (ht-get ems-projects-rosian-object-formers symbol))
;;;;; Commands

(defun ems-build-document-eli (eli)
  "Returns a string about the editorial and licensing information of the open Org-mode buffer."
  (concat
   "This document was written by me, {{{author}}}, in the United States. "
   (if (string-equal eli "default")
       "To the extent possible under law, I have waived all copyright and related or neighboring rights to this {{{doc}}}. This {{{doc}}} was created for the benefit of the public.")))

;;;; Footer

(provide 'ems-projects)

;;; ems-projects.el ends here
