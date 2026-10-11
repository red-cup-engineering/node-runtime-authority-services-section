;;; ems-ros.el --- emsenn's responsive object server

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-ros.el/
;; Version: 0.1.0
;; Package-Requires: ((emacs "26.1"))
;; Keywords: emsenn, ActivityPub, IndieWeb

;; This file is not part of GNU Emacs.

;;; Commentary
;;;; Overview

;; This is my package for handling a responsive object server:
;; a collection of functions for converting data into a
;; standard format and working with it.


;;;; Installation

;;;;; Manual

;; Put this file in your load-path, and put this in your init file:

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

;; Here's what an object might look like, using the `ht'
;; package's shorthand:

;; (ht
;;  (:headers (<empty hash-table>))
;;  (:data
;;   (:item-title "Moral Boundaries")
;;   (:item-author "Tronto, Joan")
;;   (:object-title "Library Item: Moral Boundaries")
;;   (:object-author "emsenn"))
;;  (:renderings
;;   (:text-document "LIBRARY ITEM: Moral Boundaries\nby\n
;;  Tronto, Joan")))

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

;;;; Changelog
;;;;; Recent

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
(require 'mustache)
(require 'web-server)
;;;; Customization
(defgroup ems-ros nil
  "Customization variables related to the Ems-Ros personal web
server.")
;;;;; Object Customization
;;;;;;;; language code
(defcustom ems-ros-language-code "en"
  "The ISO639-1 language code that will be applied to new rosian objects by default."
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
  "The domain name at which your ros will be available.
Don't include any http:// or anything after the top-level domain."
  :group 'ems-ros
  :type 'string)
;;;; Variables
;;;;;;;; server object
(setq ems-ros-server-object nil)
;;;;;;;; http handlers
(setq
 ems-ros-http-handlers
 '(((:GET . ".*") . ems-ros-handle-http-get-request)))
;;;; Functions
;;;;; Basic Functions
;;;;;; Object Functions
;;;;;;; Object Creation Functions
;;;;;;;; create object
(defun ems-ros-create-object ()
  "Returns a ems-rosian object with data prepopulated from Ems-Ros' customizable variables."
  (ht
   (:data (ht
	   (:object-language-code ems-ros-language-code)))
   (:headers (ht-create))
   (:renderings (ht-create))))
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
  (let* ((object(ht-copy object))
	 (data (ems-ros-read-object-data
		object))
	 (requested-path (substring
			  (cdr (assoc :GET headers))
			  1)))
    (ht-set!
     data
     :requested-path requested-path)
    object))
;;;;;;; make object into homepage
(defun ems-ros-make-object-into-homepage (object)
  (let* ((this-object (ht-copy object))
	 (data (ems-ros-read-object-data
		this-object))
	 (local-data (ht
		      (:object-title (format
				      "%s's ems-ros instance"
				      ems-ros-actor-preferred-name)))))
    (ht-map
     (lambda (key val)
       (ht-set! data key val))
     local-data)
    this-object))
;;;;;;;; make object with remote maker
(defun ems-ros-make-object-with-remote-maker (source symbol &optional obj)
  (funcall
   (symbol-function
    (ht-get
     ems-ros-object-maker-sources
     source))
   (if (boundp 'obj)
       obj
     (ems-ros-create-object))
   'teraum))
(defun ems-ros-read-source-func-from-sources (source sources)
  (symbol-function (ht-get sources source)))
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
	      (ems-ros-read-object-form object :html-declaration)))
    (ht-set! (ht-get object :headers)
	     "Content-type"
	     "text/html")
    object))
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
    (let* ((object (ems-ros-make-object-with-http-headers
		    (ems-ros-create-object)
		    headers))
	   (data (ems-ros-read-object-data
		  object))
	   (renderings (ems-ros-read-object-renderings
			object))
	   (path (ht-get data :requested-path))
	   (split-path (delq "" (split-string path "\/"))))
      (cond
       ((equal path "")
	(progn
	  (setq object (ems-ros-render-object-with-html-homepage
			object))))
       ((equal (car split-path) "teraum")
	(cond
	 ((equal (length split-path) 1)
	  (progn
	    (ht-set!
	     renderings
	     :html-document "teraum!")))
	 ((equal (length split-path) 2)
	  (progn
	    (let ((teraum-symbol (intern (car (cdr split-path)))))
	      (setq object
		    (ems-ros-make-object-with-teraum-symbol
		     object
		     teraum-symbol))
	      (setq object
		    (ems-ros-render-object-with-teraum-html-document
		     object))))))))
      (if (ht-get renderings :html-document)
	  (progn
	    (ht-set!
	     (ht-get object :headers)
	     "Content-type"
	     "text/html")
	    (ht-map
	     (lambda (key val)
	       (ws-response-header
		process
		200
		(list key val)))
	     (ems-ros-read-object-headers
	      object))))
      (process-send-string
       process
       (ems-ros-read-object-form
	object
	:html-document)))))

(defun ems-ros-make-object-with-teraum-symbol (object symbol)
  (let* ((object (ht-copy object))
	 (data (ht-get object :data))
	 (item (ht-get teraum-data symbol)))
    (ht-map
     (lambda (key value)
       (cond ((equal key :name)
	      (mapcar
	       (lambda (object-key)
		 (ht-set!
		  data
		  object-key
		  value))
	       (list :title :item-name)))))
     (ht-get teraum-data symbol))
    object))
(defun ems-ros-render-object-with-teraum-html-document (object)
  (let* ((object (ht-copy object))
	 (data (ht-get object :data))
	 (renderings (ht-get object :renderings)))
    (ht-set! (ht-get object :renderings) :html-document "argle")
    object))
(defun ems-ros-render-object-with-html-homepage (object)
  (let* ((object (ht-copy object))
	 (data (ht-get object :data))
	 (renderings (ht-get object :renderings))
	 (context (ht-create))
	 (local-data
	  (ht
	   (:title "emsenn's homepage"))))
    (ht-map
     (lambda (key value)
       (ht-set data key value))
     local-data)
    (setq object (ems-ros-render-object-with-html-declaration
		  (ems-ros-render-object-with-html-head-meta
		    (ems-ros-render-object-with-css-basic-stylesheet
		  object))))
    (ht-map
     (lambda (key value)
       (ht-set! context
		(format "data-%s"
			(substring (format "%s" key) 1)) value))
     data)
    (ht-map
     (lambda (key value)
       (ht-set! context
		(format "rendering-%s"
			(substring (format "%s" key) 1)) value))
     renderings)
    (ht-set! (ht-get object :renderings)
	     :html-document
	     (mustache-render
	      (concat
	       "{{{rendering-html-declaration}}}"
	       "<head>"
	       "{{{rendering-html-head-meta}}}"
	       "{{{rendering-html-head-links}}}"
	       "<title>{{{data-title}}}</title>"
	       "<style>"
	       "{{{rendering-css-basic-stylesheet}}}"
	       "</style>"
	       "</head>"
	       "<body>"
	       "<a class=\"skipToContentLink\" href=\"#content\">Skip to Content</a>"
	       "<header>"
	       "<h1>My name is emsenn.</h1>"
	       "</header>"
	       "<main>"
	       "</main>"
	       "</body>")
	      context))
    object))
(defun ems-ros-render-object-with-html-declaration (object)
  (let* ((object (ht-copy object))
	  (data (ht-get object :data))
	  (renderings (ht-get object :renderings))
	  (context (ht-create)))
       (ht-set! renderings
		:html-declaration
		(concat
		 "<!DOCTYPE html>"
		 "<html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\">"))
       object))
(defun ems-ros-render-object-with-html-head-meta (object)
  (let* ((object (ht-copy object))
	  (data (ht-get object :data))
	  (renderings (ht-get object :renderings))
	  (context (ht-create)))
       (ht-set! renderings
		:html-head-meta
		(concat
		 "<meta charset=\"utf-8\">"
		 "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, maximum-scale=5\">"
		 "<meta name=\"referrer\" content=\"no-referrer\">"
		 "<meta property=\"og:locale\" content=\"en\">"
		 "<meta property=\"og:site_name\" content=\"emsenn\">"
		 "<meta property=\"og:title=\" content=\"emsenn\">"))
       object))
(defun ems-ros-render-object-with-css-basic-stylesheet (object)
  (let* ((object (ht-copy object))
	  (data (ht-get object :data))
	  (renderings (ht-get object :renderings))
	  (context (ht-create)))
       (ht-set! renderings
		:css-basic-stylesheet
		"body {
position: relative;
background-color: #eee;
color: #444;
font-family: serif;
margin: 0 auto;
padding-bottom: 6rem;
min-height: 100%;
font-size: 1.2em;
}
header, h1 {
font-family: sans-serif;
text-align: left;
margin-left: 1em;
width: 80vw;
overflow: hidden;
font-family: sans-serif;
}
.title { font-size: 3.2rem; }
.subtitle { font-size: 2.2rem; }
main, #content {
width: 75vw;
max-width: 40em;
margin: 0 0 0 2em;
line-height: 1.6;
margin-bottom: 8rem;
}
footer, #postamble {
padding: 1em 0;
position: absolute;
right: 0;
bottom: 0;
left: 0;
}
section {
border-bottom: 0.1em solid #444;
margin-bottom: 1em;
}
.outline-3 {
border-bottom: 0.1rem dotted #444;
}
blockquote {
padding: 0.5rem;
border-left: 0.1em solid #444;
}
table {
border-collapse: collapse;
border-spacing: 0;
empty-cells: show;
border: 0.1em solid #444;
}
thead { font-family: sans-serif; }
th, td {
padding: 0 0.3em;
border: 0.01em solid #444;
}
img {
max-width: 80vw;
vertical-align: middle;
}
pre, .src {
padding: 0.5em;
border: 0.1em solid #444;
white-space: pre-wrap;
overflow-x: scroll;
text-overflow: clip;
}
dt {
font-weight: normal;
display: inline-block;
border-bottom: 0.1rem dotted #444;
}
#text-index dt { border-bottom: none; }
h2, h3, h4, h5, h6, h7, h8, h9, h10 {
display: block;
font-family: sans-serif;
margin: 0.5em;
}
h2 {
text-align: center;
}
h2 { font-size: 2em; }
h3 {
font-size: 1.8em;
}
h4 {
font-size: 1.6em;
}
h5 {
font-size: 1.4em;
margin: 0.5em 0 0.2em 10%;
}
h6 {
font-size: 1.2em;
margin: 0.5em 0 0.2em 30%;
}
a {
text-decoration: none;
color: #3ac;
display: inline;
position: relative;
border-bottom: 0.1rem dotted;
line-height: 1.2;
transition: border 0.3s;
}
a:hover {
color: #5ce;
outline-style: none;
border-bottom: 0.1rem solid;
}
a:visited { color: #b8c; }
a:visited:hover { color: #dae; }
a:focus {
outline-style: none;
border-bottom: 0.1rem solid;
}
::selection { background-color: #777; color: #eee; }
a::selection { background-color: #ccc; }
.todo {
background-color: #ddd;
color: #333;
font-size: .8rem;
float: right;
}
.org-src-container + .example {
margin-left: 8em;
}
label.org-src-name {
margin: 0 0 0 3em;
font-family: sans-serif;
font-size: 1rem;
line-height: 0;
}
.skipToContentLink {
opacity: 0;
position: absolute;
}
.skipToContentLink:focus{
opacity:1
}")
       object))
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
;;;;;;;; create object from source by symbol, render form, and read it
(defun ems-ros-create-object-from-source-by-symbol-render-form-and-read-it (source symbol form)
  "Creates an object from SOURCE matching SYMBOL, renders it as FORM, and returns that form as a string."
  (ems-ros-read-object-form
   (ems-ros-render-object-form
    (ems-ros-create-object-from-source-by-symbol
     source
     symbol)
    form)
   form))
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
;;;;;;;; insert object from source by symbol as form at point
(defun ems-ros-insert-object-from-source-by-symbol-as-form-at-point (source symbol form)
  (insert
   (ems-ros-create-object-from-source-by-symbol-render-form-and-read-it
    source symbol form)))
;;;;;;;; insert text project brief at point
(defun ems-ros-insert-text-project-brief-at-point (project)
  "Given a PROJECT name, insert the rendered project brief."
  (interactive "sProject name? ")
  (insert
   (ems-ros-create-object-from-symbol-render-form-and-read-it
    (intern (concat project "-project"))
    'text-project-brief)))
(defun ems-ros-insert-text-recent-activities-brief (actor)
  "Given a local ACTOR name, return a textual brief of their recent activities."
  (interactive "sActor name? "))

;;;; Footer
(provide 'ems-ros)
;;; ems-ros.el ends here
