;;; ems-ros.el --- emsenn's responsive object server

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-ros.el/
;; Version: 0.1.0
;; Package-Requires: ((emacs "26.1"))
;; Keywords: emsenn, ActivityPub, IndieWeb

;; This file is not part of GNU Emacs.

;;; Commentary:

;;;; Overview

;; This is my package for handling a responsive object server:
;; a collection of functions for converting data into a
;; standard format and working with it.


;;;; Installation

;;;;; Manual

;; Put this file in your load-path, and put this in your init
;; file:

;; (require 'ems-ros)

;;;; Usage

;; At the moment there are two ways to interact with your ros:
;; manually, and with HTTP requests.

;;;;; Manual Usage

;; Your ros comes with several functions for inserting rosian
;; object renderings into your Emacs buffer. See "User
;; Operation Functions" below for a complete list.

;;;;; HTTP Usage

;; Your ros comes with an HTTP server. It can be started with
;; the command `ems-ros-start-http-server' and stopped with
;; the command `ems-ros-stop-http-server'.

;; Before using the server, you should customize the variables
;; `ems-ros-http-base-url' and `ems-ros-http-port'.

;;;; Tips

;; + This project is really new! Don't get used to how
;;   anything works.

;;;; Credits

;; + The Discworld MUD[1] for helping me see the Web as a
;;   bunch of objects. What a useful paradigm.
;; + Christopher Lemmer-Webber[2] for his work with ActivityPub,
;;   but more generally his work developing the language
;;   around discussing the Web, the Internet, and online
;;   communication.

;; [1]: https://discworld.starturtle.net
;; [2]: https://dustycloud.org

;;;; Manual
;;;;; The "Rosian Object"

;; The core concept here is the "rosian object," the data
;; structure that sources get made into and worked around as,
;; before being spit out. My ros receives a request and
;; responds to it by creating an object, making it, and then
;; doing with it whatever the request specifies. (Usually,
;; sending it off to the requester.)

;; Each rosian object is an assembly of key-value pairs; in
;; this Elisp implementation the object is a hashtable. Each
;; object has three keys, whose values are each hashtables.

;; The `headers` key is used to store metadata about the
;; object. At the moment this is mostly unused - a
;; "Content-type" header is added at the last moment if the
;; object is being sent in response to an HTTP request, but
;; that's it.

;; The `data` key is the heart of a rosian object. It gets
;; items added to it (and changed) as the object gets made in
;; response to a request.

;; The `renderings` key is a bit unusual. When an object gets
;; requested, its data normally gets formated in some way -
;; for example, if my ros receives an HTTP GET request, it's
;; likely going to format the data of the created object as an
;; HTML document. That document would be stored as a string
;; inside the renderings key.

;; Any one object may end up with quite a lot of data, and
;; many renderings of different types - even in prototyping
;; the structure, I was combining text and html type formats.


;;;;; Making Requests

;; The previous section explained the object part of
;; "responsive object server," and this section will explain
;; the "responsive server" part.

;; Your ros receives "requests," which might come from a
;; variety of soruces but for this section, I'll assume are
;; HTTP GET requests.

;; The request is "handled," in this case by
;; `ems-ros-handle-http-get-request', which first "created" a
;; new object, and then uses information in the request to
;; determine what that object should be "made" into. Once the
;; object is made, it is "rendered" into different "forms",
;; and, most of the time, sent to the source of the request.

;; Each request must contain two pieces of information: the
;; <source of the objectmaker> and a symbol or string to be
;; looked up in that <source>. The first piece of information
;; can sometimes be inferred from the second. Down the line,
;; I'd like to be able to infer the former even if it can't be
;; inferred from anything in the request.

;; Continuing the HTTP request, let's say the request comes in
;; to `/library/moral-boundaries.html` This gives us three
;; pieces of information: the <source of the objectmaker> is
;; "library," the requested object symbol is
;; "moral-boundaries," and the rendered form is "html" (which
;; the handler interprets as "html-document".)

;; In the table `ems-ros-object-sources', there is a key
;; "library," which itself contains three keys:

;; + `create-from-symbol-func`, the value of which is a
;;   symbol: the function that will be passed a symbol, and
;;   will return a rosian object.
;; + `list-symbols-func`, the value of which is a symbol: the
;;   function that will return a list of all the symbols which
;;   will return an object if passed to
;;   `create-from-symbol-func'.

;; So, when handling a request to
;; `/library/moral-boundaries.html`, your ros passes
;; `moral-boundaries` to the function that is the value of the
;; `create-from-symbol-func` key in the hash-table which is
;; the value of the `library` key in the
;; `ems-ros-object-sources' hash-table. That returns a made
;; object, but it still needs to have itself rendered into an
;; HTML document.

;; Again, information from the request is passed to functions
;; defined in a hash-table. This time, the table is
;; `ems-ros-object-renderers'. The keys are the same, in our
;; example a `library` key would have a value that is a
;; hash-table of various renderings and the functions which
;; create them - accepting an object and returning a copy of
;; it which includes the rendering.

;; A difference here is that there is a special `default` key
;; which has renderings for a wide variety of keys, and does
;; its best job to make the rendering. So while the `library`
;; key may have a definition for an `html-document` renderer
;; function that is highly specific, it might not have one for
;; rendering a `html-dictionary-item`. In that case, the
;; default rendering would be used. Ultimately, a function is
;; determined and passed the made object and returns a copy
;; which includes the rendering.

;; The handler then sends the object to the client. In the
;; case of an HTTP GET request, each of the object's headers
;; is sent along as a header, and the `html-document`
;; rendering is sent.

;;; License:

;; This program was made by emsenn in the United States. To
;; the extent possible under law, they have waived all
;; copyright and related or neighboring rights to this
;; program. This program was made for the good of the commons.

;;; Code:
;;;; Requirements

;; At the moment, your ros has two big dependencies: `ht',
;; which is a library for working more easily with hashtables,
;; and `web-server', which is a, well, webserver. Hashtables
;; are used throughout your ros, and are the backbone of its
;; "object," the data structure that is the "o" in "ros". The
;; webserver is the HTTP server that's probably how most of
;; the interaction with Ems-Ros will happen.
(require 'ht)
(require 'web-server)
;;;; Customization
(defgroup ems-ros nil
  "Customization variables related to the Ems-Ros personal web
server.")
;;;;; Object Customization
;;;;;;;; language code
(defcustom ems-ros-language-code "en"
  "The ISO639-1 language code that will be applied to new Ems-Ros objects by default."
  :group 'ems-ros
  :type 'string)
;;;;; Actor Customization
;;;;;;;; preferred name
(defcustom ems-ros-actor-preferred-name "emsenn"
  "The name you prefer to go by in casual conversation.")
;;;;;;;; public key
(defcustom ems-ros-actor-public-key ""
  "The public key for Ems-Ros' ActivityPub actor.
Literal newlines must be replaced by \"\\n\".
See the following link for instructions on how to generate the key:
URL `https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/#the-actor'"
  :group 'ems-ros
  :type 'string)
;;;;; Server Customization
;;;;;;;; http port
(defcustom ems-ros-http-port 9000
  ""
  :group 'ems-ros
  :type 'integer)
;;;;;;;; base URL
(defcustom ems-ros-base-url "localhost"
  "The domain name at which your Ems-Ros will be available.
Don't include any http:// or anything after the top-level domain."
  :group 'ems-ros
  :type 'string)
;;;; Variables
;;;;;;;; server object
(setq ems-ros-server-object nil)
;;;;;;;; objectmakers
(setq ems-ros-objectmakers
      (ht
       ('homepage
	(lambda (object)
	  (let ((this-object (ht-copy object)))
	    object)))
       ('teraum-project
	(lambda (object)
	  (ems-ros-make-object-with-data-hashtable
	   object
	   (ht
	    (:project-name "Teraum")
	    (:project-description "a tragically funny fantasy setting")))))))
;;;;;;;; formmakers
(setq ems-ros-formmakers
      (ht
       ('html-homepage
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (ems-ros-read-object-data this-object)))
	    (ht-set!
	     data
	     :title (ht-get
		     data
		     :actor-preferred-name)))))
       ('text-project-brief
	(lambda (object)
	  (let* ((this-object (ht-copy object))
		 (data (ems-ros-read-object-data this-object))
		 (renderings (ems-ros-read-object-renderings this-object)))
	    (format "%s is %s"
		    (ht-get data :project-name)
		    (ht-get data :project-description)))))))
