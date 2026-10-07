;;;; HTTP server functions
;;;;; HTTP server management functions
;;;;;; start
(defun suros-start ()
  "Start your suros server.
The variable `suros-server-object' is set to the created server object.

Your suros reads the variable `suros-config' as it starts, so
make sure you have customized it before starting the server."
  (interactive)
  (let ((config suros-config))
    (if (suros-validate-config config)
	(setq suros-server-object
	      (ws-start
	       suros-http-handlers
	       (ht-get
		suros-config
		"web-port")
	       (get-buffer-create "suros-log"))))))
;;;;;; stop
(defun suros-stop ()
  "Stop your suros server.
Precisely, it calls the function `ws-stop' on the value of the
variable `suros-server-object'."
  (interactive)
  (ws-stop suros-server-object))
;;;;; HTTP server handler functions
;;;;;; HTTP GET handler
(defun suros-handle-http-get-request (http-request)
  "Process REQUEST as an GET-type HTTP request."
  (with-slots (process headers) http-request
    (let* ((object (ht
		    (:headers (ht-create))
		    (:datapool (ht-create))
		    (:rendering nil))))
      (suros-read-config-into-object-datapool suros-config object)
      (suros-read-http-headers-into-object-datapool headers object)
      (if (equal (ht-get (ht-get object :datapool) "requested-path") "")
	  (suros-make-homepage-html-object object)
	(if (ht-get (suros-flippen-flatten-ht suros-objectmakers)
		    (ht-get (ht-get object :datapool) "requested-path"))
	    (funcall (symbol-function
		      (ht-get (suros-flippen-flatten-ht
			       suros-objectmakers)
			      (ht-get (ht-get object :datapool) "requested-path")))
		     object)
	  (ht-set! object :rendering
		   "No path?")
	  (ht-set! object :headers
		   (ht ("Content-type" "text/hml")))))
      (ht-map (lambda (key val)
		(ws-response-header process 200 (list key val)))
	      (ht-get object :headers))
      (process-send-string process (ht-get object :rendering)))))

(defun suros-render-html-h1 (object)
  (concat
   "<h1>"
   (ht-get (ht-get object :datapool) "object-title")
   "</h1>"))
(defun suros-apply-local-data-to-object-datapool (local-data object)
  (ht-map (lambda (datum value)
	   (ht-set! (ht-get object :datapool) datum value))
	 local-data))
(defun suros-render-html-document-declaration (object)
  (let ((data (ht-get object :datapool)))
    (concat
     "<html>")))
(defun suros-make-debug-html-object (object)
  (ht-set! (ht-get object :headers) "Content-type" "text/html")
  (let ((data
	 (ht ("object-title"
	      (concat
	       (ht-get suros-config "server-name")
	       " Debug Page")))))
    (ht-map
     (lambda (datum value)
       (ht-set! (ht-get object :datapool) datum value))
     data))
  (let ((data (ht-get object :datapool)))
  (ht-set!
   object :rendering
   (concat
    "<html><body>"
    "<h1>"(ht-get data "object-title")"</h1>"
    "<section><h2>Object Headers</h2>"
    (suros-render-headers-as-html-dl object)
    "</section>"
    "<section><h2>Object Datapool</h2>"
    (suros-render-datapool-as-html-dl object)
    "</body></html>"))))
(defun suros-render-datapool-as-html-dl (object)
  (concat
   "<dl><dt>"
   (string-join
    (ht-map
     (lambda (key val)
       (concat key "</dt><dd>" val))
     (ht-get object :datapool)) "</dd><dt>")
   "</dd></dl>"))
(defun suros-render-headers-as-html-dl (object)
  (concat
   "<dl><dt>"
   (string-join
    (ht-map
     (lambda (key val)
       (concat key "</dt><dd>" val))
     (ht-get object :headers)) "</dd><dt>")
   "</dd></dl>"))
(suros-make-debug-html-object (ht
			       (:headers (ht-create))
			       (:rendering nil)
			       (:datapool (ht-create))))
(defun suros-send-object-to-http-process (object process)
  (ht-map (lambda (key val) (ws-response-header process 200 '(key . val))) (ht-get object :headers))
  (process-send-string process (ht-get object :rendering)))
(defun suros-read-post-request (request)
  (with-slots (process headers) request
    (process-send-string process "suros has read your POST request.")))
(defun suros-read-head-request (request)
  (with-slots (process headers) request
    (ws-response-header process 200 '("Content-type" . "text/plain"))))
(defun suros-send-html-object (process object)
  (ws-response-header process 200 '("Content-type" . "text/html"))
  (process-send-string process (ht-get object :object)))
(defun suros-send-json-object (process rendering)
  (ws-response-header process 200 '("Content-type" . "application/json"))
  (process-send-string process rendering))
(defun suros-render (template headers context)
  "Returns the rendering of TEMPLATE given CONTEXT."
  (let* ((mustache-partial-paths (list (gethash "template-directory" suros-config)))
	(template (with-temp-buffer (insert-file-contents
				     (concat (gethash "template-directory" suros-config) template ".mustache"))
				    (buffer-string))))
	(mustache-render template context)))
(defun suros-template-p (template)
  "Returns true if there is a file at the given template name. Does no checking of validity."
    (file-exists-p (concat (gethash "template-directory" suros-config) template ".mustache")))
(defun suros-validate-config (config)
  "Returns true. Pretty rubbish validator."
  t)
(defun suros-flippen-flatten-ht (htable)
(ht<-alist
 (-flatten-n 1 (append
		(ht-map (lambda (key vals)
			  (mapcar (lambda (val) (cons val key)) vals))
			htable)))))
(provide 'suros)
