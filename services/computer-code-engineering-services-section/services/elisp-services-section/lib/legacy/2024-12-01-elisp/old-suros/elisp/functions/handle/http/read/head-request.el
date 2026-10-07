
(defun suros-read-head-request (request)
  (with-slots (process headers) request
    (ws-response-header process 200 '("Content-type" . "text/plain"))))
