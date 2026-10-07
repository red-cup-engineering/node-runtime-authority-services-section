

(setq
 suros-http-handlers
 '(((:POST . ".*") .
    (lambda (request) (suros-handle-http-post-request request)))
   ((:GET . ".*") .
    (lambda (request) (suros-handle-http-get-request request)))
   ((:HEAD . ".*") .
    (lambda (request)
      (with-slots (process headers) request
	(ws-response-header
	 process 200
	 '("Content-text" . "text/plain")))))))
