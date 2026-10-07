(defun suros-read-http-get-request (http-request)
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
