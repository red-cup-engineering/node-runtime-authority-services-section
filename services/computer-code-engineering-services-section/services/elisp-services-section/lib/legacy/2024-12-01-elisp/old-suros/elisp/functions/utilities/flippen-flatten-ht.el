(defun suros-flippen-flatten-ht (htable)
(ht<-alist
 (-flatten-n 1 (append
		(ht-map (lambda (key vals)
			  (mapcar (lambda (val) (cons val key)) vals))
			htable)))))
