(defun suros-make-object-into-homepage (object)
  (let* ((data (ht-get object :datapool))
	 (local-data
	  (ht ("object-title"
	       (concat
		(ht-get data "preferred-name") "'s "
		(ht-get data "server-name") " instance")))))
    (suros-apply-local-data-to-object-datapool local-data object)))
