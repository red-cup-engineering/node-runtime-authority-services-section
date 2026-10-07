(defun suros-read-post-request (request)
  (with-slots (process headers) request
    (process-send-string process "suros has read your POST request.")))
