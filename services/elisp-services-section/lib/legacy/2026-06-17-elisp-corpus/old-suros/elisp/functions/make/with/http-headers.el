(defun suros-make-object-with-http-headers (object headers)
  (ht-set! (ht-get object :datapool)
	   :requested-path
	   (substring (cdr (assoc :GET http-headers)) 1)))
