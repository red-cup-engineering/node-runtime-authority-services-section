
(defun suros-send-json-object (process rendering)
  (ws-response-header process 200 '("Content-type" . "application/json"))
  (process-send-string process rendering))
