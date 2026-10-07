(defun suros-make-object-with-config (object config)
  (let ((config-attrs '("actor-public-key"
			"base-url"
			"language-code"
			 "preferred-name"
			 "proper-name"
			 "server-description"
			 "server-name"
			 "server-source-link"
			 "username")))
    (mapcar (lambda (attr)
	      (ht-set! (ht-get object :datapool)
		       attr
		       (ht-get suros-config attr)))
	    config-attrs)))
