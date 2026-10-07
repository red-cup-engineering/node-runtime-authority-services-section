;;; ems-library.el --- emsenn's package for handling a reading log

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-library.el/
;; Version: 0.1.0
;; Package-Requires: ((emacs "26.1"))
;; Keywords: emsenn

;; This file is not part of GNU Emacs.

;;; Commentary:

;; This is my package for handling my personal reading list
;; and while licensed for the good of the commons, it really
;; shouldn't be used by anyone who isn't me,

;;;; Installation

;;;;; Manual

;; Put this file in your load-path, and put this in your init
;; file:

;; (require 'ems-library)

;;;; Usage

;; I have an elisp file, `ems-log.el`, which (among other
;; lines) has calls to some of the functions here. Here's an
;; excerpt:

;; ;;;; 2019-07-28 Sunday
;; (ems-library-add-book-to-be-read
;;  "Moral Boundaries"
;;  "Tronto, Joan"
;;  "@cyborgneticz@scholar.social")

;; Entries like this manipulate the `ems-library-log'
;; variable. There are functions here for pulling data from
;; it, and also creating "surosian objects," a data structure
;; used by my `suros.el` package.


;;;; Tips

;; + Don't actually use the interactive commands!
;;   Keep a file with a series of function calls like I do, or
;;   skip using functions and maintain the data file directly,
;;   if you want - but that's... not recommended.

;;;; Credits

;;; License:

;; This program was made by emsenn in the United States. To
;; the extent possible under law, they have waived all
;; copyright and related or neighboring rights to this
;; program. This program was made for the good of the commons.

;;; Code:

;;;; Requirements

(require 'ht)

;;;; Customization

(defgroup ems-library nil
  "Settings for `ems-library'."
  :link '(url-link "http://gitlab.com/emsenn/ems-library.el"))

(defvar ems-library-log (ht
			    (:to-read (ht-create))
			    (:have-read (ht-create)))
  "This setting does something.")
;;;; Functions
;;;;;;;; reset library log
(defun ems-library-reset-log ()
  (setq ems-library-log (ht
			 (:to-read (ht-create))
			 (:have-read (ht-create)))))
;;;;;;;; add item to be read
(defun ems-library-add-item-to-be-read (item)
  (let ((to-read (ht-get
		  ems-library-log
		  :to-read))
	(title (ht-get item :title)))
    (ht-set! to-read title item)
    (ht-get to-read title)))
;;;;;;;; create rosian object from item
(defun ems-library-create-rosian-object-from-item (item)
  (let ((object (ht
		 (:headers (ht-create))
		 (:data (ht-create))
		 (:renderings (ht-create)))))
    (ht-map
     (lambda (key val)
       (ht-set! (ht-get object :data) key val))
     item)
    object))
;;;;;;;; get item from log
(defun ems-library-get-title-from-log (title log)
  (ht-get (ht-get ems-library-log log) title))
;;;;; Commands
;;;;;;;; add book to be read
(defun ems-library-add-book-to-be-read (title author &optional recommender)
  (interactive "sTitle? \nsAuthor?")
  (ems-library-add-item-to-be-read
   (ht
    (:title title)
    (:author author))))
;;;;;;;; add link to be read
(defun ems-library-add-link-to-be-read (title author source)
  (interactive "sTitle? \nsAuthor? \nsSource? ")
  (ems-library-add-item-to-be-read
   (ht
    (:title title)
    (:author author)
    (:source source))))
;;;; Footer

(provide 'ems-library)

;;; ems-library.el ends here
