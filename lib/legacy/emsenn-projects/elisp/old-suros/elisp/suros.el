;;; suros.el --- a personal web server

;; made in the United States by emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; Keywords: server, ActivityPub
;; Version: 0.1.0

;; This program was made by emsenn in the United States. To
;; the extent possible under law, they have waived all
;; copyright and related or neighboring rights to this
;; program. This program was made for the good of the commons.

;;;; Commentary
;; Suros.el provides a web server that provides objects rendered
;; from Elisp data.

;;;; DEPENDENCIES
(require 'ht)
(require 'web-server)
;;;; CUSTOMIZABLE VARIABLES
(defgroup suros nil
  "Customization variables related to the Suros personal web server.")
;;;;; GENERAL CONFIGURATION
;;;;;;;; Base URL
(defcustom suros-base-url ""
  "The domain name at which your Suros will be available.
Don't include any http:// or anything after the top-level domain."
  :group 'suros
  :type 'string)
;;;;;;;; Language code
(defcustom suros-language-code "en"
  "The ISO639-1 language code that your content may be assumed
to be in."
  :group 'suros
  :type 'string)
;;;;; ACTOR CONFIGURATION
;;;;;;;; Preferred name
(defcustom suros-actor-preferred-name ""
  "The name you prefer to go by in casual conversation.")
;;;;;;;; Public key
(defcustom suros-actor-public-key ""
  "The public key for Suros' ActivityPub actor.
Literal newlines must be replaced by \"\\n\".
See the following link for instructions on how to generate the key:
URL `https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/#the-actor'"
  :group 'suros
  :type 'string)
;;;; INTERNAL VARIABLES
;;;;;;;; server object
(setq suros-server-object nil)
;;;;;;;; objectmakers
(setq suros-objectmakers
      (ht
       ('homepage
	(lambda (object)
	  (let ((this-object (ht-copy object)))
	    object)))
       ('teraum-project
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (suros-read-object-data object)))
	    (ht-set! data :project-name "Teraum")
	    this-object)))))
;;;;;;;; forms
(setq suros-formmakers
      (ht
       ('html-homepage
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (suros-read-object-data object)))
	    (ht-set! data :title (ht-get data :actor-preferred-name)))))))
;;;; OBJECT CREATION FUNCTIONS
;;;;;;;; create object
(defun suros-create-object ()
  "Returns a surosian object with data prepopulated from the customizable variables."
  (ht
   (:data (ht
	   (:object-language-code suros-language-code)
	   (:actor-preferred-name suros-actor-preferred-name)))
   (:headers (ht-create))
   (:renderings (ht-create))))
;;;;;;;; create object from symbol
(defun suros-create-object-from-symbol (object-symbol)
  "Returns a surosian object if OBJECT-SYMBOL is an object in `suros-objectmakers'."
  (let ((this-object (ht-copy (suros-create-object))))
    (funcall
     (ht-get
      suros-objectmakers
      object-symbol)
     this-object)
    this-object))
;;;; OBJECT READING FUNCTION
;;;;;;;; read object data
(defun suros-read-object-data (object)
  (ht-get object :data))
(defun suros-read-object-renderings (object)
  (ht-get object :renderings))
(defun suros-read-object-form (object form)
  (ht-get (suros-read-object-renderings object) form))
(defun suros-add-text-project-brief-rendering-to-object (object)
  (let ((this-object (ht-copy object)))
    (ht-set! (suros-read-object-renderings object)
	     :text-project-brief "foodesc")
    this-object))
(defun suros-create-object-from-symbol-and-render-form (object-symbol form)
  (suros-render-object-form (suros-create-object-from-symbol object-symbol) form))
(defun suros-create-object-from-symbol-render-form-and-read-it (object-symbol form)
  (suros-read-object-form
   (suros-create-object-from-symbol-and-render-form object form) form))
;;;; OBJECT SENDING FUNCTIONS
;;;;;;;; send object form to point
(defun suros-send-object-form-to-point (object form)
  )
;;;;;;;; Send object, from symbol, into buffer, as form.
(defun suros-send-object-from-symbol-into-buffer-as-form (object-symbol buffer form)
  (interactive "Sobject symbol?
sbuffer name?
Sform? ")
  (if (bufferp buffer)
      (set-buffer buffer)
    (progn
      (set-buffer
       (get-buffer-create buffer))
      (insert
       (ht-get
	(ht-get
	 (suros-render-object-as-form
	  (suros-create-object-from-symbol
	   object-symbol)
	  form)
	 :renderings)
	form)))))
;;;;;;;; Send object, from symbol, as form, to point
(defun suros-send-object-from-symbol-as-form-to-point
    (object-symbol form)
  (insert
   (ht-get
    (ht-get
     (suros-render-object-as-form
      (suros-create-object-from-symbol
       object-symbol)
      form)
     :renderings)
    form)))
;;;; OBJECT RENDERING FUNCTIONS
;;;;; Render object as form
(defun suros-render-object-as-form (object form)
  ;; Lookup form in a hashtable of form-symbol->lambda that takes an object as argument and passes it to a bunch of suros-render-object-as-FORM where form is the form.
  (ht-set!
   (ht-get object :renderings)
   form (funcall (ht-get suros-objectforms-by-symbol form)
		 object))
  object)
;;;;; Render object, from symbol, as form
(defun suros-render-object-from-symbol-as-form
    (object-symbol form)
  (let ((this-object
	 (suros-make-object-from-symbol object-symbol))
	)
    (ht-set! (ht-get this-object :forms)
	     form
	     (funcall (ht-get
		       suros-objectforms-by-symbol form)
		      this-object))
    this-object))
;;;;; Render HTML forms
;;;;;; HTML declaration
(defun suros-render-html-declaration-from-object (object)
  "<html>")
;;;; OBJECT MAKING FUNCTIONS
;;;;; Functions to make objects from something
;;;;;; Make object from symbol
(defun suros-make-object-from-symbol (object-symbol)
  (let ((this-object
	 (suros-create-object)))
    (funcall (ht-get suros-objectmakers-by-symbol object-symbol) this-object)
    this-object))
;;;;; FUNCTIONS TO MAKE OBJECTS WITH SOMETHING
;;;;;; Make object from HTTP headers
(defun suros-read-http-headers-into-object-datapool (http-headers object)
  (ht-set!
   (ht-get object :datapool)
   "requested-path"
   (substring
    (cdr (assoc :GET http-headers))
    1)))
;;;;;; Make object from config
(defun suros-read-config-into-object-datapool (config object)
  (let ((config-attrs '("actor-public-key"
			"base-url"
			"language-code"
			"preferred-name"
			"proper-name"
			"server-description"
			"server-name"
			"server-source-link"
			"username")))
    (mapcar (lambda (attr)
	      (ht-set! (ht-get object :datapool)
		       attr
		       (ht-get suros-config attr)))
	    config-attrs)))
;;;;; FUNCTIONS TO MAKE OBJECTS INTO SOMETHING
;;;;;; Make object into homepage
(defun suros-make-object-into-homepage (object)
  ;; foo
  (let* ((this-object (ht-copy object))
	 (data (ht-get this-object :data)))
    (ht-set! data :object-title "Foo")))
(defun suros-make-homepage-html-object (object)
  (ht-set! (ht-get object :headers) "Content-type" "text/html")
  (let* ((data (ht-get object :datapool))
	 (local-data
	  (ht ("object-title"
	       (concat
		(ht-get data "preferred-name") "'s "
		(ht-get data "server-name") " instance")))))
    (suros-apply-local-data-to-object-datapool local-data object))
  (let ((data (ht-get object :datapool)))
    (ht-set!
     object :rendering
     (concat
      (suros-render-html-document-declaration object)
      "<body><header>" (suros-render-html-h1 object) "</header>"
      "<p>" (ht-get data "server-name") " is "
      (ht-get data "server-description") "."
      (let ((link (ht-get data "server-source-link")))
	(if link
	    (concat " Its source is available at "
	     "<a href=\"" link  "\">" link "</a>.")))
      "</p></body></html>"))))
(provide 'suros)
;;; suros.el ends here
