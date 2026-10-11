(defun suros-send-object-to-http-process (object process)
  (ht-map (lambda (key val) (ws-response-header process 200 '(key . val))) (ht-get object :headers))
  (process-send-string process (ht-get object :rendering)))
