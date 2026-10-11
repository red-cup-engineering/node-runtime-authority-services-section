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
;; At the moment, Suros has two big dependencies: `ht', which is a
;; library for working more easily with hashtables, and `web-server',
;; which is a, well, webserver. Hashtables are used throughout Suros,
;; and are the backbone of its "object," the data structure that is
;; the "o" in "Suros." The webserver is the HTTP server that's
;; probably how most of the interaction with Suros will happen.
(require 'ht)
(require 'web-server)
;;;; CUSTOMIZABLE VARIABLES
(defgroup suros nil
  "Customization variables related to the Suros personal web server.")
;;;;; OBJECT CONFIGURATION
;;;;;;;; language code
(defcustom suros-language-code "en"
  "The ISO639-1 language code that will be applied to new Suros objects by default."
  :group 'suros
  :type 'string)
;;;;; ACTOR CONFIGURATION
;;;;;;;; preferred name
(defcustom suros-actor-preferred-name "emsenn"
  "The name you prefer to go by in casual conversation.")
;;;;;;;; public key
(defcustom suros-actor-public-key ""
  "The public key for Suros' ActivityPub actor.
Literal newlines must be replaced by \"\\n\".
See the following link for instructions on how to generate the key:
URL `https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/#the-actor'"
  :group 'suros
  :type 'string)
;;;;; SERVER CONFIGURATION
;;;;;;;; http port
(defcustom suros-http-port 9000
  ""
  :group 'suros
  :type 'integer)
;;;;;;;; base URL
(defcustom suros-base-url "localhost"
  "The domain name at which your Suros will be available.
Don't include any http:// or anything after the top-level domain."
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
	  (suros-make-object-with-data-hashtable
	   object
	   (ht
	    (:project-name "Teraum")
	    (:project-description "a tragically funny fantasy setting")))))))
;;;;;;;; formmakers
(setq suros-formmakers
      (ht
       ('html-homepage
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (suros-read-object-data this-object)))
	    (ht-set!
	     data
	     :title (ht-get
		     data
		     :actor-preferred-name)))))
       ('text-project-brief
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (suros-read-object-data this-object))
		 (renderings (suros-read-object-renderings this-object)))
	    (format "%s is %s"
		    (ht-get data :project-name)
		    (ht-get data :project-description)))))))
;;;;;;;; http handlers
(setq
 suros-http-handlers
 '(((:GET . ".*") . suros-handle-http-get-request)))
;;;; FUNCTIONS
;;;;; BASIC FUNCTIONS
;;;;;; OBJECT FUNCTIONS
;;;;;;; OBJECT CREATION FUNCTIONS
;;;;;;;; create object
(defun suros-create-object ()
  "Returns a surosian object with data prepopulated from Suros' customizable variables."
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
;;;;;;; OBJECT MAKING FUNCTIONS
;;;;;;;; make object with data hashtable
(defun suros-make-object-with-data-hashtable (object table)
  (let* ((this-object (ht-copy object))
	(data (suros-read-object-data this-object)))
    (ht-map
     (lambda (key val)
       (ht-set! data key val))
     table)
    this-object))
;;;;;;;; make object with http headers
(defun suros-make-object-with-http-headers (object headers)
  (let* ((this-object (ht-copy object))
	 (data (suros-read-object-data
		this-object))
	 (requested-path (substring
			  (cdr (assoc :GET headers))
			  1)))
    (ht-set!
     data
     :requested-path requested-path)
    this-object))
;;;;;;; make object into homepage
(defun suros-make-object-into-homepage (object)
  (let* ((this-object (ht-copy object))
	 (data (suros-read-object-data this-object))
	 (local-data
	  (ht (:object-title (format "%s's suros instance"
				     suros-actor-preferred-name)))))
    (ht-map
     (lambda (key val)
       (ht-set! data key val)) local-data)
    this-object))
;;;;;;; OBJECT READING FUNCTIONS
(defun suros-read-object-data (object)
  (ht-get object :data))
(defun suros-read-object-form (object form)
  (ht-get (suros-read-object-renderings object) form))
(defun suros-read-object-renderings (object)
  (ht-get object :renderings))
(defun suros-read-object-headers (object)
  (ht-get object :headers))
;;;;;;; OBJECT RENDERING FUNCTIONS
;;;;;;;; render object form
(defun suros-render-object-form (object form)
  (ht-set!
   (suros-read-object-renderings object)
   form
   (funcall
    (ht-get suros-formmakers form)
    object))
  object)
;;;;;;;; render object as html homepage
(defun suros-render-object-as-html-homepage (object)
  "Adds an html-document form to the OBJECT. The form is a personal website homepage."
  (let ((object (suros-render-components
		 (ht-copy object)
		 (list 'html-declaration))))
    (ht-set! (suros-read-object-renderings object)
	     :html-document
	     (concat
	      (suros-read-object-form object :html-declaration)))))
;;;;;;;; render html declaration
(defun suros-render-html-declaration (object)
  (let ((this-object (ht-copy object)))
    (ht-set!
     (suros-read-object-renderings
      this-object)
     :html-declaration "<html>")
    this-object))
;;;;;;;; render components
(defun suros-render-components (object components)
  (let ((object (ht-copy object)))
    (mapcar
     (lambda (component)
       (setq object
	     (funcall (symbol-function
		       (intern (concat
				"suros-render-"
				(symbol-name component))))
		      object)))
     components)
    object))
;;;;;;; COMPOSE OBJECT FUNCTIONS
(defun suros-compose-html-homepage (object)
  (let ((object (ht-copy object)))
    (ht-set! (suros-read-object-renderings object)
	     :html-document
	     (format "%s"
		     (suros-read-object-form object :html-declaration)))
    object))
;;;;;; REQUEST HANDLER FUNCTIONS
;;;;;;; HTTP HANDLER FUNCTIONS
;;;;;;;; handle http get request
(defun suros-handle-http-get-request (http-request)
  "Process REQUEST as an GET-type HTTP request."
  (with-slots
      (process headers)
      http-request
    (let* ((this-object (suros-create-object))
	   (this-object (suros-make-object-with-http-headers
			 this-object
			 headers))
	   (data (suros-read-object-data
		  this-object)))
      (if (equal (ht-get data :requested-path)
		 "")
	  (setq this-object
		(suros-render-object-as-html-homepage
		 (suros-make-object-into-homepage
		  this-object)))
	(progn
	  (ht-set!
	   (ht-get this-object :renderings)
	   :html-document "No path? 404, maybe.")
	  (ht-set!
	   (ht-get this-object :headers)
	   "Content-type"
	   "text/html")))
      (ht-map
       (lambda (key val)
	 (ws-response-header
	  process
	  200
	  (list key val)))
       (suros-read-object-headers
	this-object))
      (process-send-string
       process
       (suros-read-object-form
	this-object
	:html-document)))))
;;;;; COMBINATION FUNCTIONS
;;;;;; OBJECT COMBO FUNCTIONS
;;;;;;;; create object from symbol, render form, and read it
(defun suros-create-object-from-symbol-render-form-and-read-it (object-symbol form)
  "Creates an object from OBJECT-SYMBOL, renders it as FORM, and returns that form as a string."
  (let* ((this-object
	  (suros-render-object-form
	   (suros-create-object-from-symbol object-symbol)
	   form)))
    (suros-read-object-form this-object form)))
;;;;; SERVER OPERATIONS
;;;;;;;; start http server
(defun suros-start-http-server ()
  "Starts an HTTP server for interacting with your suros.
The variable `suros-server-object' is set to the created server object.

Your suros reads the variable `suros-config' as it starts, so
make sure you have customized it before starting the server."
  (interactive)
  (setq suros-server-object
	(ws-start
	 suros-http-handlers
	 suros-http-port
	 (get-buffer-create "suros-log"))))
;;;;;;;; stop http server
(defun suros-stop-http-server ()
  "Stop your suros server.
Precisely, it calls the function `ws-stop' on the value of the
variable `suros-server-object'."
  (interactive)
  (ws-stop suros-server-object))
;;;;; USER OPERATIONS
;;;;;;;; insert text project brief at point
(defun suros-insert-text-project-brief-at-point (project)
  (interactive "sproject name? ")
  (insert
   (suros-create-object-from-symbol-render-form-and-read-it
    (intern (concat project "-project"))
    'text-project-brief)))