;;;;;;;; http handlers
(setq
 ems-ros-http-handlers
 '(((:GET . ".*") . ems-ros-handle-http-get-request)))
;;;; Functions
;;;;; Basic Functions
;;;;;; Object Functions
;;;;;;; Object Createion Function
;;;;;;;; create object
(defun ems-ros-create-object ()
  "Returns a ems-rosian object with data prepopulated from Ems-Ros' customizable variables."
  (ht
   (:data (ht
	   (:object-language-code ems-ros-language-code)
	   (:actor-preferred-name ems-ros-actor-preferred-name)))
   (:headers (ht-create))
   (:renderings (ht-create))))
;;;;;;;; create object from symbol
(defun ems-ros-create-object-from-symbol (object-symbol)
  "Returns a ems-rosian object if OBJECT-SYMBOL is an object in `ems-ros-objectmakers'."
  (let ((this-object (ht-copy (ems-ros-create-object))))
    (funcall
     (ht-get
      ems-ros-objectmakers
      object-symbol)
     this-object)
    this-object))
;;;;;;; Object Making Functions
;;;;;;;; make object with data hashtable
(defun ems-ros-make-object-with-data-hashtable (object table)
  (let* ((this-object (ht-copy object))
	(data (ems-ros-read-object-data this-object)))
    (ht-map
     (lambda (key val)
       (ht-set! data key val))
     table)
    this-object))
;;;;;;;; make object with http headers
(defun ems-ros-make-object-with-http-headers (object headers)
  (let* ((this-object (ht-copy object))
	 (data (ems-ros-read-object-data
		this-object))
	 (requested-path (substring
			  (cdr (assoc :GET headers))
			  1)))
    (ht-set!
     data
     :requested-path requested-path)
    this-object))
;;;;;;;; make object into homepage
(defun ems-ros-make-object-into-homepage (object)
  (let* ((this-object (ht-copy object))
	 (data (ems-ros-read-object-data this-object))
	 (local-data
	  (ht (:object-title (format "%s's ems-ros instance"
				     ems-ros-actor-preferred-name)))))
    (ht-map
     (lambda (key val)
       (ht-set! data key val)) local-data)
    this-object))
;;;;;;;; make object from scope and symbol
;;;;;;;; make object from scope and string
;;;;;;; Object Reading Functions
(defun ems-ros-read-object-data (object)
  (ht-get object :data))
(defun ems-ros-read-object-form (object form)
  (ht-get (ems-ros-read-object-renderings object) form))
(defun ems-ros-read-object-renderings (object)
  (ht-get object :renderings))
(defun ems-ros-read-object-headers (object)
  (ht-get object :headers))
;;;;;;; Object Rendering Function
;;;;;;;; render object form
(defun ems-ros-render-object-form (object form)
  (ht-set!
   (ems-ros-read-object-renderings object)
   form
   (funcall
    (ht-get ems-ros-formmakers form)
    object))
  object)
;;;;;;;; render object as html homepage
(defun ems-ros-render-object-as-html-homepage (object)
  "Adds an html-document form to the OBJECT. The form is a personal website homepage."
  (let ((object (ems-ros-render-components
		 (ht-copy object)
		 (list 'html-declaration))))
    (ht-set! (ems-ros-read-object-renderings object)
	     :html-document
	     (concat
	      (ems-ros-read-object-form object :html-declaration)))))
;;;;;;;; render html declaration
(defun ems-ros-render-html-declaration (object)
  (let ((this-object (ht-copy object)))
    (ht-set!
     (ems-ros-read-object-renderings
      this-object)
     :html-declaration "<html>")
    this-object))
;;;;;;;; render components
(defun ems-ros-render-components (object components)
  (let ((object (ht-copy object)))
    (mapcar
     (lambda (component)
       (setq object
	     (funcall (symbol-function
		       (intern (concat
				"ems-ros-render-"
				(symbol-name component))))
		      object)))
     components)
    object))
;;;;;;; Compose Object Functions
(defun ems-ros-compose-html-homepage (object)
  (let ((object (ht-copy object)))
    (ht-set! (ems-ros-read-object-renderings object)
	     :html-document
	     (format "%s"
		     (ems-ros-read-object-form object :html-declaration)))
    object))
;;;;;; Request Handler Functions
;;;;;;; HTTP Request Handler Functions
;;;;;;;; handle http get request
(defun ems-ros-handle-http-get-request (http-request)
  "Process REQUEST as an GET-type HTTP request."
  (with-slots
      (process headers)
      http-request
    (let* ((this-object (ems-ros-create-object))
	   (this-object (ems-ros-make-object-with-http-headers
			 this-object
			 headers))
	   (data (ems-ros-read-object-data
		  this-object)))
      (if (equal (ht-get data :requested-path)
		 "")
	  (setq this-object
		(ems-ros-render-object-as-html-homepage
		 (ems-ros-make-object-into-homepage
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
       (ems-ros-read-object-headers
	this-object))
      (process-send-string
       process
       (ems-ros-read-object-form
	this-object
	:html-document)))))
;;;;; Combination Functions
;;;;;; Object Combination Functions
;;;;;;;; create object from symbol, render form, and read it
(defun ems-ros-create-object-from-symbol-render-form-and-read-it (object-symbol form)
  "Creates an object from OBJECT-SYMBOL, renders it as FORM, and returns that form as a string."
  (let* ((this-object
	  (ems-ros-render-object-form
	   (ems-ros-create-object-from-symbol object-symbol)
	   form)))
    (ems-ros-read-object-form this-object form)))
;;;;; HTTP Server Operation Functions
;;;;;;;; start http server
(defun ems-ros-start-http-server ()
  "Starts an HTTP server for interacting with your ems-ros.
The variable `ems-ros-server-object' is set to the created server object.

Your ems-ros reads the variable `ems-ros-config' as it starts, so
make sure you have customized it before starting the server."
  (interactive)
  (setq ems-ros-server-object
	(ws-start
	 ems-ros-http-handlers
	 ems-ros-http-port
	 (get-buffer-create "ems-ros-log"))))
;;;;;;;; stop http server
(defun ems-ros-stop-http-server ()
  "Stop your ems-ros server.
Precisely, it calls the function `ws-stop' on the value of the
variable `ems-ros-server-object'."
  (interactive)
  (ws-stop ems-ros-server-object))
;;;;; User Operation Functions
;;;;;;;; insert text project brief at point
(defun ems-ros-insert-text-project-brief-at-point (project)
  (interactive "sproject name? ")
  (insert
   (ems-ros-create-object-from-symbol-render-form-and-read-it
    (intern (concat project "-project"))
    'text-project-brief)))
;;;; Footer
(provide 'ems-ros)
;;; ems-ros.el ends here
