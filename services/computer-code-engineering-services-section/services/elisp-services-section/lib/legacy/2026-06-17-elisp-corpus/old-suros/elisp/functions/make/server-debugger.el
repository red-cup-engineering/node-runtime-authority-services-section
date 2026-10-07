(defun suros-make-object-into-server-debugger (object)
  (let ((data (ht ("object-title" (concat
				   (ht-get suros-config "server-name")
				   " Debug Page")))))
    (ht-map
     (lambda (datum value)
       (ht-set! (ht-get object :datapool) datum value))
     data)))
